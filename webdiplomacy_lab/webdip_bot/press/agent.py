"""The LLM side: model through the Coworld sidecar, per-call cost logging, tools, one wake.

The only LLM path is COWORLD_LLM_ENDPOINT (the per-pod sidecar; locally,
webdiplomacy_lab/tools/llm_sidecar_local.py). Requests are non-streaming OpenAI chat
completions. The model is COWORLD_LLM_MODEL (fixed per uploaded policy version), with
config.PRESS_MODEL as the local default.
"""

import json
import os
import threading
import time
from pathlib import Path

import httpx2
from pydantic_ai import Agent, CancellationToken
from pydantic_ai.exceptions import RunCancelled, UsageLimitExceeded
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.usage import UsageLimits

from webdip_bot import config
from webdip_bot.dipmap import POWER

HERE = Path(__file__).resolve().parent
SPEND_HEADER = "x-coworld-spend-usd"


def llm_available():
    return bool(os.environ.get("COWORLD_LLM_ENDPOINT"))


def model_name():
    return os.environ.get("COWORLD_LLM_MODEL") or config.PRESS_MODEL


def build_model(journal, ledger, tracker):
    """OpenAI-compatible model on the sidecar. Every request and response is logged.

    `tracker` is the player's {"wake": id, "logged": n} dict. A request logs only the messages
    not yet logged in this wake (the first request of a wake carries the briefing; later ones
    carry the assistant turns and tool results since), so the log reconstructs every
    conversation without repeating it. The system prompt is logged once, at press_start."""

    async def record_request(request):
        try:
            body = json.loads(request.content or b"{}")
        except ValueError:
            return
        messages = body.get("messages") or []
        fresh = messages[tracker["logged"]:]
        tracker["logged"] = len(messages)
        fresh = [{"role": "system", "content": "(system prompt: see press_start)"} if m.get("role") == "system" else m
                 for m in fresh]
        journal.log(event="llm_request", wake=tracker["wake"], model=body.get("model"), messages=fresh)

    async def record(response):
        await response.aread()
        try:
            body = response.json()
        except ValueError:
            body = {}
        usage = body.get("usage") or {}
        call = {"status": response.status_code, "model": body.get("model"),
                "prompt_tokens": usage.get("prompt_tokens") or 0,
                "completion_tokens": usage.get("completion_tokens") or 0,
                "reasoning_tokens": (usage.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0,
                "cached_tokens": (usage.get("prompt_tokens_details") or {}).get("cached_tokens") or 0,
                "cost_usd": float(usage.get("cost") or 0.0),
                "sidecar_spend_usd": response.headers.get(SPEND_HEADER)}
        if response.status_code != 200:
            call["error"] = (body.get("error") or {}).get("message") if isinstance(body, dict) else None
        ledger.append(call)
        reply = ((body.get("choices") or [{}])[0] or {}).get("message") if isinstance(body, dict) else None
        journal.log(event="llm_call", wake=tracker["wake"], generation_id=body.get("id"), reply=reply, **call)

    client = httpx2.AsyncClient(event_hooks={"request": [record_request], "response": [record]},
                                timeout=config.PRESS_CALL_TIMEOUT_S)
    endpoint = os.environ["COWORLD_LLM_ENDPOINT"].rstrip("/")
    # The sidecar ignores the auth header; the SDK still wants a key.
    provider = OpenAIProvider(base_url=endpoint + "/v1", api_key="coworld-sidecar", http_client=client)
    return OpenAIChatModel(model_name(), provider=provider)


def system_prompt(soul):
    soul_text = (HERE / "souls" / soul / "SOUL.md").read_text()
    harness = (HERE / "HARNESS.md").read_text()
    skills = []
    for path in sorted((HERE / "skills").glob("*/SKILL.md")):
        first = path.read_text().split("\n", 3)
        description = next((line[len("description:"):].strip() for line in first if line.startswith("description:")), "")
        skills.append(f"- {path.parent.name}: {description}")
    return f"{soul_text}\n\n{harness}\n\n## Skills (load with read_skill)\n" + "\n".join(skills)


class Toolbox:
    """Tools the agent calls. Each returns plain text or JSON text; errors come back as text
    so the model can correct itself instead of the wake failing."""

    def __init__(self, player):
        self.p = player

    def _guard(self, tool, arguments, fn):
        """Run one tool call: enforce the wake deadline, turn ValueError into text the model can
        read, and log the call with its arguments and result."""
        started = time.time()
        if self.p.wake_deadline and time.time() > self.p.wake_deadline:
            result = "TIME UP for this wake. Stop calling tools and give a one-line final answer."
        else:
            try:
                result = fn()
            except ValueError as error:
                result = f"ERROR: {error}"
        text = result if isinstance(result, str) else json.dumps(result)
        self.p.journal.log(event="tool_call", wake=self.p.tracker["wake"], tool=tool, arguments=arguments,
                           result=text, seconds=round(time.time() - started, 2))
        return text

    def board(self) -> str:
        """The current board: centres and units of every power, neutral centres, and your exposed centres."""
        return self._guard("board", {}, lambda: self.p.service.notation.brief(self.p.country))

    def predict(self, power: str) -> str:
        """The most likely orders of one power this phase under your opponent model and your current committed policy, with frequencies."""
        return self._guard("predict", {"power": power}, lambda: self.p.service.predict(power, self.p.policy))

    def search(self, policy: dict) -> str:
        """Run look-ahead search under a policy and return the best orders for your units with expected/worst-case centres and per-order success rates. Policy keys (all optional): stances {POWER: ally|neutral|hostile}, trust {POWER: 0-1}, expected_orders [other powers' promised orders], forbid_moves_into [provinces], require_orders [your orders that must be played], center_values {POWER: bonus per centre taken from them}, risk 0-1. Does not change your submitted orders."""
        return self._guard("search", {"policy": policy}, lambda: self.p.service.search(policy)[1])

    def evaluate(self, orders: list[str], policy: dict | None = None) -> str:
        """Score a specific set of your orders (standard notation, e.g. "A PAR - BUR"; units left out hold) against sampled opponents under an optional policy."""
        return self._guard("evaluate", {"orders": orders, "policy": policy},
                           lambda: self.p.service.evaluate(orders, policy)[1])

    def assess_deal(self, power: str, their_orders: list[str], our_orders: list[str],
                    our_forbidden: list[str] | None = None) -> str:
        """Value a proposed deal with one power: expected centres if both sides honour it, if they betray you, and if you betray them."""
        def run():
            honour = {"stances": {power: "ally"}, "trust": {power: 1.0}, "expected_orders": their_orders,
                      "require_orders": our_orders, "forbid_moves_into": our_forbidden or []}
            _, both, _ = self.p.service.search(honour)
            _, they_betray = self.p.service.evaluate(both["orders"], {"stances": {power: "hostile"}})
            _, we_betray, _ = self.p.service.search({"stances": {power: "ally"}, "trust": {power: 1.0},
                                                     "expected_orders": their_orders})
            return {"both_honour": {"expected_centres": both["expected_centres"], "our_orders": both["orders"]},
                    "they_betray": {"expected_centres": they_betray["expected_centres"],
                                    "worst_case_centres": they_betray["worst_case_centres"]},
                    "we_betray": {"expected_centres": we_betray["expected_centres"], "our_orders": we_betray["orders"]}}
        arguments = {"power": power, "their_orders": their_orders, "our_orders": our_orders,
                     "our_forbidden": our_forbidden}
        return self._guard("assess_deal", arguments, run)

    def commit_orders(self, policy: dict) -> str:
        """Adopt a policy for THIS phase: runs the search and saves the resulting orders to the server now (you can re-commit later). Returns the orders that will be played."""
        return self._guard("commit_orders", {"policy": policy}, lambda: self.p.commit(policy))

    def send_press(self, to: str, text: str) -> str:
        """Send a message. `to` is a power name (private) or ALL (public). Keep it under 600 characters."""
        return self._guard("send_press", {"to": to, "text": text}, lambda: self.p.send(to, text))

    def conversation(self, power: str) -> str:
        """Your recent private message thread with one power."""
        def run():
            thread = self.p.journal.conversation(self.p.service.notation.country_id(power))
            return "\n".join(thread) or "(no private messages with this power yet)"
        return self._guard("conversation", {"power": power}, run)

    def record_commitment(self, power: str, orders: list[str] | None = None, dmz: list[str] | None = None,
                          note: str = "") -> str:
        """Record a promise made THIS phase so the referee checks it after adjudication. `power` is who promised (a power name, or ME for your own promise); `orders` are promised orders in standard notation; `dmz` are provinces that power promised not to enter."""
        return self._guard("record_commitment", {"power": power, "orders": orders, "dmz": dmz, "note": note},
                           lambda: self.p.record_commitment(power, orders or [], dmz or [], note))

    def update_plan(self, text: str) -> str:
        """Replace your plan.md (objectives, alliance map, intentions for next phases). Keep it under 3000 characters."""
        def run():
            self.p.workspace.set_plan(text)
            return "plan.md saved"
        return self._guard("update_plan", {"text": text}, run)

    def note_power(self, power: str, text: str) -> str:
        """Replace your notes on one power (disposition toward you, trust, goals, style, promises). Keep it under 1800 characters."""
        def run():
            name = power.strip().upper()
            if name not in POWER.values():
                raise ValueError(f"unknown power {power!r}")
            self.p.workspace.set_note(name, text)
            return f"notes on {name} saved"
        return self._guard("note_power", {"power": power, "text": text}, run)

    def read_skill(self, name: str) -> str:
        """Load the full text of one skill listed in your instructions."""
        def run():
            path = HERE / "skills" / name.strip() / "SKILL.md"
            if not path.is_file():
                raise ValueError(f"no skill named {name!r}")
            return path.read_text()
        return self._guard("read_skill", {"name": name}, run)

    def all(self):
        return [self.board, self.predict, self.search, self.evaluate, self.assess_deal, self.commit_orders,
                self.send_press, self.conversation, self.record_commitment, self.update_plan, self.note_power,
                self.read_skill]


def run_wake(agent, prompt, seconds, request_limit):
    """One agent run with a request cap and a wall-clock limit. Returns (final text, status)."""
    token = CancellationToken()
    timer = threading.Timer(seconds, token.cancel)
    timer.start()
    try:
        result = agent.run_sync(prompt, usage_limits=UsageLimits(request_limit=request_limit),
                                cancellation_token=token)
        return str(result.output), "ok"
    except RunCancelled:
        return "", "time_limit"
    except UsageLimitExceeded:
        return "", "request_limit"
    finally:
        timer.cancel()


def make_agent(model, soul, toolbox):
    settings = {"max_tokens": config.PRESS_MAX_TOKENS, "temperature": config.PRESS_TEMPERATURE}
    if config.PRESS_REASONING:
        settings["extra_body"] = {"reasoning": {"effort": config.PRESS_REASONING}}
    return Agent(model, instructions=system_prompt(soul), tools=toolbox.all(), model_settings=settings, retries=2)
