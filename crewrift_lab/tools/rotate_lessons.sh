#!/usr/bin/env bash
# Shared implementation; this path remains the game hook entrypoint.
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
exec "$REPO/tools/rotate_lessons.sh" crewrift_lab
