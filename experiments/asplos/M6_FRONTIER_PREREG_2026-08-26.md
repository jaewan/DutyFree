# M6 pre-registration: the hostile control against M5 — does CAT-narrow reach the same corner?

Written before measurement. **This is the cheapest hostile configuration against
the new headline, and it is registered before the claim is written.**

## The threat

M5's showcase cell is *4 MiB table + flush → 0.9929×*. But a 4 MiB table fits in
one of EMR's 16 MiB ways. So an operator can give F a **narrow CAT mask**: the
table fits, the stream is confined, V keeps the rest. That may reach the same
corner the label reached — via `resctrl`, in an afternoon, with shipped hardware.

The monotone-harm result that says CAT taxes F by +19–44% was measured at the
**256 MiB** table, where any mask starves it. It does not transfer to 4 MiB.

The counter-hypothesis is equally live: the stream churning *inside* F's narrow
mask (~5–10 GB/s through 32 MiB) may evict F's own 4 MiB table faster than the
probe re-promotes it, so CAT-narrow taxes F even at small geometry. **The outcome
is genuinely uncertain, which is why it is measured before the claim ships.**

## Apparatus

`resctrl` verified live on mos181: `cbm_mask = fffff` (20 ways × 16 MiB),
15 CLOSes, `min_cbm_bits = 1`. Victim cpu8 and F's cores 32–47 all resolve to
**L3 domain 0**, so CAT can partition between them. Reusing the committed helper
`resctrl_clos.sh setup_c <F_ways> <F_cpus> <V_cpu>`, which assigns **disjoint**
masks and refuses if any CPU is outside domain 0.

- **none** — no CLOS; both share all 20 ways
- **narrow** — F gets 2 ways (32 MiB), V gets the complementary 18 (288 MiB)

## Two passes

**Pass A — F's own cost, no victim, n=3.** 8 configs: table {4 MiB, 256 MiB} ×
stream {retain, flush} × CAT {none, narrow}. F's stdout is captured, so
`active_cycles_per_access` and `stream_bandwidth_gbps` are read directly. This is
the "cost to F" axis and it cannot be obtained from the co-run pass, where F is
killed before it prints.

**Pass B — V's harm, n=10, order rotated.** 10 arms: `V_none`, `V_narrow`
(baselines, since V's own speed changes when it loses 2 ways), and the 8 F
configs above.

## Pre-registered readings

**R1 — does CAT-narrow reach the corner at 4 MiB?** Compare, at the 4 MiB table
with the stream **retained**:

| outcome | verdict |
|---|---|
| V ≤ 1.05× **and** F's cost within 5% of its uncontrolled value | **CAT-narrow reaches the corner.** The headline becomes *division of labour*, not sole rescue: partitioning arbitrates working sets, the label removes the class partitioning cannot name, and each is used at its natural scope. Still a mechanism story, different sentence. |
| V ≤ 1.05× but F's cost **> 5% worse** | **intra-mask churn taxes F.** The drafted claim survives with its hostile control attached: the label reaches the corner at zero tenant cost, CAT reaches it only by charging the tenant. |
| V > 1.05× | CAT-narrow does not reach the corner at all; the label's win stands outright |

**R2 — does the label help *inside* the composition at 256 MiB?** At the 256 MiB
table with CAT-narrow, compare stream retained vs flushed:

Registered prediction: **flushed beats retained on F's own cost at equal V
protection**, because under CAT-alone F's mask must hold both its table and the
stream's churn, while under label+CAT the churn is gone. If F's cost is *not*
better when flushed, that mechanism is absent and the composition argument is
withdrawn.

**Instrument check, with the action pre-registered.** `V_none` must fall within
**median ± 3 sd** of the pooled victim-alone value from M3b/M4/M5
(78.05–78.09, sd ≈ 0.02 → window 78.01–78.13). **On miss: report, do not void**,
and re-derive harms against this run's own `V_none` rather than the historical
value. That judgement is fixed now, not after seeing the data.

## Out of scope

AMD; the `mid` (5-way) mask, dropped to keep n=10 exact position balance rather
than trading balance for a third point; any change to either binary; e2e.
