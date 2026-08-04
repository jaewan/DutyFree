# ASPLOS'27 STREAMING — experiment harness

Reproduces the gem5 (H1/H2/H3) and AMD-hardware results in the ASPLOS paper.
Every script here maps to a specific table/claim.

## gem5 simulation (Intel 8592+ build, CHI Ruby)

The gem5 model is the `gem5` submodule, branch `streaming`, tag
`asplos27-submission` (commit `00fca787bd`). Build:

```
cd ../../gem5    # or the sibling ~/DutyFree-Gem5 working clone
yes '' | scons build_Intel_8592/gem5.opt -j"$(nproc)"
```

Run harnesses (env-parametrized; both write to `/tmp/<name>/stats.txt`):

| Script | Purpose | Paper artifact |
|---|---|---|
| `b4run.sh` | single run: victim + `alone`/`wb`/`st` aggressor, finite-SF + H3 knobs | base harness |
| `b4run2.sh` | same, with env `WSS`/`ITERS`/`L3_ASSOC` + MSHR/PF knobs exposed | base harness (sweeps) |
| `sfsweep.sh` | snoop-filter size sweep → the 65,536-entry knee | SF sizing (Sec5) |
| `p0batch.sh` | ITERS gate, victim-neutrality (MSHR throttle), H2 bandwidth band | **de-confound** (Sec5 `tab:h3sf` + de-confound paragraph) |
| `p1batch.sh` | H2 recovery vs LLC associativity and WSS/LLC ratio (infinite SF) | **`tab:sens`** (sensitivity) |
| `collect.sh` | pull cyc/iter, tax, back-invals, SF-evicts, aggressor BW from a batch | analysis |
| `parse_p0.py` | de-confound batch → per-arm tax vs MSHR-matched baseline | analysis |
| `bwcheck.py` | node-separated aggressor bandwidth (victim=DRAM0, stream=CXL node1) | de-confound BW attribution |

Env knobs read by `gem5/configs/ruby/CHI_config_8592.py`:
`HNF_SF_FINITE HNF_SF_SETS HNF_SF_WAYS HNF_H3 HNF_DMT HNF_MSHR L1_MSHR L2_MSHR PF_DEGREE_L1 PF_DEGREE_L2 PF_OFF_CORES`.
Note `HNF_SF_FINITE=1` requires `HNF_DMT=0` (asserted).

### Key results reproduced
- **tab:h3sf** (finite SF, 65,536 entries): WB inf-SF 1.22×, WB finite-SF 2.53×,
  H2 2.55×/3683 back-inval, H2+H3 1.05×/11.
- **de-confound**: at matched config the H3/ReadOnce aggressor sustains *higher*
  bandwidth (3.84 GB/s) than the enrolling H2 aggressor (2.52) while cutting the
  tax 2.55×→1.05× — recovery is SF-enrollment elision, not a slower stream.
  (NB: MSHR-throttling is an *invalid* BW control — it makes the H3 aggressor
  revert ReadOnce→ReadShared and re-enroll; use the like-for-like native compare.)
- **tab:sens**: H2 recovery 76–84% across LLC assoc {8,12,20} and WSS/LLC
  {53%,97%}; L2-resident (24%) victim → H2 correctly a no-op (scope boundary).

## AMD hardware (EPYC 9754, broker; CXL node 2)

| Script | Purpose | Paper artifact |
|---|---|---|
| `exp35_smba_pareto.sh` / `exp35_analyze.py` | SMBA bandwidth-throttle Pareto vs CAT | CAT+SMBA insufficiency |
| `exp36_localdram_ccx.sh` / `exp36_analyze.py` | local-DRAM + cross-CCX controls | CAT residual is generic, not CXL-specific |

## Design reference
- `H3_IMPL_SPEC.md` — finite-SF + SF_Eviction + H3-bypass implementation spec.
- `CHI_H3_B1_and_pseudoinst.patch` — the B1 (knobs + setstreaming TLB-flush) patch.

## Paths
Harnesses hardcode `~/DutyFree-Gem5` and `testcase/dirtax|dutyfree/...`; adjust to
`../../gem5` if running from the submodule checkout. Raw outputs land in `/tmp` and
are archived under `results/` (git-ignored — see repo `.gitignore`).
