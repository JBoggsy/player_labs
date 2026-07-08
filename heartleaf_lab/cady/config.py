"""Tunable constants for Cady's deterministic v1 policy."""

GATHER_CUTOFF_MINUTES = 540
"""Stop gathering at 5:00 PM, nine hours after Heartleaf's 8:00 AM start.

All *_MINUTES below are minutes since the 8:00 AM start (Heartleaf's clock;
``perception.parse_clock_minutes``). Dinner is at 6:00 PM = 600."""

# --- Social schedule (deterministic floor; mirrors the starter villager's phases,
# see docs/designs/cady-social-llm-controller.md + villager-dinner-attendance.md).
DINNER_MINUTES = 600
"""6:00 PM (minutes-since-8AM) — the DISPLAYED dinner time. NOTE: dinner actually
RESOLVES/scores at 6:55 PM = 655 (game `DinnerTallyMinutes`), not 600. This
constant is the clock label only; the strategy keys off HOUSE_ENTER_MINUTES
(be inside well before the 655 resolve). See docs/heartleaf-gameplay.md
'Exact timing'."""

DINNER_RESOLVE_MINUTES = 655
"""6:55 PM (minutes-since-8AM) — the tick dinner actually tallies and scores
(game `DinnerTallyMinutes` = DinnerMinutes+55). Be inside our own home BEFORE
this. This is the true deadline, not the 6:00 shown on the clock."""

HOST_PREP_MINUTES = 420
"""3:00 PM (420 min after the 8 AM start). If we are food-rich by now, stop
gathering early and go prepare to host our own party."""

HOUSE_ENTER_MINUTES = 540
"""5:00 PM — stop gathering for good; commit to a house (ours or a party) and be
in position before dinner. Equal to GATHER_CUTOFF_MINUTES by design."""

# --- Food bands that decide host-vs-attend (item counts; only total matters).
STRONG_HOST_FOOD = 12
"""At/above this, we have plenty to host a worthwhile party — host our own."""

LOW_HOST_FOOD = 2
"""At/below this, hosting scores little; better to attend someone else's party
(as a guest we score 0, but this is the floor before the invite/steal logic)."""

ATTEND_MAX_FOOD = 10
"""At/below this food, prefer ATTENDING a heard invite over hosting our own
(hosting `food × guests` scores little with this little food, so reciprocity is
nearly free). Food persists + accumulates across days until a successful dinner
clears it, so early days / just-after-hosting are naturally low-food attend days
— which also keeps self-play non-degenerate (some Cadys attend, real guests
appear). Above this, host. Set generously vs LOW_HOST_FOOD since Cady's
full-circuit gather grows fast once a day gets going."""

HOUSE_CROWD_RADIUS = 48
"""Pixels from a house rect within which a visible gnome counts toward that
house's 'crowd' (for choosing which party to attend)."""

# --- Invite (get guests to OUR party) --------------------------------------
#: Fixed house-owner display names by house index (heartleaf protocol.nim
#: PlayerNames). A player's house index == its gnome index == perception's
#: own_house_index, so PLAYER_NAMES[own_house_index] is OUR house's owner name —
#: which is how villagers refer to a house ("<Name>'s house"). Our invite names
#: our own house this way so a hearer's LLM can commit to attending it.
PLAYER_NAMES = (
    "Ivan", "Anton", "Yura", "Sasha", "Maxim", "Nikita", "Vova", "Dima", "Egor",
)

INVITE_START_MINUTES = 420
"""3:00 PM — start broadcasting invites (matches the villager's invite window;
too early and villagers keep gathering instead of committing)."""

# A gnome HEARS our chat iff our bubble lands in their 320x200 viewport. Since
# each viewer's camera is centered on themselves and the bubble sits just above
# our head, that's ~"the gnome is within a viewport of us" — and perception only
# ever returns gnomes already on OUR screen, so a visible gnome is essentially
# guaranteed to see our chat. We test it as a rectangular in-view box (camera
# cancels: both positions are map coords), inset from the raw half-extents to
# stay clear of the edge / bubble-anchor asymmetry.
INVITE_VIEW_HALF_W = 150
"""Half-width (px) of the in-view box for chat audience (viewport is 320 wide;
inset from 160 for safety)."""

