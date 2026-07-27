# hash_join_gem5fs — FS-mode fork of benchmarks/e2e/hash_join

Base: DutyFree commit f6e15c1 (original untouched in ../hash_join).
Deltas vs. base:
1. Makefile: add `gem5-fs` target (-static, no -DGEM5 so mbind/pin stay live,
   no -march => SSE2 baseline for gem5 x86).
2. src/cxl_join_bench.cpp: MAP_HUGE_2MB fallback define (build env only).
3. src/cxl_join_bench.cpp: `--line-stride` opt-in flag + stream_read_lines()
   (one 8B load per 64B line) — bandwidth-anchor probe approved by the
   handoff author (2026-07-24 email); default off, original paths unchanged.
