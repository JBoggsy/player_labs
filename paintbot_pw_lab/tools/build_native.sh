#!/usr/bin/env bash
# Build the paintbot-pw native training library (libpw.dylib) that tools/pw_local.py drives.
#
#   paintbot_pw_lab/tools/build_native.sh [coworld-vX.Y.Z]    # default: PW_RELEASE_TAG in tools/release.env
#
# Runs build_tools.sh <tag> first, so the release worktree (tools/.cache/<tag>/) and
# paintbot-headless (the parity reference) exist for the same tag, then compiles
# examples/paintbot/native_env.nim as a shared library into tools/bin/<tag>/libpw.dylib.
#
# Next to the library it writes libpw.build.json: {tag, commit, nim, sha256}. pw_local.py
# refuses to run when that file is missing, names a different tag or commit, or the library's
# sha256 no longer matches (the library itself has no call that reports its build ref).
set -euo pipefail

LAB="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$LAB/tools/release.env"
TAG="${1:-$PW_RELEASE_TAG}"
TREE="$LAB/tools/.cache/$TAG"
OUT="$LAB/tools/bin/$TAG"

"$LAB/tools/build_tools.sh" "$TAG"

cd "$TREE"
export POLYWORLD_DEPS="$TREE/tmp/coworld/deps"
nim c --app:lib --mm:arc --threads:on -d:pwTraining -d:headless -d:release \
  -o:"$OUT/libpw.dylib" examples/paintbot/native_env.nim

COMMIT="$(git rev-parse HEAD)"
NIM="$(nim --version | head -1)"
SHA="$(shasum -a 256 "$OUT/libpw.dylib" | cut -d' ' -f1)"
python3 - "$OUT/libpw.build.json" "$TAG" "$COMMIT" "$NIM" "$SHA" <<'EOF'
import json, sys
path, tag, commit, nim, sha = sys.argv[1:]
with open(path, "w") as f:
    json.dump({"tag": tag, "commit": commit, "nim": nim, "sha256": sha}, f, indent=2)
    f.write("\n")
EOF
echo "built libpw.dylib for $TAG (${COMMIT:0:8}) into $OUT"
