# Canonical config sign-off, and #15 Build B resolved by a decision already taken

Written 2026-08-16, closing two items that have been blocking #28.

## 1. Canonical config — sign off on `297e276`, not `b2c64991`

`CANONICAL_CONFIG_PROPOSAL.md` (2026-08-13) proposed gem5
`b2c64991948e771e660041b17ef8c0265d835873`. The tree has since moved, and
every run in the 2026-08-15 campaign used a later commit. Rather than
re-run to match a stale pin, here is what actually separates them.

**`b2c64991` -> `3d0d1ca2` is exactly one commit**, and it is model-neutral:

```
3d0d1ca2  task #26: h1bw_stream probe for tab:h1bw re-run
  .gitignore                      |  1 +
  testcase/dutyfree/h1bw_stream.c | 61 +++++++++
```

**Zero files under `src/`.** It adds a benchmark and a gitignore line; it
cannot change simulation semantics. `git merge-base --is-ancestor` confirms
HEAD descends from `b2c64991` linearly.

**`3d0d1ca2` -> `297e276` is one further commit**, made 2026-08-16: it makes
`number_of_repl_TBEs` env-configurable (`L1_REPL`/`L2_REPL`) in
`CHI_config_8592.py`. Defaults preserved exactly (16 / 32), verified inert by
a control run whose instantiated config was byte-identical to the pre-change
cells (l1d `(64,16)`, l2 `(48,32)` from `config.json`). It changes nothing
unless the new variables are set.

**Recommendation: canonicalise on `297e276` (current `streaming` HEAD),**
recorded as *model-equivalent to `b2c64991`* with the two-commit derivation
above. This is strictly better than pinning `b2c64991`: it is what the
2026-08-15 results were produced at, it is HEAD so nobody has to detach, and
the delta is auditable in two lines.

Everything else in `CANONICAL_CONFIG_PROPOSAL.md` stands unchanged — topology,
cache geometry, `ITERS=3e6`, explicit pool placement in every script, SF
geometry when H3 is in scope, and prefetch/MSHR knobs left at defaults unless
a task documents a reason to sweep.

Two additions the 2026-08-15 campaign forces:

- **Name the LLC replacement policy.** It is `TreePLRURP`, the `RubyCache`
  default, never overridden. Any future comparison must say so rather than
  assume LRU.
- **Prefetchers are part of arm identity now.** H2's fill suppression is
  prefetch-dependent (44.0% with prefetch off, invariant to MSHR depth; 43.5%
  -> 32.6% with it on as depth goes 16 -> 64). `PF_OFF_CORES` and `PF_DEGREE`
  belong in the recorded arm whenever an H2 magnitude is reported.

Still provisional pending Eunji's reply on lineage, exactly as the original
proposal stated. That does not block #28.

## 2. #15 Build B — the scope conflict is moot; do not build it

**Recommendation: close #15 as "not doing", and record the reason.**

The flag's substance (`PHASE2_FINDINGS.md` §2.5): the gem5
finite-transaction-pool model was instructed by a panel but "directly conflicts
with a boundary the user set earlier" — gem5 was explicitly out of scope for
the hardware campaign. The prior session flagged rather than executed,
correctly.

That conflict no longer needs adjudicating, because **the lead's 2026-08-15
decision to demote gem5 subsumes it.** Build B's entire purpose was to
reproduce a *magnitude* in simulation — specifically a transaction-pool
mechanism that reproduces both Intel's near-total flush-behind recovery and
AMD's ~6x residual under the identical mechanism
(`phase2_AMD_flushbehind_OUTCOME.md`). Under demotion, gem5 carries mechanism
existence only and no such magnitude would be cited. Building a model whose
output the paper has decided not to quote is a pure cost.

Three further reasons, each independent:

1. **The target is embargoed.** Build B exists to explain the AMD residual.
   Attributing that residual between H2 and H3 is exactly what §3 forbids. A
   model built to explain it would sit unusable behind the embargo.
2. **It would compound a known credibility problem.** The existing model reads
   39% low, has prefetch-mediated H2 under-enforcement, is not bit-reproducible
   at fixed seed under randomisation, and has an unresolved HNF hit-accounting
   anomaly. Adding a new mechanism to that model makes the artifact harder to
   defend, not easier.
3. **The hardware result already carries the claim.** `phase2_AMD_flushbehind`
   established the cross-vendor discriminator *on silicon*: flush-behind and
   CAT produce near-identical partial recovery on AMD (71.5% vs 69%), while the
   identical mechanism nearly fully recovers on Intel. That is the finding.
   Simulating it adds no evidence a reviewer would weigh more heavily.

What is preserved by closing it: `phase2_AMD_flushbehind_OUTCOME.md` already
states the falsifiable target for whoever picks this up later. Closing #15
does not destroy that; it declines to spend the remaining schedule on it.

**What closing #15 unblocks:** #28 no longer waits on it. Per
`TASK28_DESIGN_MEMO_2026-08-15.md` §6.3, #28 does not need Build B resolved as
long as it runs on the canonical config above — which, with §1 settled, it now
can.
