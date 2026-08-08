#!/usr/bin/env bash
set -uo pipefail

ROOT=/home/metta/paintbot_rl_training_20260807
STATUS="$ROOT/runs/expert-corpus-v1/training-v1/status.json"
LOCK="$ROOT/runs/expert-corpus-v1/training-v1.lock"

cd "$ROOT"
export PYTHONPATH=paintbot_lab/paintbot/rl
export HF_HOME=/home/metta/.cache/huggingface

while true; do
  /usr/bin/flock --no-fork "$LOCK" \
    .venv/bin/python -u paintbot_lab/paintbot/rl/run_expert_training.py \
      --manifest runs/expert-replay-pool-v1/expert-replay-pool-v1.json \
      --workspace runs/expert-corpus-v1 \
      --output runs/expert-corpus-v1/training-v1
  if test -s "$STATUS" && grep -q '"stage": "complete"' "$STATUS"; then
    exit 0
  fi
  echo "training handoff exited; retrying in 60 seconds" >&2
  sleep 60
done
