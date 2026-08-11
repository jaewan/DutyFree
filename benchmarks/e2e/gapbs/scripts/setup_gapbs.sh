#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)
src_dir=${GAPBS_SRC_DIR:-"$repo_root/benchmarks/e2e/gapbs/third_party/gapbs"}
url=https://github.com/sbeamer/gapbs.git

if [[ ! -d "$src_dir/.git" ]]; then
  mkdir -p "$(dirname "$src_dir")"
  git clone "$url" "$src_dir"
fi

git -C "$src_dir" fetch origin main
git -C "$src_dir" checkout --detach origin/main
make -C "$src_dir" -j"$(nproc)" bfs pr cc
git -C "$src_dir" rev-parse HEAD
