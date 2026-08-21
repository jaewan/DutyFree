#!/usr/bin/env bash
# DuckDB v1.1.3 (19864453f7) — the victim binary for the join co-run campaign.
# Pinned by version because the hash-join collision-chain layout this campaign
# depends on is an internal detail that upstream is free to change.
set -euo pipefail
dest=${1:-$HOME/duckdb-1.1.3}
mkdir -p "$dest"; cd "$dest"
# curl is NOT installed on mos181 (only wget); prefer whichever exists.
url=https://github.com/duckdb/duckdb/releases/download/v1.1.3/duckdb_cli-linux-amd64.zip
if [ ! -x ./duckdb ]; then
  if command -v curl >/dev/null 2>&1; then
    curl -fL -o duckdb.zip "$url"
  elif command -v wget >/dev/null 2>&1; then
    wget -qO duckdb.zip "$url"
  else
    echo "need curl or wget" >&2; exit 1
  fi
  unzip -o duckdb.zip && rm -f duckdb.zip
fi
./duckdb --version
