# Pre-registration: IVF-Flat list-dominated declaration site (native, c4)

Registered **2026-09-02, before any arm of this campaign produced a
number.** STREAMING datapath is **not** measured. This is the identity
gate the silicon IVF CAT scaffold does not provide: inverted lists as one
file-backed VMA whose **scan work dominates the codebook**, so a later
`mprotect` on that mapping would name the fills that actually run.

Do **not** invoke `experiments/asplos/run_silicon_ivf.sh` or
`IVF_FLAT_SILICON_PREREG_2026-09-01.md`. That campaign is CAT on a
**codebook-dominated** costume (`nlist=8192`, `dim=1024`, `nb=nlist×4` ⇒
~4 vectors/list; ~256 KiB lists/query vs 32 MiB codebook). This file is
a different question.

## Why

`--preset silicon` / `--preset gem5` keep codebook/LLC ∈ [0.50, 0.55] by
inflating **nlist×dim**, then set `nb = nlist×4`. Per query the kernel
still walks the **whole codebook**. List bytes per query are
`nprobe × (nb/nlist) × dim × 4`. The work ratio

```
list_dom_ratio = nprobe × nb / nlist²
               = list_bytes_per_query / codebook_bytes_per_query
```

is **0.0078** on silicon and **0.031** on gem5. STREAMING on lists cannot
be the story if the scan is a codebook walk. Inflate **nb**, not dim.

The official STREAMING application cell remains the hash join. Success
here does not add a second STREAMING family to the paper. It licenses a
**later** gem5 H2 kill-gate on this mapping (after r6b is judged), with
its own prereg.

## What this is allowed to be

A **declaration-site** campaign. One sealed IVF-Flat search at the
list-dom geometry below. Metric: recall@k, `/proc/self/smaps` RSS of the
**lists file**, anonymous RSS growth across the timed search, `mprotect`
errno, and `list_dom_ratio`. **Not** QPS vs CAT, **not** neighbour R,
**not** gem5, **not** H2, **not** the 32 MiB codebook CAT cell.

## Host

**mos182 / `ssh c4` only** for `--full`. Smoke (`--self-test`, tiny
identity) may run anywhere. Do **not** run on mos181 (FS r6b owns that
host). No CAT, no victim, no exclusive-host resctrl, no
`run_silicon_ivf.sh`.

## Geometry (the arm)

`--preset list_dom`. Codebook/LLC is **not** in [0.50, 0.55]; that gate
is the CAT costume and is **off**.

| knob | value | why |
|---|---:|---|
| nlist | **128** | small coarse set; invert is `O(nb·nlist·dim)` |
| dim | **256** | RAG-like width; not the 1024-d CAT costume |
| nb | **262144** | lists ≈ 258 MiB; Rss is not kB-granular noise |
| nq | **48** | recall sample; not a QPS campaign |
| nprobe | **32** | 25% of lists |
| k | **10** | costume check |
| kmeans_iters | **3** | train_n=16384 |
| codebook | 128×256×4 = **131072 B** | WB heap |
| lists | nb×dim×4 + nb×8 = **270532608 B** | one file-backed mmap |
| list_dom_ratio | 32×262144 / 128² = **512** | ≫ 8 |

`--require-ratio` on this preset **must abort** (codebook/LLC ≈ 0.002).
`--require-list-dom` on `--preset silicon` **must abort**.

## Registered gates (fail-closed)

- **G-host.** `--full` hostname is `mos182` or `c4`.
- **G-list-dom.** `list_dom_ratio ≥ 8`. Action on miss: **void** (still
  the costume scan). Tiny `--preset tiny` is exactly 8 and may be used
  in unit tests; the arm is 512.
- **G-recall.** `recall_at_k ∈ (0, 1]`. Action on miss: **void** (not
  IVF-Flat).
- **G-vma.** After invert, smaps shows a mapping whose pathname contains
  the lists file and `Rss ≥ 0.50 × lists_bytes`. Action on miss: **void**
  (lists were not the scanned object).
- **G-copy (the STREAMING-site kill).** On the identity arm, anonymous
  RSS growth across the timed search (`[heap]` + nameless anon) is
  **≤ 0.25 × lists_bytes**. Action on miss: **VOID for STREAMING IVF** —
  search copied lists into WB heap; `mprotect` on the file mapping would
  not name the fills. Do **not** start gem5 IVF, do **not** write an E5
  STREAMING IVF sentence.
- **G-stream-uapi.** `mprotect(PROT_READ|PROT_STREAMING)` is attempted
  after invert, lists sealed read-only. Success or `EINVAL` / `ENOSYS`
  is **recorded, not a kill**. Stock SPR is expected to refuse or treat
  slot 6 as WB. This campaign does not claim H2.

`--policy stream` remains refused on native.

## What success licenses

Only: “inverted lists can be a distinct mapping the search scans, list
work dominates the codebook, and search did not fully materialize lists
into anonymous RSS.” That licenses a **later** gem5 SE H2 kill-gate on
**that mapping**, then FS `mprotect`, each with its own prereg. It does
**not** license quoting silicon CAT IVF (unrun), r5 join tuples/s, or
DuckDB +104% as this operator’s STREAMING win.

## What has not happened

No JSONL, no outcome, no gem5, no CAT IVF, no paper sentence. This file
is a gate list, not a result.
