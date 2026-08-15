#!/usr/bin/env bash
set -uo pipefail

ROOT=/home/metta/paintbot_rl_training_20260807
WORKSPACE=runs/expert-corpus-v1
LOCK="$ROOT/$WORKSPACE/training-v2-diversity.lock"
EVENT_OUTPUT="$ROOT/$WORKSPACE/training-v4-event-actions"
EVENT_STATUS="$EVENT_OUTPUT/status.json"
SPATIAL_OUTPUT="$ROOT/$WORKSPACE/training-v3-spatial-semantics"
SPATIAL_STATUS="$SPATIAL_OUTPUT/status.json"

cd "$ROOT"
export PYTHONPATH=paintbot_lab/paintbot/rl
export HF_HOME=/home/metta/.cache/huggingface
ulimit -n 8192

run_until_terminal() {
  local status=$1
  shift
  while true; do
    /usr/bin/flock --no-fork "$LOCK" "$@"
    if test -s "$status" && grep -Eq '"stage": "(complete|screen_rejected)"' "$status"; then
      return 0
    fi
    echo "accuracy experiment exited; retrying in 60 seconds" >&2
    sleep 60
  done
}

run_until_terminal "$EVENT_STATUS" \
  .venv/bin/python -u paintbot_lab/paintbot/rl/run_event_action_experiment.py \
    --workspace "$WORKSPACE" \
    --output "$WORKSPACE/training-v4-event-actions"

# A promoted event arm needs model-selection review before combining variables.
if grep -q '"stage": "complete"' "$EVENT_STATUS"; then
  exit 0
fi

run_until_terminal "$SPATIAL_STATUS" \
  .venv/bin/python -u paintbot_lab/paintbot/rl/run_spatial_semantics_experiment.py \
    --workspace "$WORKSPACE" \
    --output "$WORKSPACE/training-v3-spatial-semantics"
