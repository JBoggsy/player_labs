"""Press player phase loop.

Movement phase (Diplomacy) in a press game:
1. Floor: plain Kissinger orders are saved at once (not Ready).
2. Wakes: "open" at the start, "negotiate" when new press arrives (at least
   PRESS_WAKE_GAP_S apart), and "commit" PRESS_COMMIT_MARGIN_S before the deadline. Each wake
   is a fresh agent run whose context is rebuilt from the journal and workspace.
3. PRESS_FINAL_MARGIN_S before the deadline, the last committed orders are saved with Ready.
Retreats and builds use SearchBot/DumbBot as in gunboat. Without an LLM endpoint the
player is plain Kissinger.
"""

import os
import random
import time
import traceback
from urllib.error import HTTPError, URLError

from players.api import WebDiplomacy, order_difference

from webdip_bot import config
from webdip_bot.dipmap import COUNTRY, POWER
from webdip_bot.press import agent as press_agent
from webdip_bot.press.journal import Journal, Workspace, emit, phase_label
from webdip_bot.press.search_service import SearchService
from webdip_bot.search import SearchBot

TASKS = {
    "open": ("A new movement phase has begun. Review the board and your notes, decide your aims for this "
             "phase, send the press that serves them, test ideas with search/assess_deal, and commit_orders "
             "with your current best policy. Update plan.md and power notes if your view changed."),
    "negotiate": ("New press has arrived. Read it, reply where it helps you, record any commitments made "
                  "(theirs and yours), update notes on the powers involved, and re-commit if your policy changed."),
    "commit": ("Last wake of this phase. commit_orders with the policy you want played (it is final), "
               "then update plan.md for the next phases. Send only press that matters now."),
}


