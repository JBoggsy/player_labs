#!/usr/bin/env bash
set -uo pipefail

ROOT=/home/metta/paintbot_rl_training_20260807
WORKSPACE=runs/expert-corpus-v1
LOCK="$ROOT/$WORKSPACE/training-v2-diversity.lock"
DIVERSITY_STATUS="$ROOT/$WORKSPACE/training-v2-diversity/status.json"
DIVERSITY_VALIDATION="$ROOT/$WORKSPACE/training-v2-diversity/full/validation_evaluation.json"
BASELINE_AUTOREGRESSIVE_VALIDATION="$ROOT/$WORKSPACE/training-v1/full/validation_autoregressive_evaluation.json"
EVENT_OUTPUT="$ROOT/$WORKSPACE/training-v4-event-actions"
EVENT_STATUS="$EVENT_OUTPUT/status.json"
SPATIAL_OUTPUT="$ROOT/$WORKSPACE/training-v3-spatial-semantics"
SPATIAL_STATUS="$SPATIAL_OUTPUT/status.json"
DASHBOARD_PID="$ROOT/$WORKSPACE/training-v1/dashboard.pid"
DASHBOARD_LOG="$ROOT/$WORKSPACE/training-v1/dashboard.log"

cd "$ROOT"
export PYTHONPATH=paintbot_lab/paintbot/rl
export HF_HOME=/home/metta/.cache/huggingface
ulimit -n 8192

retarget_dashboard() {
  local training_root=$1
  local training_log=$2
  if test -s "$DASHBOARD_PID"; then
    local pid
    pid=$(cat "$DASHBOARD_PID")
    if test -r "/proc/$pid/cmdline" \
      && tr '\0' ' ' <"/proc/$pid/cmdline" | grep -q 'training_dashboard[.]py'; then
      kill "$pid"
      for _ in $(seq 1 20); do
        kill -0 "$pid" 2>/dev/null || break
        sleep 0.1
      done
    fi
  fi
  nohup .venv/bin/python -u paintbot_lab/paintbot/rl/training_dashboard.py \
    --workspace "$ROOT/$WORKSPACE" \
    --training-root "$training_root" \
    --training-log "$training_log" \
    --port 8765 >"$DASHBOARD_LOG" 2>&1 </dev/null &
  echo $! >"$DASHBOARD_PID"
}

run_until_terminal() {
  local status=$1
  local training_root=$2
  local training_log=$3
  shift 3
  while true; do
    (
      /usr/bin/flock --exclusive 9
      retarget_dashboard "$training_root" "$training_log"
      "$@" >>"$training_log" 2>&1
    ) 9>"$LOCK"
    if test -s "$status" && grep -Eq '"stage": "(complete|screen_rejected)"' "$status"; then
      return 0
    fi
    echo "accuracy experiment exited; retrying in 60 seconds" >&2
    sleep 60
  done
}

exceeds_target() {
  local evaluation=$1
  test -s "$evaluation" \
    && .venv/bin/python -c \
      'import json,sys; raise SystemExit(json.load(open(sys.argv[1]))["groups"]["all"]["autoregressive_exact_action_accuracy"] <= 0.70)' \
      "$evaluation"
}

while ! test -s "$DIVERSITY_STATUS" \
  || ! grep -q '"stage": "complete"' "$DIVERSITY_STATUS"; do
  sleep 60
done

while ! test -s "$BASELINE_AUTOREGRESSIVE_VALIDATION"; do
  (
    /usr/bin/flock --exclusive 9
    .venv/bin/python -u paintbot_lab/paintbot/rl/evaluate_sft.py \
      --checkpoint "$WORKSPACE/training-v1/full/best" \
      --samples "$WORKSPACE/arrow/validation" \
      --maps "$WORKSPACE/prepared/validation.maps.jsonl" \
      --sample-indices "$WORKSPACE/indices/validation.npy" \
      --max-text-tokens 4096 \
      --out "$BASELINE_AUTOREGRESSIVE_VALIDATION" \
      >>"$ROOT/logs/baseline-autoregressive-validation.log" 2>&1
  ) 9>"$LOCK"
  if ! test -s "$BASELINE_AUTOREGRESSIVE_VALIDATION"; then
    echo "baseline autoregressive evaluation exited; retrying in 60 seconds" >&2
    sleep 60
  fi
done

if exceeds_target "$DIVERSITY_VALIDATION"; then
  exit 0
fi

run_until_terminal "$EVENT_STATUS" \
  "$EVENT_OUTPUT" \
  "$ROOT/logs/event-actions.log" \
  .venv/bin/python -u paintbot_lab/paintbot/rl/run_event_action_experiment.py \
    --workspace "$WORKSPACE" \
    --output "$WORKSPACE/training-v4-event-actions"

# Continue to the independent spatial arm unless event actions already clear the
# preregistered target. Combining representation variables remains a later,
# validation-selected experiment.
if exceeds_target "$EVENT_OUTPUT/full/validation_evaluation.json"; then
  exit 0
fi

run_until_terminal "$SPATIAL_STATUS" \
  "$SPATIAL_OUTPUT" \
  "$ROOT/logs/spatial-semantics.log" \
  .venv/bin/python -u paintbot_lab/paintbot/rl/run_spatial_semantics_experiment.py \
    --workspace "$WORKSPACE" \
    --output "$WORKSPACE/training-v3-spatial-semantics"
