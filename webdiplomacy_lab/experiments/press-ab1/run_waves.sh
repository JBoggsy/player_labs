#!/bin/bash
# press-ab1 wave runner: each wave = one request per arm (same window), stream, wait, repeat.
# Usage: run_waves.sh WAVES EPISODES_PER_ARM ARM=POLICY_VERSION_ID ...   (run from the repo root)
# Request bodies/creation output: experiments/press-ab1/wave<N>-<arm>.{json,out}; ids: waves.tsv.
# Evidence: evidence/press-ab1/<arm>/. Needs HOME pointing at a private ~/.softmax copy.
set -u
waves=$1; episodes=$2; shift 2
dir=webdiplomacy_lab/experiments/press-ab1
S=.claude/skills
for wave in $(seq 1 "$waves"); do
  start=$(( $(ls $dir/wave*-*.out 2>/dev/null | sed 's/.*wave\([0-9]*\)-.*/\1/' | sort -n | tail -1 || echo 0) + 1 ))
  pids=()
  for arm in "$@"; do
    name=${arm%%=*}; ref=${arm#*=}
    python3 $dir/make_request.py "$name" "$ref" "$episodes" $dir/wave$start-$name.json
    uv run python $S/coworld-experience-requests/scripts/experience_request.py create $dir/wave$start-$name.json > $dir/wave$start-$name.out 2>&1
    xreq=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['id'])" $dir/wave$start-$name.out 2>/dev/null)
    if [ -z "$xreq" ]; then echo "wave $start $name create FAILED"; tail -5 $dir/wave$start-$name.out; continue; fi
    printf '%s\t%s\t%s\t%s\n' "$start" "$name" "$ref" "$xreq" >> $dir/waves.tsv
    uv run python $S/coworld-episode-artifacts/scripts/fetch_artifacts.py --xreq "$xreq" --watch \
      --out webdiplomacy_lab/evidence/press-ab1/$name > /tmp/claude-501/press-ab1-$xreq.log 2>&1 &
    pids+=($!)
    echo "wave $start $name $xreq"
  done
  wait "${pids[@]}"
  echo "wave $start drained"
done
