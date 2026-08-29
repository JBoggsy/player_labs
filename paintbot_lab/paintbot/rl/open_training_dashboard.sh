#!/usr/bin/env bash
set -euo pipefail

HOST=${PAINTBOT_DASHBOARD_HOST:-mettabox1}
REMOTE_ROOT=${PAINTBOT_TRAINING_ROOT:-/home/metta/paintbot_rl_training_20260807}
REMOTE_PORT=${PAINTBOT_DASHBOARD_REMOTE_PORT:-8765}
LOCAL_PORT=${PAINTBOT_DASHBOARD_LOCAL_PORT:-8876}
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REMOTE_SCRIPT="$REMOTE_ROOT/paintbot_lab/paintbot/rl/training_dashboard.py"
RUN="$REMOTE_ROOT/runs/expert-corpus-v1"
TRAINING_ROOT=${PAINTBOT_DASHBOARD_TRAINING_ROOT:-$RUN/training-v1}
TRAINING_LOG=${PAINTBOT_DASHBOARD_TRAINING_LOG:-$REMOTE_ROOT/logs/expert-training-v1.log}
PID_FILE="$RUN/training-v1/dashboard.pid"
LOG_FILE="$RUN/training-v1/dashboard.log"
HASH_FILE="$RUN/training-v1/dashboard.sha256"
SCRIPT_HASH=$(printf '%s\n%s\n%s\n' \
  "$(shasum -a 256 "$SCRIPT_DIR/training_dashboard.py" | awk '{print $1}')" \
  "$TRAINING_ROOT" "$TRAINING_LOG" | shasum -a 256 | awk '{print $1}')

scp -q "$SCRIPT_DIR/training_dashboard.py" "$HOST:$REMOTE_SCRIPT"
ssh "$HOST" "
set -eu
running=false
if test -s '$PID_FILE'; then
  pid=\$(cat '$PID_FILE')
  if test -r /proc/\$pid/cmdline && tr '\\0' ' ' </proc/\$pid/cmdline | grep -q training_dashboard.py; then
    running=true
    if test \"\$(cat '$HASH_FILE' 2>/dev/null || true)\" != '$SCRIPT_HASH'; then
      kill \$pid
      running=false
    fi
  fi
fi
if test \"\$running\" = false; then
  cd '$REMOTE_ROOT'
  nohup .venv/bin/python -u '$REMOTE_SCRIPT' --workspace '$RUN' \
    --training-root '$TRAINING_ROOT' --training-log '$TRAINING_LOG' \
    --port '$REMOTE_PORT' >'$LOG_FILE' 2>&1 </dev/null &
  echo \$! >'$PID_FILE'
  echo '$SCRIPT_HASH' >'$HASH_FILE'
fi
for attempt in \$(seq 1 20); do
  if curl --fail --silent --max-time 1 'http://127.0.0.1:$REMOTE_PORT/healthz' >/dev/null; then
    break
  fi
  sleep 0.1
done
curl --fail --silent --max-time 1 'http://127.0.0.1:$REMOTE_PORT/healthz' >/dev/null
"

while lsof -nP -iTCP:"$LOCAL_PORT" -sTCP:LISTEN >/dev/null 2>&1 \
  && ! curl --fail --silent --max-time 1 "http://127.0.0.1:$LOCAL_PORT/api/status" >/dev/null; do
  LOCAL_PORT=$((LOCAL_PORT + 1))
done

if ! curl --fail --silent --max-time 1 "http://127.0.0.1:$LOCAL_PORT/healthz" >/dev/null; then
  ssh -fN -o ExitOnForwardFailure=yes -L "$LOCAL_PORT:127.0.0.1:$REMOTE_PORT" "$HOST"
fi

URL="http://127.0.0.1:$LOCAL_PORT"
open "$URL"
printf 'Paintbot RL dashboard: %s\n' "$URL"
