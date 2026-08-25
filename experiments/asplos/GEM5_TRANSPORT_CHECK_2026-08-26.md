# The gem5 retrodiction: the simulator cannot model a congestion component, by construction

The panel proposed this as an afternoon's opportunistic counter-reading: gem5
under-predicts the silicon WB tax by **39%**, and if the two-component model is
right, the gap should show up as under-modelled congestion. **It does — and not
as a measurement but as a structural fact about the model, which is a stronger
form of the same argument.** No simulation was run; this is a config and stats
audit of an existing frozen run (`/tmp/tx_wb_dmt0_cxl_s3`).

## What the model actually contains

From `config.json` of the campaign's own runs:

| | type | latency | latency_var | bandwidth |
|---|---|--:|--:|--:|
| `mem_ctrls[0]` (local DRAM) | **`SimpleMemory`** | 98 000 ps = 98 ns | **0** | capped |
| `mem_ctrls[1]` (CXL) | **`SimpleMemory`** | 203 000 ps = 203 ns | **0** | capped |

And the stats the controllers expose, in full:

    bwRead  bwTotal  bwWrite  bytesRead  bytesWritten  numReads  numWrites
    power_state.pwrStateResidencyTicks

**There is no queue-latency counter, no queue-length counter, no bus-utilisation
counter, and no DRAM timing counter — because there is nothing to count.**
`SimpleMemory` returns every access at a fixed latency with `latency_var = 0`. It
enforces a bandwidth *ceiling* by delaying packet delivery, so throughput
saturates correctly, but each request's latency does not grow with queue depth,
and there are no bank conflicts, row-buffer effects or read/write turnaround.

Stated precisely, because "gem5 models no queueing" would be too strong: **the
model reproduces a bandwidth ceiling but not congestion latency.**

## Why that is the retrodiction

The two-component model says neighbour harm = residency + a non-residency
component. Match that against what the simulator can and cannot represent:

| component | can `SimpleMemory` + CHI produce it? | what the project measured |
|---|---|---|
| **residency** — the stream's lines evicting the victim's | **Yes.** Caches, associativity, replacement and the snoop filter are all modelled in detail | H2 removes **90.9%** of the capacity charge at an infinite SF — gem5's cleanest result |
| **non-residency** — congestion latency under load | **No.** Fixed latency, zero variance, no DRAM timing | gem5 under-predicts the silicon WB tax by **39%** |

So the simulator is accurate exactly where the model says the mechanism acts, and
blind exactly where the model says the residual lives. A 39% shortfall is what
that predicts.

## What this is and is not worth

**It is a genuine retrodiction**, and unusually cheap: it converts a known
simulator defect — one the provenance ledger already carries as "calibration
claim fails: sim 1.600× vs hw 2.61× is 38.7% low" — into evidence for the model.
It also explains why the gem5 arm has always looked *more* favourable to H2 than
silicon: in a world with no congestion latency, removing residency removes almost
everything, so H2 recovers 90.9% there and 28% on the machine.

**It is not proof.** Three honest limits:

1. It is an argument from model *structure*, not from a fitted residual. It shows
   gem5 *cannot* produce a congestion component; it does not show that the missing
   39% *is* congestion. Other omissions could contribute.
2. The 39% figure has its own provenance caveat — the published `tab:gem5`
   calibration was measured against a *local-DRAM* aggressor and is recorded in
   the ledger as not reproducible as published.
3. It cuts against the paper's own simulator results in one direction worth
   stating plainly: **if gem5 systematically omits the component that dominates
   silicon harm, then every gem5 recovery figure in the paper is an upper bound on
   what silicon would show.** H2's 90.9% is the clearest example. That is not a
   reason to drop those numbers, but they must be labelled as ceilings, and the
   28–76% silicon range is the honest quantity.

## Consequence for the write-up

The paper gains a two-line explanation for a discrepancy it has been carrying as
an unexplained defect, and loses the ability to quote gem5 recovery figures
without a ceiling caveat. Both belong in `Sec5`.
