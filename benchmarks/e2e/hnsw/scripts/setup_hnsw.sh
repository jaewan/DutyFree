#!/usr/bin/env bash
# Fetch hnswlib at a pinned commit and build the victim. Header-only, so this
# is a single translation unit.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
root="$(dirname "$here")"
src_dir="$root/third_party/hnswlib"
ref=${HNSWLIB_REF:-d9b3608c83d83b46c96e25088cb1d729b29dcfe9}   # v0.9.0
url=https://github.com/nmslib/hnswlib.git

if [[ ! -d "$src_dir/.git" ]]; then
  mkdir -p "$(dirname "$src_dir")"
  git clone "$url" "$src_dir"
fi
git -C "$src_dir" fetch origin
git -C "$src_dir" checkout --detach "$ref"

mkdir -p "$root/build"
g++ -std=c++14 -O3 -march=native -DNDEBUG -Wall \
    -I"$src_dir" "$root/src/hnsw_bench.cc" -o "$root/build/hnsw_bench"
echo "hnswlib $(git -C "$src_dir" rev-parse HEAD)"
echo "built $root/build/hnsw_bench"
