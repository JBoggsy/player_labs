#!/bin/bash
# usage: verify_round.sh <round_id> <label>
set -u
S=/private/tmp/claude-501/-Users-jamesboggs-coding-personal-labs-personal-paintbot/9883cd94-2df2-4e9d-aca1-2737f3dca09b/scratchpad
R=$1; L=$2
cd ~/coding/personal_labs/personal_paintbot
uv run coworld episodes -r "$R" --json 2>/dev/null > $S/eps-$L.json
python3 - "$S/eps-$L.json" <<'PY' > $S/eps-$L.txt
import json,sys
d=json.load(open(sys.argv[1])); e=d['entries'] if isinstance(d,dict) else d
print("episodes", len(e), "failed", sum(1 for x in e if x.get('status')=='failed'), "versions", sorted(set(x['coworld_id'] for x in e)))
ok=[x for x in e if x.get('status')=='completed' and x.get('replay_url')]
print(ok[0]['id'] if ok else "", ok[0]['replay_url'] if ok else "")
PY
head -1 $S/eps-$L.txt
E=$(sed -n 2p $S/eps-$L.txt | cut -d' ' -f1); U=$(sed -n 2p $S/eps-$L.txt | cut -d' ' -f2)
[ -z "$E" ] && { echo "no completed episode with replay"; exit 1; }
curl -s -o $S/ep-$L.replay "$U"
cd ~/coding/coworlds/coworld-ctf
echo "== movement (replay $E)"; timeout 600 $S/move_probe $S/ep-$L.replay 2>&1 | tail -17 | sed 's/aliveTicks/alive/; s/movingTicks/moving/; s/ kills=[0-9]* deaths=[0-9]*//'
mkdir -p $S/logs-$L; cd ~/coding/personal_labs/personal_paintbot
uv run coworld --elevated episode-logs $E --agent 3 -d $S/logs-$L > /dev/null 2>&1
f=$(ls $S/logs-$L/*agent_3.log 2>/dev/null | head -1)
echo "== agent 3 log: $(wc -c < "$f") bytes"
python3 - "$f" <<'PY'
import sys
s=open(sys.argv[1],errors="replace").read().replace("\\n","\n")
for key in ("model backend", "Roster (name, seat, team)", "Huddle so far", "You are ", "Your duo partner is", "0xA3 chat:"):
    hits=[l for l in s.split("\n") if key in l]
    print(f"{key!r}: {len(hits)} lines; first: {hits[0][:200] if hits else '-'}")
PY
