#!/usr/bin/env bash
set -uo pipefail

ROOT=/home/metta/paintbot_rl_training_20260807
OUTPUT="$ROOT/runs/expert-corpus-v1/training-v3-spatial-semantics"
STATUS="$OUTPUT/status.json"
LOCK="$ROOT/runs/expert-corpus-v1/training-v2-diversity.lock"

cd "$ROOT"
export PYTHONPATH=paintbot_lab/paintbot/rl
export HF_HOME=/home/metta/.cache/huggingface
ulimit -n 8192

while true; do
  /usr/bin/flock --no-fork "$LOCK" \
    .venv/bin/python -u paintbot_lab/paintbot/rl/run_spatial_semantics_experiment.py \
      --workspace runs/expert-corpus-v1 \
      --output runs/expert-corpus-v1/training-v3-spatial-semantics
  if test -s "$STATUS" && grep -Eq '"stage": "(complete|screen_rejected)"' "$STATUS"; then
    exit 0
  fi
  echo "spatial semantics experiment exited; retrying in 60 seconds" >&2
  sleep 60
done
