#!/usr/bin/env bash
# Builds the offline install bundle. Run on a machine WITH internet (Linux, WSL or Git Bash), from a clean
# checkout of the release tag. The target server needs no internet: everything it installs is in the bundle.
#
#   PY_VERSION   Python minor version on the target server (default 3.11). The wheels must match it.
#   PLATFORM     pip platform tag of the target (default manylinux2014_x86_64; use ..._aarch64 for ARM).
#   VERSION      bundle version (default: git describe).
set -euo pipefail
# Git Bash on Windows rewrites values like "/" into "C:/Program Files/Git/"; keep them as typed.
export MSYS_NO_PATHCONV=1

PY_VERSION="${PY_VERSION:-3.11}"
PLATFORM="${PLATFORM:-manylinux2014_x86_64}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VERSION="${VERSION:-$(git -C "$ROOT" describe --tags --always 2>/dev/null || date +%Y%m%d)}"
NAME="ghg-platform-$VERSION"
OUT="$ROOT/dist/$NAME"
ABI="cp${PY_VERSION/./}"

echo "==> Building $NAME for Python $PY_VERSION on $PLATFORM"
rm -rf "$OUT"
mkdir -p "$OUT/server" "$OUT/web" "$OUT/wheels" "$OUT/deploy"

echo "==> Web app"
(cd "$ROOT/new/client" && npm ci && VITE_API_URL=/api VITE_BASE_PATH=/ npm run build)
cp -r "$ROOT/new/client/dist/." "$OUT/web/"

echo "==> Server code"
(cd "$ROOT/new/server" && tar \
    --exclude=tests --exclude=__pycache__ --exclude='*.pyc' --exclude='*.db' --exclude='*.db-wal' \
    --exclude='*.db-shm' --exclude=backups --exclude=upload_jobs --exclude=instance --exclude=trace.log \
    --exclude='audit_*_bugs*.json' --exclude='seed_berkine*' --exclude=.env -cf - .) | tar -C "$OUT/server" -xf -

echo "==> Python packages (wheels for Python $PY_VERSION, $PLATFORM)"
grep -viE '^(pytest|hypothesis)' "$ROOT/new/server/requirements.txt" > "$OUT/requirements-runtime.txt"
python3 -m pip download -r "$OUT/requirements-runtime.txt" --dest "$OUT/wheels" \
    --only-binary=:all: --platform "$PLATFORM" --python-version "$PY_VERSION" --implementation cp --abi "$ABI"

echo "==> Install files"
cp "$ROOT/deploy/native/"{install.sh,upgrade.sh,ghg.service,ghg.env.example} "$OUT/deploy/"
# index.html carries one small inline script; the nginx security policy allows exactly that script by hash.
HASH="$(python3 - "$OUT/web/index.html" <<'PY'
import base64, hashlib, re, sys
html = open(sys.argv[1], encoding="utf-8").read()
inline = [m for m in re.findall(r"<script>(.*?)</script>", html, re.S)]
assert len(inline) == 1, f"expected exactly one inline script in index.html, found {len(inline)}"
print(base64.b64encode(hashlib.sha256(inline[0].encode("utf-8")).digest()).decode())
PY
)"
sed "s|__INLINE_SCRIPT_HASH__|$HASH|" "$ROOT/deploy/native/nginx-ghg.conf" > "$OUT/deploy/nginx-ghg.conf"
grep -q '__INLINE_SCRIPT_HASH__' "$OUT/deploy/nginx-ghg.conf" && { echo "hash placeholder not replaced" >&2; exit 1; }
cp "$ROOT/docs/sonatrach/install-linux.md" "$OUT/INSTALL.md" 2>/dev/null || true
echo "$VERSION" > "$OUT/VERSION"
echo "$PY_VERSION" > "$OUT/PYTHON_VERSION"
chmod +x "$OUT/deploy/"*.sh

echo "==> Archive and checksums"
(cd "$ROOT/dist" && tar -czf "$NAME.tar.gz" "$NAME" && sha256sum "$NAME.tar.gz" > "$NAME.tar.gz.sha256")
echo "Done: $ROOT/dist/$NAME.tar.gz"
cat "$ROOT/dist/$NAME.tar.gz.sha256"
