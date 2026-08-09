# Gate 0: unify the gem5 tree

Dated 2026-08-09. Blocks everything after it per the campaign's own rule.

## PR located

The "LLC_RP=srrip|drrip, TreePLRU-default" PR described was not findable by
that description alone — `DutyFree-Gem5` has no branch/PR matching it
literally. Located via explicit user direction: **PR #2** ("Intel streaming
tax", branch `intel_streaming_tax`, author `pakeunji`/Eunji), which bundles
two logically separate changes across two commits:

1. `arch-x86,tests: decode PAT slot 6 as the STREAMING type` — new
   `entry.streaming` PTE-walk decode (PAT=1,PCD=1,PWT=0 at the selector bit
   for each leaf level), `entry.uncacheable = uncacheable && !entry.streaming`,
   plus an `aggressor.c` `argv[2]=="h2"` mode using
   `mprotect(PROT_READ|PROT_STREAMING)`.
2. `[minor] add SRRIP|DRRIP replacement policies (config-only)` — the actual
   `LLC_RP` env knob, in `configs/ruby/CHI.py`.

PR body confirms: *"SRRIP/DRRIP, usage: env LLC_RP=srrip|drrip"*.

**My local `origin/intel_streaming_tax` ref was stale** — `git merge` first
reported "already up to date" before a `git fetch` pulled the real commits;
worth remembering that a merge-base check against a stale remote-tracking
ref is worse than useless, it's confidently wrong.

## Checklist review (adapted to what this PR actually contains)

**(a) Default preserved for LLC_RP**: `_llc_rp = os.environ.get("LLC_RP", "plru").lower()`;
`HNFCache.replacement_policy` is only touched inside `if _llc_rp != "plru":`.
Verified against the actual class hierarchy, not just the PR's own comment:
`RubyCache.replacement_policy = Param.BaseReplacementPolicy(TreePLRURP(), "")`
in `src/mem/ruby/structures/RubyCache.py` — confirmed TreePLRU genuinely is
the unconditional default `HNFCache` inherits when `LLC_RP` is unset.
**Confirmed correct at the code level.**

**(a', for the finite-SF work)**: already on `streaming` (not a separate
fork needing location — it's `8ef0c8ab86`/`28de9e28ba`/`0102eee441` on the
current HEAD `00fca787bd`), already parameterized:
`self.sf_finite = bool(int(os.environ.get("HNF_SF_FINITE", 0)))` in
`configs/ruby/CHI_config_8592.py`, default 0 → `sf=NULL`, "byte-identical
to legacy" per the code's own comment. Capacity is `HNF_SF_WAYS`/`HNF_SF_SETS`
(not literally `SF_ENTRIES=<n>`, but the same explicit-parameter intent).
**Confirmed correct at the code level.** No merge needed for this half —
already unified, just needs the build+validate the HEAD commit message
itself flags as outstanding ("UNBUILT/UNVALIDATED").

**(b) Purely additive / no Ruby-CHI protocol behavior touched**: the
`LLC_RP` commit only touches `configs/ruby/CHI.py` (Python config, not a
protocol `.sm` file) — clean. **The PAT-STREAMING commit is not purely
additive by inspection alone**: it changes `entry.uncacheable`'s
computation for any PTE that happens to hit the PAT=1/PCD=1/PWT=0
combination at a leaf, whether or not the STREAMING feature is otherwise in
use. Whether this is inert for the existing non-STREAMING test matrix
depends on whether any pre-existing config/kernel path already produces
that exact bit pattern for an unrelated reason — not fully resolvable by
static reading alone (depends on the paired `DutyFree-Linux` kernel's own
PAT MSR programming, out of scope for a gem5-only audit). **This is
exactly what the smoke-test diff is for.**

**(c) Smoke-test diff, in progress**:
- Built `streaming` HEAD (`00fca787bd`) clean — first real build+validate,
  since the HEAD commit's own message says "Needs rebuild ... before
  trusting non-pure-R paths." Binary backed up: `/tmp/gem5_baseline_streaming.opt`.
- Merged PR #2 into a scratch branch `gate0-test` (clean merge, no
  conflicts, merge-base `8ef0c8ab86` — PR#2 and the B2/B3 finite-SF surgery
  are true siblings off the B1 scaffold).
- Running `b4run.sh baseline_alone alone 0 0` (quiescent config, SF_FINITE=0,
  H3=0 — the actual default path both before and after the merge) against
  the **baseline** binary now; will rerun the identical invocation against
  the **gate0-test** binary once built, and diff `stats.txt`.
- **Merge criterion**: identical `stats.txt` for this default-path run
  before/after merging PR #2. If it diverges, the PAT-STREAMING commit is
  not safe to merge as-is and needs to be split from the LLC_RP commit
  (which passes its own review independently).

## Also surfaced, relevant to Gate 1 (not yet acted on)

