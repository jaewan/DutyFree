#!/usr/bin/env python3
"""RECONSTRUCTION, not the original runner. Read this header before citing it.

Three of the nine rows in the paper's fused-vs-split table (`tab:fused`) come
from `results/clos_split/raw/bsweep_*.json`, run 2026-07-29 05:30-05:31:

    bsweep_B_8way    -> "Fused + CAT  8 of 20 ways"   253.4 Mt/s
    bsweep_B_12way   -> "Fused + CAT 12 of 20 ways"   281.0 Mt/s
    bsweep_A_bsweep  -> "Fused + CAT 20 of 20 ways"   337.0 Mt/s

**The script that produced them does not exist in this repository and, unlike
every other class in that directory, its records do not carry a `cmd` field.**
The way count survives only in the filename. Nothing in the artifact records
which CAT mask was installed, or whether the 20-way row was a full-mask CLOS or
simply CAT torn down. That is unrecoverable and is stated as such in
`experiments/asplos/W4.3_PROVENANCE_LEDGER_2026-08-23.md` (F1.2, F8).

What this file is: the arms those three rows *must* have been, reconstructed
from what the artifacts do record. Every benchmark-side field in the three
bsweep record classes is byte-identical to `panel_B16` -- the 4-of-20-way arm,
whose full argv IS recorded -- except for the presence of `no_stream`, which is
a binary-version difference, not an arm difference (see F8). So the arms differ
from `B16` in the CAT mask alone, and `B16`'s recorded argv fixes everything
else. This script therefore reuses `run_confirmatory_panel` as a module and
overrides only the way count, exactly as `run_mba_moscxl` reuses
`run_probe_moscxl`.

Running it will NOT reproduce the published numbers bit-for-bit: the binary is
a later build (`389c9f2` and after; the 2026-07-29 build was uncommitted
working-tree state), and `results/clos_split/` is the state of one machine on
one morning. What it will do is let a referee re-run the sweep on the same host
and see whether the shape holds.

The 20-of-20 arm is written here as an explicit full-mask CLOS rather than as
CAT-off, because a full-mask CLOS is the honest control for a way sweep -- it
holds the resctrl plumbing constant and varies only the mask. The original may
have used CAT-off instead; if it did, the two should agree, and `A_full`
agreeing with an untouched `A3_16` is itself the check.

Writes to `raw_bsweep_reconstructed/`, never to `raw/`: the committed artifact
directory is not appended to (A6.19).
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_confirmatory_panel as P  # noqa: E402

WAYS = [int(w) for w in os.environ.get("BSWEEP_WAYS", "8,12,20").split(",")]
RAW = P.RESULTS_DIR / "raw_bsweep_reconstructed"


def run_one(label, args, idx, cat_profile):
    """P.run_one with the output path redirected. Identical otherwise."""
    real_raw = P.RAW_DIR
    P.RAW_DIR = RAW
    try:
        return _orig_run_one(label, args, idx, cat_profile)
    finally:
        P.RAW_DIR = real_raw


_orig_run_one = P.run_one
P.run_one = run_one


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    P.cat_teardown()

    specs = {}
    for w in WAYS:
        specs[f"bsweepR_{w}way"] = {
            "args": P.morsel_args(P.FACT_16C, 16, P.CPU16),
            "cat": {"kind": "b", "ways": w, "cpus": P.CPU16},
        }
    # CAT-off control in the same randomized block, so the sweep has an
    # in-block reference and does not lean on panel_A3_16 from an earlier hour.
    specs["bsweepR_off"] = {"args": P.morsel_args(P.FACT_16C, 16, P.CPU16), "cat": None}

    recs = P.run_sequence("bsweepR", specs, P.N_REPS, P.SEED_BASE + 7)
    rows = P.summarize_records(recs)
    for label, row in sorted(rows.items()):
        print(f"{label:16s} n={row['n']:3d} "
              f"throughput_median={row['throughput_median']:8.3f} "
              f"active_cyc_median={row['active_cyc_median']:8.3f}", file=sys.stderr)
    print(f"\nraw -> {RAW}", file=sys.stderr)
    print("Published 2026-07-29 values for comparison: "
          "8way 253.4, 12way 281.0, 20way 337.0, unrestricted 336.6",
          file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    finally:
        P.cat_teardown()
