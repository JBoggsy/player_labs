#!/usr/bin/env python3
"""Write an intent-instrumented copy of reference/base.bas (for the pw_intent record/audit loop).

Splices reference/intent_telemetry.bas into base.bas and sets the intent variables (mode, heart,
target seat, reason) at base.bas decision points, then calls pwIntent once per decision.
Anchors are exact base.bas text: if base.bas changes, this script fails loudly (str.index).

Usage (repo root):
  uv run python paintbot_pw_lab/reference/wire_intent_base.py paintbot_pw_lab OUT.bas
  uv run python paintbot_pw_lab/tools/pw.py intent record OUT.bas paintbot_pw_lab/reference/base.bas --seeds 3
"""
import sys
from pathlib import Path
lab = Path(sys.argv[1]); out = Path(sys.argv[2])
base = (lab / "reference/base.bas").read_text()
module = (lab / "reference/intent_telemetry.bas").read_text()

def insert_after(text, anchor, addition, nth=1):
    idx = -1
    for _ in range(nth):
        idx = text.index(anchor, idx + 1)
    end = idx + len(anchor)
    return text[:end] + addition + text[end:]

t = base
# module goes after the last helper SUB, before the one-time setup
t = t.replace("if started = 0 then\n  started = 1\n", module + "\nif started = 0 then\n  started = 1\n", 1)
t = insert_after(t, "goalX = selfX\ngoalY = selfY\nholding = 0\n", "intM = 0\nintH = -1\nintS = -1\nintR = 0\n")
t = insert_after(t, "  if thief >= 0 then\n    goalX = playerX(thief)\n    goalY = playerY(thief)\n", "    intM = 6\n    intS = thief\n")
t = insert_after(t, "  if objective >= 0 then\n    hx = controlX(objective)\n    hy = controlY(objective)\n    goalX = hx\n    goalY = hy\n",
                 "    intM = 1\n    intH = objective\n    intR = 1\n")
t = insert_after(t, "        isqrt(ax * ax + ay * ay)\n        if root > 0 then\n", "          intM = 2\n")
t = insert_after(t, "    goalX = pickupMemoryX(nearest)\n    goalY = pickupMemoryY(nearest)\n    holding = 0\n", "    intM = 3\n    intH = -1\n    intR = 5\n")
t = insert_after(t, "  if away >= 0 then\n    goalX = controlX(away)\n    goalY = controlY(away)\n    holding = 0\n", "    intM = 4\n    intH = away\n    intR = 3\n")
t = insert_after(t, "if best >= 0 then\n  tx = playerX(best)\n  ty = playerY(best)\n", "  intS = best\n  if intM <> 4 then\n    intM = 5\n  end if\n")
t = insert_after(t, "    else\n      lookAt(tx, ty)\n    end if\n", "", 1)
t = t.replace("    if clear and gunWait = 0 then\n", "    if clear = 0 then\n      intR = 7\n    end if\n    if clear and gunWait = 0 then\n", 1)
t = insert_after(t, "  if dx * dx + dy * dy < 810000 then\n    sneak(1)\n", "    intR = 6\n")
t = t.rstrip("\n") + "\npwIntent(intM, intH, intS, intR, foesSeen)\n"
out.write_text(t)
print("wrote", out, len(t), "bytes")