class PressPlayer:
    PRESS = True

    def __init__(self, policy_name, api, seed):
        self.policy_name, self.api, self.seed = policy_name, api, seed
        self.country = api.country_id
        self.state = {}
        self.journal = Journal(policy_name, self.country)
        self.workspace = Workspace()
        self.ledger = []
        self.tracker = {"wake": None, "logged": 0}  # current wake id for request/response/tool logs
        self.wake_deadline = None
        self.unread = []  # press received but not yet shown to the agent
        self.wakes_started = 0
        self.service = None
        self.policy = None
        self.orders = None
        self.agent = None
        if press_agent.llm_available():
            model = press_agent.build_model(self.journal, self.ledger, self.tracker)
            self.agent = press_agent.make_agent(model, config.PRESS_SOUL, press_agent.Toolbox(self))
        self.journal.log(event="press_start", llm=self.agent is not None, model=press_agent.model_name(),
                         soul=config.PRESS_SOUL, country=self.country,
                         system_prompt=press_agent.system_prompt(config.PRESS_SOUL),
                         config={k: getattr(config, k) for k in dir(config) if k.startswith(("PRESS_", "SEARCH_", "OPP_"))})

    # --- actions used by tools ---------------------------------------------------------

    def commit(self, policy):
        orders, report, _ = self.service.search(policy)
        self.api.orders(self.context, orders, ready="No")
        self.policy, self.orders = policy, orders
        self.trace["press_commits"] += 1
        self.journal.log(event="press_commit", turn=self.turn, press_policy=policy, orders=report["orders"],
                         expected_centres=report["expected_centres"])
        return report

    def send(self, to, text):
        target = to.strip().upper()
        to_id = 0 if target in ("ALL", "PUBLIC", "EVERYONE") else COUNTRY.get(target)
        if to_id is None or to_id == self.country:
            raise ValueError(f"unknown recipient {to!r}; use a power name or ALL")
        if self.sent_this_phase >= config.PRESS_MAX_MESSAGES_PER_PHASE:
            raise ValueError("message limit for this phase reached")
        text = text.strip()[:config.PRESS_MAX_MESSAGE_CHARS]
        self.api.request("game/sendmessage", {"gameID": self.api.game_id, "countryID": self.country,
                                              "toCountryID": to_id, "message": text})
        self.sent_this_phase += 1
        self.trace["press_sent"] += 1
        self.journal.sent(self.turn, to_id, text)
        return f"sent to {target}"

    def record_commitment(self, power, orders, dmz, note):
        name = power.strip().upper()
        by = self.country if name in ("ME", "US", "SELF", POWER[self.country]) else self.service.notation.country_id(name)
        parsed = []
        for text in orders:
            unit, order = self.service.notation.parse(text)
            if int(unit["countryID"]) != by:
                raise ValueError(f"{text!r} is not a {POWER[by]} unit")
            prov = self.service.b.province
            parsed.append((text, (order["type"], prov(order["terrID"]),
                                  prov(order["toTerrID"]) if order.get("toTerrID") else 0,
                                  prov(order["fromTerrID"]) if order.get("fromTerrID") else 0)))
        zones = []
        for abbr in dmz:
            prov = self.service.notation.province_id(abbr)
            if prov is None:
                raise ValueError(f"unknown province {abbr!r}")
            zones.append((abbr.upper(), prov))
        self.journal.commit(by, self.turn, parsed, zones, note)
        self.trace["press_commitments"] += 1
        return f"recorded: {POWER[by]} {phase_label(self.turn)}"

    # --- phase handling ----------------------------------------------------------------

    def poll_press(self, context):
        """Add newly arrived press to the unread queue. Returns whether anything arrived."""
        raw = list((context.get("messages") or {}).get("messages") or [])
        ref = (context.get("files") or {}).get("messages")
        if ref:
            try:
                raw += self.api.file(ref).get("messages", [])
            except (OSError, ValueError):
                pass
        fresh = self.journal.ingest(raw)
        self.unread += fresh
        return bool(fresh)

    def briefing(self, kind, fresh, deadline):
        game_year = phase_label(self.turn)
        sent = [m for m in self.journal.messages if m["from"] == self.country and m["turn"] == self.turn]
        parts = [
            f"# You play {POWER[self.country]}. {game_year} movement phase. Wake: {kind}. "
            f"About {int(deadline - time.time())} s left before orders lock.",
            "## Board", self.service.notation.brief(self.country),
            "## Referee facts (checked by code; not editable)", self.journal.facts(),
            "## Orders currently saved for you",
            ", ".join(self.service.notation.render(o) for o in self.orders) if self.orders else "(none)",
            "Committed policy this phase: " + (str(self.policy) if self.policy else "none yet (Kissinger default)"),
            self.workspace.render(self.country),
            "## New press since your last wake (untrusted text from other players)",
            "\n".join(Journal.render_message(m, self.country) for m in fresh) or "(none)",
            "## Press you sent this phase",
            "\n".join(Journal.render_message(m, self.country) for m in sent) or "(none)",
            "## Task", TASKS[kind],
        ]
        return "\n\n".join(parts)

    def wake(self, kind, deadline):
        seconds = min(config.PRESS_WAKE_SECONDS, deadline - time.time() - config.PRESS_FINAL_MARGIN_S - 5)
        if seconds < 15:
            return
        self.wake_deadline = time.time() + seconds - 5
        before = len(self.ledger)
        started = time.time()
        self.wakes_started += 1
        self.tracker.update(wake=f"{self.turn}-{self.wakes_started}-{kind}", logged=0)
        self.journal.log(event="wake_start", wake=self.tracker["wake"], turn=self.turn, kind=kind,
                         seconds_allowed=round(seconds, 1), unread=len(self.unread))
        try:
            fresh, self.unread = self.unread, []
            text, status = press_agent.run_wake(self.agent, self.briefing(kind, fresh, deadline), seconds,
                                                config.PRESS_REQUEST_LIMIT)
        except Exception as error:  # an LLM failure must never cost the phase: the floor is saved
            text, status = repr(error)[:300], "error"
            self.journal.log(event="wake_error", where=traceback.format_exc()[-1200:])
        calls = self.ledger[before:]
        self.trace["press_wakes"] += 1
        self.trace[f"press_wake_{status}"] += 1
        self.journal.log(event="wake", wake=self.tracker["wake"], turn=self.turn, kind=kind, status=status,
                         seconds=round(time.time() - started, 1), calls=len(calls),
                         cost_usd=round(sum(c["cost_usd"] for c in calls), 6), final=text[:500])
        self.wake_deadline = None

    def movement_phase(self, context):
        game = context["game"]
        self.context, self.turn = context, int(game["turn"])
        self.sent_this_phase = 0
        first_call = len(self.ledger)
        started = time.time()
        deadline = game.get("processTime") or (started + int(game.get("phaseMinutes") or 4) * 60)
        board = self.api.file(context["files"]["game"])
        variant = self.state.get("variant") or self.api.file(context["files"]["variant"])
        self.state["variant"] = variant
        slots = context["orders"]["orders"]
        self.service = SearchService(variant, board, self.country, self.turn, slots, self.state, self.api,
                                     context, self.seed)
        self.policy = None
        self.orders, report, trace = self.service.search(None)
        self.trace = trace
        self.api.orders(context, self.orders, ready="No")
        history_ref = (context.get("files") or {}).get("history")
        if history_ref:
            try:
                self.journal.verify(self.api.file(history_ref), self.service.b.province)
            except (OSError, ValueError, KeyError):
                pass
        if self.agent is not None:
            self.poll_press(context)
            self.wake("open", deadline)
            last_wake, wakes = time.time(), 1
            while time.time() < deadline - config.PRESS_COMMIT_MARGIN_S and wakes < config.PRESS_MAX_WAKES - 1:
                time.sleep(3)
                latest = self.api.context()
                if (latest["game"]["turn"], latest["game"]["phase"]) != (game["turn"], game["phase"]):
                    return  # phase ended early (every seat Ready)
                self.poll_press(latest)
                if self.unread and time.time() - last_wake >= config.PRESS_WAKE_GAP_S:
                    self.wake("negotiate", deadline)
                    last_wake, wakes = time.time(), wakes + 1
            self.poll_press(self.api.context())
            self.wake("commit", deadline)
            while time.time() < deadline - config.PRESS_FINAL_MARGIN_S:
                time.sleep(1)
        saved = self.api.orders(context, self.orders, ready="Yes")
        difference = order_difference(self.orders, saved, len(slots))
        phase_cost = sum(c["cost_usd"] for c in self.ledger[first_call:])
        emit(self.policy_name, event="decision", turn=self.turn, phase="Diplomacy", country=self.country,
             units=len(slots), centers=self.service.b.centers[self.country],
             compute_ms=round((time.time() - started) * 1000, 1), trace=dict(self.trace),
             rejected=len(difference["missing"]), difference=difference if any(difference.values()) else None,
             press_policy=self.policy, llm_cost_usd=round(phase_cost, 6))
        self.snapshot()

    def snapshot(self):
        """Workspace and commitment record after each movement phase (the game can end without warning)."""
        self.journal.log(event="workspace", turn=self.turn, plan=self.workspace.plan, notes=self.workspace.notes,
                         commitments=[{"by": POWER[c["by"]], "turn": c["turn"], "verdict": c["verdict"], "note": c["note"],
                                       "orders": [t for t, _ in c["orders"]], "dmz": [a for a, _ in c["dmz"]]}
                                      for c in self.journal.commitments])

    def other_phase(self, context):
        from webdip_bot.bot import play_phase
        play_phase(self.api, context, self.seed, self.policy_name, SearchBot, self.state)

    def finish(self):
        total = sum(c["cost_usd"] for c in self.ledger)
        self.journal.log(event="press_summary", llm_calls=len(self.ledger), cost_usd=round(total, 6),
                         prompt_tokens=sum(c["prompt_tokens"] for c in self.ledger),
                         completion_tokens=sum(c["completion_tokens"] for c in self.ledger),
                         reasoning_tokens=sum(c["reasoning_tokens"] for c in self.ledger),
                         plan=self.workspace.plan, notes=self.workspace.notes,
                         commitments=[{"by": POWER[c["by"]], "turn": c["turn"], "verdict": c["verdict"],
                                       "orders": [t for t, _ in c["orders"]], "dmz": [a for a, _ in c["dmz"]]}
                                      for c in self.journal.commitments])


