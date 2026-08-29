#!/usr/bin/env bash
set -uo pipefail

ROOT=/home/metta/paintbot_rl_training_20260807
OUTPUT="$ROOT/runs/expert-corpus-v1/training-v2-diversity"
STATUS="$OUTPUT/status.json"
LOCK="$OUTPUT.lock"

cd "$ROOT"
export PYTHONPATH=paintbot_lab/paintbot/rl
export HF_HOME=/home/metta/.cache/huggingface
ulimit -n 8192

while true; do
  /usr/bin/flock --no-fork "$LOCK" \
    .venv/bin/python -u paintbot_lab/paintbot/rl/run_diversity_experiment.py \
      --workspace runs/expert-corpus-v1 \
      --output runs/expert-corpus-v1/training-v2-diversity
  if test -s "$STATUS" && grep -q '"stage": "complete"' "$STATUS"; then
    exit 0
  fi
  echo "diversity experiment exited; retrying in 60 seconds" >&2
  sleep 60
done
