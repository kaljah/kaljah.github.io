#!/usr/bin/env bash
# Build an offline release bundle of Neocarbon (run on a machine with internet access and Docker).
#
#   deploy/release.sh 1.0.0                 # images from Docker Hub
#   REGISTRY=registry.example.dz/library deploy/release.sh 1.0.0
#   SKIP_BUILD=1 deploy/release.sh 1.0.0    # package neocarbon-{app,web}:1.0.0 already built
#   DOCKER_RUN_ARGS="-e HTTPS_PROXY=http://proxy:3128" deploy/release.sh 1.0.0   # proxy for pip
#
# Output: deploy/release/neocarbon-<version>.tar.gz containing
#   images/neocarbon-images.tar   the app, web, postgres and redis images (`docker load -i ...`)
#   compose.yml, .env.example     the container install
#   native/                       the files for an install without containers
#   spa/                          the built web interface (native install)
#   server/                       the API source (native install)
#   wheels/                       Python packages for an offline `pip install` (native install, x86_64)
#   deployment.md                 the install guide
#   SHA256SUMS
set -euo pipefail

VERSION="${1:?usage: deploy/release.sh <version>}"
REGISTRY="${REGISTRY:-docker.io/library}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/deploy/release/neocarbon-$VERSION"

rm -rf "$OUT" && mkdir -p "$OUT/images"
cd "$ROOT"

if [ -z "${SKIP_BUILD:-}" ]; then
  echo "== Building images ($VERSION)"
  for target in app web; do
    docker build -f deploy/Dockerfile --target "$target" --build-arg REGISTRY="$REGISTRY" \
      -t "neocarbon-$target:$VERSION" .
  done
fi
docker pull "$REGISTRY/postgres:16-alpine"
docker pull "$REGISTRY/redis:7-alpine"

echo "== Saving images"
docker save -o "$OUT/images/neocarbon-images.tar" \
  "neocarbon-app:$VERSION" "neocarbon-web:$VERSION" \
  "$REGISTRY/postgres:16-alpine" "$REGISTRY/redis:7-alpine"

echo "== Container install files"
cp deploy/compose.yml "$OUT/compose.yml"
# The bundle runs the images it ships: drop the build sections, pin the version and registry.
python3 - "$OUT/compose.yml" <<'PY'
import re, sys
p = sys.argv[1]
s = open(p).read()
s = re.sub(r"\n    build:\n(?:      .*\n)+", "\n", s)
open(p, "w").write(s)
PY
sed -e "s/^NEOCARBON_VERSION=.*/NEOCARBON_VERSION=$VERSION/" \
    -e "s|^# REGISTRY=.*|REGISTRY=$REGISTRY|" deploy/.env.example > "$OUT/.env.example"

echo "== Native install files"
cp -r deploy/native "$OUT/native"
cp deploy/gunicorn.conf.py deploy/nginx/neocarbon.conf.template "$OUT/native/"
# Built SPA and API source, taken from the images just built so both installs run the same code.
cid=$(docker create "neocarbon-web:$VERSION")
docker cp "$cid:/usr/share/nginx/html" "$OUT/spa"
docker rm "$cid" >/dev/null
cid=$(docker create "neocarbon-app:$VERSION")
docker cp "$cid:/app" "$OUT/server"
docker rm "$cid" >/dev/null
# Python wheels for Python 3.11 on x86_64 Linux, downloaded in the same base image.
# shellcheck disable=SC2086
docker run --rm ${DOCKER_RUN_ARGS:-} -v "$OUT:/out" "$REGISTRY/python:3.11-slim" \
  pip download --no-cache-dir -d /out/wheels -r /out/server/requirements.runtime.txt

cp docs/deployment.md "$OUT/deployment.md"
echo "$VERSION" > "$OUT/VERSION"

echo "== Packing"
(cd "$OUT" && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS)
tar -C "$ROOT/deploy/release" -czf "$ROOT/deploy/release/neocarbon-$VERSION.tar.gz" "neocarbon-$VERSION"
echo "Done: deploy/release/neocarbon-$VERSION.tar.gz"