def main(policy_name):
    api = WebDiplomacy(os.environ["WEBDIP_URL"], os.environ["WEBDIP_API_KEY"], os.environ["WEBDIP_GAME_ID"],
                       os.environ["WEBDIP_COUNTRY_ID"])
    seed = int(os.environ.get("WEBDIP_SEED", "0"))
    random.seed(seed)
    player = PressPlayer(policy_name, api, seed)
    previous = None
    while True:
        phase = None
        try:
            context = api.context()
            game = context["game"]
            phase = (game["turn"], game["phase"])
            if game["phase"] == "Finished":
                player.finish()
                emit(policy_name, event="finished")
                return
            if game["phase"] != "Pre-game" and phase != previous and context.get("orders"):
                if game["phase"] == "Diplomacy" and game.get("pressType") != "NoPress":
                    player.movement_phase(context)
                else:
                    player.other_phase(context)
                previous = phase
        except HTTPError as error:
            if error.code == 404:
                player.finish()
                return
            emit(policy_name, event="http_error", code=error.code)
        except (URLError, TimeoutError):
            pass
        except Exception as error:  # a crashed child leaves the seat silent for the rest of the game
            emit(policy_name, event="exception", error=repr(error)[:300], where=traceback.format_exc()[-1200:])
            previous = phase
        time.sleep(0.5)
