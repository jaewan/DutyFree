# Draft: question for Eunji (send today, per Gate 0 review)

Subject: quick config question — which checkout were your LLC/SF/prefetcher numbers from?

Hi Eunji,

Before I start reconciling the published gem5 tables against the actual
configs (Gate 1 of the tree-unification pass), I want to make sure I'm
comparing against the right thing. Your email mentioned:

- LLC = 5 MiB *per core* (10 MiB total for the 2-core co-run pair)
- Prefetchers: stride(4)+DCPT / stride+tagged
- (implicitly) infinite SF

Quick question: **which script/config/commit were those statements
describing?** Specifically:

1. Was this from your own local checkout/branch, or from a run against
   `streaming` (or a specific commit on it)?
2. Do you have the exact command line or config file for the run(s) you
   were describing?

I ask because `streaming` HEAD had never actually been built until
yesterday (confirmed via a clean rebuild — the tree had genuinely
diverged from what anyone had last validated), and the harness script
behind the co-run pair (`b4run.sh`) passes `--num-l3caches=1
--l3_size=5MiB` for the 2-core run, which reads as genuinely shared at
the `se.py` level — the opposite of "5 MiB per core." I don't want to
assume either the paper's table or your description is the stale one
without checking, and your answer would save me from re-deriving
something you already know.

Separately, and unrelated to the urgency of the above: the PR you sent
over bundled the PAT-slot-6 STREAMING decode and the LLC_RP replacement-
policy addition into one commit set under one title ("Intel streaming
tax"). I merged it after smoke-testing both paths, but for anything
future, could you split unrelated changes into separate PRs? It made
bisecting slower on my end, and it'll matter more once more people are
touching this tree.

Thanks,
[user]

---

**Note to self**: this is a draft, not sent. No email tool is
authenticated in this session — send manually, or say the word and I'll
walk through Gmail OAuth if you want me to send it directly.