`b4run.sh`'s `COMMON` config passes `--num-l3caches=1 --l3_size=5MiB` for a
`--num-cpus=2` run — at the `se.py` invocation level this looks like a
single, genuinely-shared 5 MiB L3, matching the paper's claim rather than
Eunji's "5 MiB/core = 10 MiB" description. Whether `CHI_config_8592.py`
does anything to this value internally (e.g. multiply by core/HNF count)
is exactly what Gate 1's config-dump step needs to check — noted here so
it isn't lost, not yet verified.

## Smoke-test results

**Default-path diff (LLC_RP unset, both binaries)**: `stats.txt` diff shows
*only* host-performance meta-stats differing (`hostSeconds` 73.84 vs 74.33,
`hostTickRate`, `hostMemory`, `hostInstRate`, `hostOpRate` — all
simulator-wall-clock/resource bookkeeping, not simulated-architecture
statistics). **Every simulated statistic is byte-identical.** This
confirms both halves of the merge (LLC_RP addition, PAT-STREAMING decode)
are inert on the default path — satisfies the merge criterion. The
PAT-STREAMING change specifically is confirmed harmless here because this
test never exercises the `h2` aggressor tag, so `entry.streaming` never
evaluates true regardless of the code path existing.

**Non-default path (`LLC_RP=srrip`)**: ran without error. Checked the
*instantiated* config, not the code's own comments (Gate 1's own
principle, applied a gate early): `config.ini` shows
`system.ruby.hnf.cntrl.cache.replacement_policy` → `type=BRRIPRP`,
`btp=100`, `hit_priority=true`, `num_bits=2`. The `type=BRRIPRP` looked
like a possible bug at first glance (PR code writes `RRIPRP(...)` for
`srrip`) — verified directly against `ReplacementPolicies.py`: `RRIPRP`
is gem5's own mainline class, `class RRIPRP(BRRIPRP): btp = 100`, with no
`type` override, so it correctly inherits `type="BRRIPRP"` for SimObject
registration while being a genuinely distinct, correctly-parameterized
policy (always-long-RRPV insertion vs BRRIP's own bimodal 3%). Not a bug;
gem5's own design, confirmed by reading the class hierarchy rather than
trusting the display string.

## Status: Gate 0 criteria met, ready to finalize

- Default path: byte-identical simulated stats, pre- vs post-merge. ✓
- `LLC_RP=srrip` path: runs, instantiates correctly. ✓ (in progress:
  confirming clean exit, not just correct instantiation)
- Finite-SF: already on `streaming`, already parameterized safely,
  default byte-identical per its own code comment (not independently
  re-verified by a smoke-test diff in this pass — the HEAD commit's own
  "UNBUILT/UNVALIDATED" flag refers to the *non-default* H3/finite-SF
  paths specifically, which Gate 1/Build B's actual validation runs will
  exercise; the default (`sf_finite=false`) path is exactly what both
  smoke-test runs above already tested and passed).

**Next**: merge `gate0-test` into `streaming`, tag, push. Then Gate 1.

## Finalized

- Merged `gate0-test` into `streaming` (`--no-ff`, full verification record
  in the merge commit message): `streaming` HEAD is now `23f27375e9`.
- Tagged `gate0-unified` on the gem5 repo, pushed both branch and tag.
- PR #2 auto-detected as merged by GitHub (identical commit content);
  commented with a pointer to this file, since it was merged via direct
  `git merge` rather than GitHub's own merge button.
- Umbrella `DutyFree` repo's `gem5` submodule pointer updated to
  `23f27375e9`. **`asplos27-submission` tag deliberately left untouched**
  at the old SHA (`00fca787bd`) — it's the reproducibility anchor for what
  was actually submitted; Gate 0's unification is new work building on
  top of it, not a correction to it, so the historical tag stays put and
  `gate0-unified` is the new reference point going forward.
- Scratch branch `gate0-test` deleted (fully merged, no longer needed).

**Gate 0 is complete.** Every future run in this campaign should build
from `streaming` HEAD `23f27375e9` (or later), not the pre-Gate-0
`00fca787bd`.

## Follow-up closed: streaming-path (`st` tag) smoke-test diff

Per the panel's flag that the original smoke test only covered the
default/WB path, not the enforced `setstreaming` route behind the co-run
pair — ran `b4run.sh <name> st 0 0` at both the pre-merge SHA
(binary backed up, restored afterward) and post-merge (`23f27375e9`):
**identical exit tick (`82319833184`) and byte-identical `stats.txt` on
every simulated statistic** — only host-performance meta-stats
(`hostSeconds` etc.) differ, exactly as the default-path check showed.
The PAT-slot-6 STREAMING PTE-decode commit does not interfere with the
existing `setstreaming`-pseudo-inst-based streaming path; the two
mechanisms coexist without observable interaction on this test.
**Gate 0 has no remaining open items.**
