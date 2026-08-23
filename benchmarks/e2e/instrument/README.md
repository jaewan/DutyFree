# Vendored instrument source

The streamer binaries that produce every co-run number in `benchmarks/e2e`
were, until this directory existed, built from sources that lived **only** in a
second repository (`~/tmp_dutyfree_exp`) and were **uncommitted there**. The
md5 recorded in a campaign log was the entire provenance record: nothing tied a
published tax figure to a recoverable source. This directory closes that.

Vendored on 2026-08-23, on the lead's instruction.

## What is here, and what it is

| file | role | upstream status |
|---|---|---|
| `src/aggressor.c` | the Intel/AMD streamer: `wb_load`, `wb_prefetchnta`, `wb_local`, `-N <node>` | tracked in `tmp_dutyfree_exp`, **modified and uncommitted** |
| `src/common.h` | allocation and pinning helpers; a build dependency of *every* instrument | tracked in `tmp_dutyfree_exp`, **modified and uncommitted** |
| `src/amd_flushbehind_aggressor.c` | the flush-behind streamer: the `FB0`/`FB256` arms | **untracked in any repository, and present on one host only** |

## Provenance

Upstream repository `https://github.com/jaewan/tmp_dutyfree_exp.git`, HEAD
`481115c5ceece541afa524240c67eb5492b3b9b6` (2026-05-15).

- `aggressor.c` differs from `481115c:src/aggressor.c` by the addition of
  `-N <mem_node>` and the `wb_local` mode (local-DDR write-back streaming, used
  for the `WB_local` control arm). Upstream blob `4fe556f`.
- `common.h` differs from `481115c:src/common.h` by `+33` lines: the
  `alloc_wb_node()` helper, which binds with `MPOL_BIND` and spot-checks
  placement with `move_pages` every 64 MB. Upstream blob `99757c3`.
- `amd_flushbehind_aggressor.c` has no upstream blob. It was never `git add`ed
  anywhere, and existed only on `moscxl`. Its md5 `143a308f...` is the first
  durable record of it.

The other four instrument sources in that repo — `victim.c`,
`validate_memtype.c`, `intra_app_corun.c`, `latency_chase.c` — are
byte-identical to `481115c` and are **deliberately not vendored**: their
provenance is already pinned by a real commit hash in a real repository, and
copying them here would create a second copy to keep in sync for no gain.
`common.h` is vendored because it is uncommitted, and it is a build dependency
of those four as well — see "The drift hazard" below.

## Verification performed at vendoring time

Not "the file was copied", but "this source is the one that produced the data":

1. `aggressor.c` and `common.h` are byte-identical across **mos181, moscxl and
   mos182** (`check_drift.sh`, all match).
2. On every host, a fresh build from that source is **bit-identical to the
   binary already deployed** there. No host is running a stale binary:

   | host | `bin/aggressor` md5 | fresh build |
   |---|---|---|
   | mos181 | `2022e09cd8a0dd00e5656e3bd4a79212` | identical |
   | moscxl | `85e05f4d2869dc9e1bcb074099ac4f2c` | identical |
   | mos182 | `ac3a0f4c9c56079b19421da0cddd99be` | identical |

   The three differ from each other because of `-march=native`; that is
   expected, and is why binaries are never copied between hosts.
3. `amd_flushbehind_aggressor` on moscxl, md5 `cbc25208c177b2f7c05ba3c4a6cabbc3`,
   is reproduced bit-identically by **both** its header's documented build line
   (`-mavx2`, no `-msse4.1`, `-lnuma -lm`) and this Makefile's uniform flags, so
   the flag difference is immaterial and the uniform flags are used.
4. The vendored `amd_flushbehind_aggressor.c` also compiles clean on Intel
   (`-Wall -Wextra`, no diagnostics), though it has only ever been run on Zen.

## Why native builds

`-march=native` is part of the instrument, not an optimisation detail: the
streamer's bandwidth depends on which vector width the compiler selects. Each
host builds its own binary from identical source. A binary copied from another
host is not the same instrument and its numbers are not comparable.

## The drift hazard, which is the point of `check_drift.sh`

**Vendoring did not change what the hosts build from.** Every campaign script
still points at `~/tmp_dutyfree_exp/bin/` — `run_join_campaign.py` defaults
`AGG_BIN` there, and `FB` is hard-coded there. So this directory is a second
copy of a live source, and a second copy that nothing compares is worse than
one copy, because it looks authoritative while being able to be stale.

`./check_drift.sh` md5s the live sources on all three hosts against
`MANIFEST.md5` and exits non-zero on mismatch. **Run it before any campaign
whose numbers will be cited, and keep the output with that campaign's
artifacts.** If it reports drift, the vendored copy is not evidence for
anything produced after the drift, and which side is correct has to be
established before, not after, looking at the results.

`make verify` checks only this checkout against the manifest; `check_drift.sh`
is the one that checks the hosts.

Two follow-ups are deliberately **not** taken here, because they are structural
and belong to the lead:

- pointing the campaign scripts at this directory instead of
  `~/tmp_dutyfree_exp/bin/`, which would make the vendored copy authoritative
  and delete the hazard rather than monitor it. That changes the apparatus, and
  the apparatus rule forbids doing it as a side effect of a bookkeeping commit.
- committing the two modified files upstream in `tmp_dutyfree_exp`, which would
  give them real hashes. Nothing here can do that for `amd_flushbehind_aggressor.c`
  in any case: it needs a decision about which repository owns it.

## Building

    make            # both streamers, into ./bin (gitignored)
    make verify     # this checkout's sources vs MANIFEST.md5
    ./check_drift.sh   # all three hosts' live sources vs MANIFEST.md5
