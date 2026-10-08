"""Per-game memory. The Journal holds facts the harness records and checks (press, commitments
and their kept/broken verdicts). The Workspace holds the LLM's own markdown notes. Every
journal event is also printed as one JSON line, so seat logs carry the full record."""

import json
import time

from webdip_bot.dipmap import POWER

NOTE_LIMIT = 1800  # characters per note file; longer writes are cut


def emit(policy, **fields):
    print(json.dumps({"policy": policy, **fields}), flush=True)


def phase_label(turn):
    return f"{'S' if turn % 2 == 0 else 'F'}{1901 + turn // 2}"


class Workspace:
    """plan.md plus one note per power, kept in memory and dumped to the log at game end."""

    def __init__(self):
        self.plan = "(empty: write your strategic plan with update_plan)"
        self.notes = {}

    def set_plan(self, text):
        self.plan = text[:NOTE_LIMIT * 2]

    def set_note(self, power, text):
        self.notes[power] = text[:NOTE_LIMIT]

    def render(self, me):
        parts = ["## Your plan (plan.md)", self.plan, "", "## Your notes on each power"]
        for cid, name in sorted(POWER.items()):
            if cid != me:
                parts.append(f"### {name}\n{self.notes.get(name, '(no notes yet)')}")
        return "\n".join(parts)


class Journal:
    def __init__(self, policy, me):
        self.policy, self.me = policy, me
        self.seen_ids = set()
        self.messages = []  # every message in or out, in arrival order
        self.commitments = []  # dicts: by, turn, orders [(text, signature)], dmz [(abbr, province)], note, verdict

    def log(self, **fields):
        emit(self.policy, t=round(time.time(), 1), **fields)

    # --- press -------------------------------------------------------------------------

    def ingest(self, raw_messages):
        """Add unseen messages (private or public). Returns the new ones."""
        fresh = []
        for m in sorted(raw_messages, key=lambda m: m["id"]):
            if m["id"] in self.seen_ids:
                continue
            self.seen_ids.add(m["id"])
            entry = {"id": m["id"], "turn": int(m["turn"]), "from": int(m["fromCountryID"]),
                     "to": int(m["toCountryID"]), "text": m["message"]}
            self.messages.append(entry)
            if entry["from"] != self.me:
                fresh.append(entry)
                self.log(event="press_in", id=entry["id"], turn=entry["turn"], frm=POWER.get(entry["from"]),
                         to="ALL" if entry["to"] == 0 else "us", text=entry["text"])
        return fresh

    def sent(self, turn, to, text):
        self.log(event="press_out", turn=turn, to="ALL" if to == 0 else POWER[to], text=text)

    @staticmethod
    def render_message(m, me):
        frm = "you" if m["from"] == me else POWER.get(m["from"], "?")
        to = "ALL (public)" if m["to"] == 0 else ("you" if m["to"] == me else POWER.get(m["to"], "?"))
        return f'<press phase="{phase_label(m["turn"])}" from="{frm}" to="{to}">{m["text"]}</press>'

    def conversation(self, power_id, limit=12):
        """Recent private messages between us and one power."""
        thread = [m for m in self.messages if {m["from"], m["to"]} == {self.me, power_id}]
        return [self.render_message(m, self.me) for m in thread[-limit:]]

    # --- commitments -------------------------------------------------------------------

    def commit(self, by, turn, orders, dmz, note):
        entry = {"by": by, "turn": turn, "orders": orders, "dmz": dmz, "note": note, "verdict": None}
        self.commitments.append(entry)
        self.log(event="commitment", by=POWER[by], turn=turn, orders=[t for t, _ in orders],
                 dmz=[a for a, _ in dmz], note=note)

    def verify(self, history, province):
        """Check commitments for finished movement phases against the adjudicated orders."""
        phases = {(ph["turn"], ph["phase"]): ph for ph in history.get("phases", [])}
        for c in self.commitments:
            if c["verdict"] is not None:
                continue
            ph = phases.get((c["turn"], "Diplomacy"))
            if ph is None or not ph.get("orders"):
                continue
            played = [o for o in ph["orders"] if int(o["countryID"]) == c["by"]]
            signatures = {(o["type"], province(o["terrID"]), province(o["toTerrID"]) if o.get("toTerrID") else 0,
                           province(o["fromTerrID"]) if o.get("fromTerrID") else 0) for o in played}
            broken = [text for text, sig in c["orders"] if sig not in signatures]
            entered = {province(o["toTerrID"]) for o in played if o["type"] == "Move" and o.get("toTerrID")}
            broken += [f"entered {abbr}" for abbr, prov in c["dmz"] if prov in entered]
            c["verdict"] = "broken: " + "; ".join(broken) if broken else "kept"
            self.log(event="commitment_verdict", by=POWER[c["by"]], turn=c["turn"], verdict=c["verdict"])

    def facts(self):
        """Referee facts for the briefing: commitment record per power."""
        lines = []
        for c in self.commitments[-20:]:
            what = "; ".join([t for t, _ in c["orders"]] + [f"no entry into {a}" for a, _ in c["dmz"]])
            status = c["verdict"] or "pending (phase not adjudicated yet)"
            lines.append(f"- {POWER[c['by']]} {phase_label(c['turn'])}: {what} -> {status}")
        return "\n".join(lines) or "- no commitments recorded yet"
