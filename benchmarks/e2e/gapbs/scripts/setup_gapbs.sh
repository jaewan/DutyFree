#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)
src_dir=${GAPBS_SRC_DIR:-"$repo_root/benchmarks/e2e/gapbs/third_party/gapbs"}
url=https://github.com/sbeamer/gapbs.git

if [[ ! -d "$src_dir/.git" ]]; then
  mkdir -p "$(dirname "$src_dir")"
  git clone "$url" "$src_dir"
fi

# Pinned, not floating: the 2026-08-11 sizing gate recorded 2972aeb on both
# hosts, and a later origin/master would silently build a different benchmark.
ref=${GAPBS_REF:-2972aeb2703165bafd921222f4ed7196f542d3a8}
git -C "$src_dir" fetch origin master
git -C "$src_dir" checkout --detach "$ref"
make -C "$src_dir" -j"$(nproc)" bfs pr cc
git -C "$src_dir" rev-parse HEAD
