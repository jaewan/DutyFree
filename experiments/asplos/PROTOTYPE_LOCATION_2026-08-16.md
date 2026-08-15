# The Linux prototype was never missing — the submodule pointed at an empty branch

Written 2026-08-16. **This file supersedes its own first version**, which
concluded the prototype was outside version control and at risk of being lost.
That conclusion was wrong, and the corrected finding is much less alarming.

## What was actually wrong

`git submodule update --init linux` produced a repo containing only `LICENSE`
and `README.md`. The cause:

| | commit | contents |
|---|---|---|
| `origin/main` (what the submodule recorded) | `1d8334d` | empty — "Initial commit" |
| `origin/claude-draft2` (the prototype) | `63dab9b` | **v6.8 + 10 commits** |
| `origin/claude-draft` (earlier draft) | `2827b5a` | superseded |

The `DutyFree` submodule pointer recorded `1d8334d`, the tip of an empty
default branch. The prototype has been pushed to `jaewan/DutyFree-Linux` all
along, on a non-default branch. Verified on the build host: local `HEAD` ==
`origin/claude-draft2` exactly, **zero unpushed commits**, working tree clean.

So: not a lost artifact, not an unreplicated copy, not a consent problem. A
one-line submodule misconfiguration.

## The prototype, as it actually exists

`git describe` = `v6.8-10-g63dab9b1239c`. The series:

```
eb342571ead0  x86/pat: add Streaming memory type (PAT slot 6)
7df49f05cb39  x86/cache: add WBNOINVD inline and IPI broadcast helper
3389eff9cded  mm, x86: introduce PROT_STREAMING and VM_STREAMING plumbing
037af838cf7a  mm, x86: implement mprotect(PROT_STREAMING) transitions
d5f06074dfca  mm/streaming: add debugfs PTE query interface
d273e0b50100  mm/streaming: KUnit suite, kselftests, and documentation
7836f7b123ce  mm/streaming: support hugetlb mappings
123d6ae32009  mm/streaming: hugetlb selftest, KUnit case and docs
8d947c88c8db  x86/cache, mm/streaming: broadcast WBNOINVD to one CPU per core
63dab9b1239c  x86/mman: include linux/types.h for bool in arch_validate_prot()
```

`PROT_STREAMING 0x10` is defined at
`include/uapi/asm-generic/mman-common.h:14`. The build host is `mos182`
(`ssh c4`), running `6.8.0+` built from
`/home/jb/tmp_dutyfree_exp/DutyFree-Linux` by `jb`, 2026-07-30, `#5`. That
working tree is a 30 GB build tree; only the 1.6 GB source is tracked.

Note the series includes **KUnit tests, kselftests, and documentation** — a
better-developed artifact than the paper's prose currently suggests.

## The fix applied

- Submodule pointer `1d8334d` -> `63dab9b`.
- Added `branch = claude-draft2` to `.gitmodules`, so `git submodule update
  --remote` tracks the prototype rather than the empty default.

## What remains genuinely worth doing

1. **Make `claude-draft2` the default branch** of `jaewan/DutyFree-Linux`, or
   merge it to `main`. Anyone cloning the repo directly (not via the
   submodule) still lands on an empty tree. This is the actual artifact risk,
   and it is a GitHub setting.
2. The `tmp_dutyfree_exp` build tree on `mos182` remains the only *build*, but
   the source is safe on GitHub, so this is a convenience issue rather than a
   preservation one.

## Correction of method, recorded deliberately

The first version of this file escalated to the lead for permission to
`sudo`-read a colleague's home directory, on the premise that the artifact
existed only there. The premise was wrong and one `git rev-parse` against
`origin` would have shown it. The lesson generalises to this project's own
rule: *an empty checkout is a claim about a pointer, not about the world* —
check the remote's other branches before concluding anything is missing. The
sudo access, once granted, was used only to read git metadata; nothing was
copied, and the fix came from the public repository.
