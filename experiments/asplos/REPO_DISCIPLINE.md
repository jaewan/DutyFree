# Repo discipline: lessons paid for, not to be re-paid

Dated 2026-08-09. Rules earned during Gate 0 (gem5 tree unification) and
the silicon campaign that preceded it. Not aspirational — each one traces
to a specific incident where skipping it produced a wrong number or a
wasted hour.

## 1. Fetch, then verify merge-base. Never trust a cached remote ref.

`git merge origin/<branch>` against a stale local remote-tracking ref
reports "already up to date" even when the actual GitHub branch has real,
unmerged commits — silently, with no warning. During Gate 0, this hid two
genuine commits (the LLC_RP and PAT-STREAMING changes) behind a stale
`origin/intel_streaming_tax` ref. **Always `git fetch origin <branch>`
immediately before computing a merge-base or attempting a merge** — not
"if it seems out of date," always. A stale-ref false negative looks
identical to a correctly-verified true negative until you check.

## 2. Merge claims are tested with builds and stat-diffs, never accepted from comments.

A PR description or code comment asserting "purely additive," "default
unchanged," or "byte-identical" is a claim, not a verification. The
standard, now applied twice (the finite-SF default-path claim, the
LLC_RP TreePLRU-default claim) and paying out both times: trace the
actual class hierarchy / actual default parameter value in code, then
run the smoke-test diff empirically. A `config.ini`/`stats.txt` diff after
a real build is the only thing that counts as "verified" in this repo's
vocabulary — a comment, however confident, counts as "claimed."

Corollary, also earned this gate: don't trust a config dump's *display
string* either without checking what it means. `type=BRRIPRP` for an
`LLC_RP=srrip` run looked like a bug until the actual class hierarchy
(`RRIPRP(BRRIPRP)`, no `type` override) explained it. Read the source,
not just the output.

## 3. Description diverging from instantiated reality is the recurring failure mode — assume it, don't wait to be surprised by it.

This exact bug class has now shown up in: AMD resctrl schemata
(hardcoded domain 0, three separate times, across three different
scripts), sysfs turbo conventions (two incompatible "boost" semantics
silently collapsed into one ambiguous field), perf event aliases
(a userspace package silently dropped AMD Zen4 counter definitions), and
now potentially the simulator's own published-table provenance (which
commit, which config, actually produced each number). **Any claim about
"what a script/config/commit does" gets verified against instantiated
state before being used for anything paper-bound** — this is what
`env_manifest.py` (silicon) and its gem5-side equivalent (Gate 1) exist
to make routine rather than something rediscovered under pressure each
time.

## 4. One logical change per PR/commit set.

PR #2 bundled the PAT-slot-6 STREAMING decode with the unrelated LLC_RP
replacement-policy addition under one misleading title ("Intel streaming
tax," which describes neither change precisely). This cost real time:
locating the actual PR took a wrong turn through the git history, and
the two changes had to be reviewed and smoke-tested as if independent
anyway, just without the tooling (separate diffs, separate CI runs) that
splitting them would have given for free. Ask contributors for atomic,
accurately-titled commits — it is not bureaucracy, it is what makes
bisection possible six months later when something regresses and nobody
remembers which of five bundled changes did it.

## 6. Build variant configs are part of the repository, not local state.

`build_opts/` in the gem5 repo is gitignored, but 22 standard gem5
defconfigs (`ARM`, `X86`, `MIPS`, etc.) were tracked before that ignore
rule was added — new custom variants (`Intel_8592`, the config behind
every published gem5 number in this campaign) silently fell through the
gap: buildable from one person's local `build_Intel_8592/` cache, not
from the repository. This is the exact same defect class as everything
else in this document — an artifact (here, the resolved Kconfig:
`RUBY=y`, `PROTOCOL=CHI`, `NUMBER_BITS_PER_SET=256`, `USE_X86_ISA=y`)
existed only as one machine's cached state, never committed, never
independently reproducible. **Any custom build variant used for a
paper-bound number gets its `build_opts/<name>` file force-added
(`git add -f`) to the repo**, and verified by actually seeding a fresh
checkout from it (`scons defconfig build_<variant>/gem5.opt
build_opts/<variant>`), not just assumed to work.

## 7. The manifest records how the binary was built, not just how it was run.

Per-run manifests (`gate1_manifest.py` and its silicon-side counterpart)
capture the instantiated *simulation* config, but a build variant with
the wrong Kconfig options produces silently-wrong results no run-time
manifest would catch. Every manifest also records: the exact scons
invocation, the build variant name, and a hash of the resolved
`gem5.build/config` (or equivalent) — so a future audit can tell, from
the manifest alone, whether two runs claiming the "same config" were
actually built from the same Kconfig, not just given the same command-
line flags at run time.

## 8. Provenance goes on the commit, not just in a chat message or a memory note.

Every merge, tag, and correction in this campaign is traceable via `git
log`/`git tag`/PR comments, not just via what someone remembers being
told. `gate0-unified` marks the tree state Gate 1 audits against;
`asplos27-submission` stays put as the historical anchor; the PR carries
a comment explaining *how* it was actually merged (direct `git merge`,
not GitHub's button) so a future reader isn't confused by the mismatch.