INVITE_VIEW_HALF_H = 90
"""Half-height (px) of the in-view box (viewport is 200 tall; inset from 100,
extra margin because the bubble sits above our head)."""

INVITE_MIN_INTERVAL_TICKS = 72
"""Min frames between our invite chats (~3 s). Chat bubbles linger ~5 s; we
re-broadcast periodically without spamming."""

INVITE_MIN_AUDIENCE = 1
"""Broadcast as soon as at least this many other gnomes are in view. Measured
from replays: during the gather phase Cady has >=1 villager in view ~18% of
frames but >=2 only ~2% — so requiring 2 threw away ~9x the real opportunities.
A single in-view villager both hears the bubble and can accept, so 1 is right.
Kept as a knob in case a future patrol wants to hold out for a group. One
villager in range still gets invited if the window is
closing (see INVITE_BROADCAST_DEADLINE_MINUTES)."""

INVITE_BROADCAST_DEADLINE_MINUTES = 510
"""4:30 PM — past this, drop the audience requirement and invite whoever is in
range (even one), since time to recruit is almost gone before the 5 PM cutoff."""

INVITE_RETURN_MINUTES = 525
"""4:45 PM — stop the door-to-door tour and head back to our own door, so we're
never caught far from home at the HOUSE_ENTER cutoff (5 PM)."""

DOOR_REACH_RADIUS = 24
"""Pixels: how close to a house's door target counts as 'reached' on the
door-to-door invite tour (then we mark it done and move to the next nearest)."""

NAV_PROGRESS_EPS = 2.0
"""Pixels: per-frame movement below this counts as 'no progress' for stuck
detection (she moves several px/frame when walking freely)."""

NAV_STUCK_TICKS = 20
"""Frames of no progress before the navigator force-replans from the current
position. ~0.8s at 24fps — long enough to ignore momentary contact with a wall
while sliding, short enough to escape a real dead-stall before it wastes a day.
Root cause it fixes: a stale cached waypoint walled off from where we actually
are, which the arrival-only cursor could never skip (observed: frozen ~900
ticks against a wall, harvesting ~1/day)."""

INVITE_MAP_CENTER = (374, 473)
"""Walkable point near the map's geometric center (748x941) — the default place
to head when no crowd is visible yet, to maximize the chance of finding one."""

WAYPOINT_RADIUS = 6
"""Distance in pixels at which a cached navigation waypoint counts as reached."""

WAYPOINT_RADIUS_SQ = WAYPOINT_RADIUS * WAYPOINT_RADIUS
"""Squared waypoint-arrival radius for cheap tests."""

HARVEST_RADIUS = 40
"""Distance in pixels from a garden rect at which an A press can harvest.

Matches the game's ``InteractionRadius`` (heartleaf ``common.nim``): the server
harvests when the player's foot is within this distance of the garden rect and A
is pressed."""

MARKER_SIGHT_RADIUS = 60
"""Distance in pixels within which a visible garden marker counts as "food to
harvest here." A bit larger than HARVEST_RADIUS so we don't skip a real garden
whose marker position sits at the edge of range; the game's own 40px check still
gates whether the A press actually collects."""

A_PRESS_PERIOD = 4
"""Frames to wait (releasing A) after each A press before pressing again. The
game acts on a fresh A *edge*; we press once, then observe for this many frames
whether the result we want happened (a pickup, a door transition) before pressing
again — a deliberate press-and-verify cadence, never a per-frame button-spam. A
successful action lands within 1-2 frames, so the mode stops requesting A before
the next press fires."""

MAX_GATHER_TICKS = 12
"""Frames to keep pressing A at one garden before giving up and moving on. One
successful press harvests all of a garden's food, so this only needs to cover
the 1-2 frame perception lag for the pickup to register; if nothing is collected
in this window the garden is empty (already harvested) or out of true range."""

EXIT_RADIUS = 40
"""Distance in pixels from the home exit rect at which an A press can leave."""

HOME_RADIUS = 8  # CALIBRATION: how close to home_anchor counts as seated; TODO(calibrate)
HOME_RADIUS_SQ = HOME_RADIUS * HOME_RADIUS
"""Squared home-arrival radius used by HostMode."""

DIAG_EVERY_TICKS = 24
"""CADY_DIAG cadence while temporary frame diagnostics are enabled."""
