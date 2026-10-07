#!/bin/bash
# Stop a local run cleanly: kill its python driver(s) and remove its game + player containers.
# usage: webdiplomacy_lab/tools/stop_run.sh <pattern matching the run's out dir or command>
pat="$1"
pkill -f "$pat"
sleep 2
for c in $(docker ps -q --filter name=coworld-run-game); do
  if docker inspect -f '{{range .Mounts}}{{.Source}} {{end}}' "$c" 2>/dev/null | grep -q "$pat"; then
    id=$(docker inspect -f '{{.Name}}' "$c" | sed 's#^/coworld-run-game-##')
    docker ps -aq --filter "name=$id" | xargs -r docker rm -f >/dev/null
  fi
done
