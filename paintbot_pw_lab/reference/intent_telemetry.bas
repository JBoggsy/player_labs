' PWI intent telemetry, format v1 (plan T13). Paste this SUB into a policy above its main code
' and call it ONCE, as the last statement of every decision:
'
'   pwIntent(mode, heart, target, reason, seen)
'
' It prints at most one line per decision to the seat's private log:
'
'   PWI v=1 t=<worldTick> m=<mode> h=<heart> s=<target> r=<reason> e=<seen> c=<changed>
'
'   v  format version (1). The parser (tools/pw_intent.py) rejects other versions.
'   t  worldTick when the policy decided. The command it issued shows up in the replay
'      tables at t + 1 (tables are stamped with the tick AFTER the step).
'   m  mode code (table below), h control heart index or -1, s target seat or -1,
'   r  reason code (table below), e how many enemies the policy counted as seen this tick,
'   c  1 when the line was printed because m/h/s/r changed, 0 for a periodic line.
'   s and e are what BASIC observes (visible(i), playerX(i)): a disguised body answers to
'   its disguise, so a disguised teammate counts as an enemy. pw_intent.py audit models this.
'
' Only intent is logged. The replay already holds every executed command (goal, aim, shot,
' sneak, charge) and every position, so logging those would waste the budget.
'
' Mode codes (m), shared with tools/pw_intent.py MODE_NAMES. Keep the two in step.
'   0 hold      nothing chosen, standing
'   1 heart     walking to or capturing the chosen control heart (h)
'   2 cover     covering the chosen heart from outside the ring (h)
'   3 supply    walking to a remembered supply
'   4 retreat   refusing a losing fight, walking to heart h away from the enemy
'   5 fight     in contact with target s (footwork and gun)
'   6 chase     chasing target s
'   7 defend    returning to defend heart h
' Reason codes (r), policy-defined, 0 = none. Current meanings (tools/pw_intent.py REASON_NAMES):
'   1 squad pick, 2 avoided unreachable heart, 3 outnumbered, 4 low hp, 5 wanted supply,
'   6 heard sound, 7 teammate in the line of fire (held fire)
'
' Knobs (globals start at 0, so the module is ON by default with no setup):
'   intentOff = 1      turns the line off entirely.
'   intentEvery = N    periodic line every N ticks (0 = default 24 = 1 second).
'
' Budget (per decision the engine allows 1,024 print bytes and 128 print events; breaking
' either is a runtime error that disables the seat for the rest of the episode;
' bots.nim:160, basic.nim:2423-2430):
'   events: 7 text pieces + 7 values + 1 newline = 15 events per line, 12% of 128.
'   bytes:  text pieces "PWI v=1 t=" (10) + six of " m=" etc. (6 x 3 = 18) = 28 bytes;
'           values are decimal int32, at most 11 bytes each ("-2147483648"), 7 x 11 = 77;
'           newline 1. Worst case 28 + 77 + 1 = 106 bytes, 10% of 1,024.
'           Typical: t up to 5 digits, m/h/s/e 1-2, r 1, c 1 = about 45 bytes.
'   whatever else the policy prints in the same decision must fit in the remaining
'   113 events and 918 bytes.
' Log volume (the seat log is cut at 10 MiB, not fatal; coworld.nim:7-8):
'   worst case one line every tick: 106 x 14,400 ticks = 1.53 MB, 15% of the cap.
'   typical: one line per 24 ticks plus changes, about 45 x (2,500 / 24 + changes) = a few KB
'   for a normal 1,600-4,100 tick league match.
' Instructions: the SUB is a handful of comparisons and one PRINT, about 40 VM instructions,
' under 0.1% of the 50,000 budget. BASIC cannot read its own instruction count (no builtin),
' so budget headroom is NOT in the line; measure peaks locally with PW_BASIC_PEAKS=1.
' Dead cogs do not run BASIC, so there are no lines while a seat waits to respawn.
sub pwIntent(mode, heart, target, reason, seen)
  if intentOff = 1 then
    exit sub
  end if
  pwiPeriod = intentEvery
  if pwiPeriod <= 0 then
    pwiPeriod = 24
  end if
  pwiChanged = mode <> pwiMode or heart <> pwiHeart or target <> pwiTarget or reason <> pwiReason
  ' pwiStarted keeps the first decision from comparing against the zero defaults.
  if pwiStarted = 0 then
    pwiChanged = 1
    pwiStarted = 1
  end if
  if pwiChanged or worldTick >= pwiNext then
    print "PWI v=1 t="; worldTick; " m="; mode; " h="; heart; " s="; target; " r="; reason; " e="; seen; " c="; pwiChanged
    pwiNext = worldTick + pwiPeriod
    pwiMode = mode
    pwiHeart = heart
    pwiTarget = target
    pwiReason = reason
  end if
end sub
