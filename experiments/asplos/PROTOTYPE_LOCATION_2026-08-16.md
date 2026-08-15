# Where the Linux prototype actually is — and why it is a single point of failure

Written 2026-08-16, after `git submodule update --init linux` returned an
empty repo (one commit, `LICENSE` + `README.md`, no patch).

## Located

| fact | value |
|---|---|
| path | `/home/jb/tmp_dutyfree_exp/DutyFree-Linux` |
| host | `mos182` (`ssh c4`) |
| running kernel | `6.8.0+` |
| evidence | `/lib/modules/6.8.0+/build` -> that path |
| build stamp | `Linux version 6.8.0+ (jb@mos182) ... #5 SMP PREEMPT_DYNAMIC Thu Jul 30 17:34:44 KST 2026` |
| corroboration | `aggressor.c`: "Linux 6.8 claude-draft2: PAT slot 6" |

Searched and ruled out first: `mos181` (this host, whole `/home/domin`),
`mos182` `~`, `moscxl` `~`. The only `PROT_STREAMING` text anywhere reachable
is `gem5/testcase/dirtax/aggressor.c`, which defines the constant itself.

## Not accessible to this account

`/home/jb` is `drwxr-x--- jb jb`; `domin` (uid 1004) is not in group `jb`.
`domin` does hold `sudo` on `mos182`, so it is technically reachable, but
reading a colleague's home directory and republishing its contents is a
consent question, not a technical one. Not done. Escalated to the lead.

## Why this is urgent independent of the ABI decision

1. **The paper's central systems contribution has no reachable
   implementation.** `Sec4_Streaming.tex` makes present-tense claims ("the
   prototype admits anonymous and device-DAX mappings", "the prototype
   enforces I1 for CPU mappings"), and §5 reports a measured ~48 ms epoch
   entry. An artifact evaluator cloning `DutyFree` gets an empty submodule.
2. **It is one unreplicated copy**, in a directory named `tmp_dutyfree_exp`,
   on one machine, owned by one user, with the corresponding GitHub repo
   (`jaewan/DutyFree-Linux`) empty. Any of: a cleanup script, a reimage, a
   disk failure, or that user moving on, loses the artifact behind the paper.
3. **It blocks estimating the sealed-memfd work** properly
   (`SEALED_MEMFD_ESTIMATE_2026-08-16.md` is structural for exactly this
   reason), and it blocks that work being reviewable once done.

## The two ways forward

- **Preferred: `jb` pushes it** to `jaewan/DutyFree-Linux` and the submodule
  pointer is updated. Cleanest — preserves authorship, avoids copying a
  colleague's tree, and lets `jb` exclude anything unrelated or private that
  happens to live under `tmp_dutyfree_exp`.
- **Fallback: retrieve via `sudo`** with the lead's explicit go-ahead, review
  what is captured before committing, and attribute it to `jb`.

Note the mtime on `/home/jb` is today, so `jb` is active on the machine and
reachable.
