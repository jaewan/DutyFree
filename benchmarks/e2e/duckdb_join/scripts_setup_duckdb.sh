#!/usr/bin/env bash
# DuckDB v1.1.3 (19864453f7) — the victim binary for the join co-run campaign.
# Pinned by version because the hash-join collision-chain layout this campaign
# depends on is an internal detail that upstream is free to change.
set -euo pipefail
dest=${1:-$HOME/duckdb-1.1.3}
mkdir -p "$dest"; cd "$dest"
if [ ! -x ./duckdb ]; then
  curl -fL -o duckdb.zip https://github.com/duckdb/duckdb/releases/download/v1.1.3/duckdb_cli-linux-amd64.zip
  unzip -o duckdb.zip && rm -f duckdb.zip
fi
./duckdb --version
