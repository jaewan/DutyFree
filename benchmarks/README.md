# DutyFree Benchmark Artifact

Artifact for the HotStorage'26 paper on CXL LLC interference.
Reproduces the WB streaming tax measurements and the CAT/MBA double-dissociation.

## Hardware Requirements

| Platform | CPU | LLC | CXL node | Used for |
|----------|-----|-----|----------|----------|
| EMR | Intel Xeon Platinum 8592+ | 320 MB (20 ways) | NUMA node 2, same-socket | WSS sweep + CAT/MBA proof |
| SPR | Intel Xeon Platinum 8462Y+ | 60 MB | NUMA node 2, cross-socket | WSS sweep only |

Both machines require:
- Kernel ≥ 5.12 (resctrl + CXL NUMA support)
- `libnuma-dev`, `numactl`, `gcc`
- Root access (for `setup/` scripts and `cat_mba_driver.sh`)

## Quickstart: Regenerate Figures from Bundled Data

No hardware needed — uses CSVs in `data/`:

```bash
pip install -r analysis/requirements.txt
make figures
# → figures/wss_sweep.pdf  figures/cat_mba.pdf
```

## Quickstart: Reproduce Measurements

### 1. Build binaries

```bash
make build
# or: make -C bench/
```

### 2. Freeze system state (run once per boot)

On EMR:
```bash
sudo bash setup/emr_freeze.sh
```

On SPR:
```bash
sudo bash setup/spr_freeze.sh
```

### 3. WSS sweep (EMR)

```bash
python3 experiments/wss_sweep.py --platform emr --sweep all --out-dir experiments/results/
```

Takes ~45 min (2 sweeps × 3 WSS points × 2 conditions × 30 trials × 10 s).

### 4. WSS sweep (SPR)

On the SPR machine, after running `setup/spr_freeze.sh` and building:
```bash
python3 experiments/wss_sweep.py --platform spr --sweep all --out-dir experiments/results/
```

### 5. CAT/MBA double-dissociation (EMR only, requires root + resctrl)

```bash
sudo bash experiments/cat_mba_driver.sh
```

Takes ~2 hours (11 conditions × 2 phases × 30 trials × 10 s).

### 6. Regenerate figures from your results

```bash
# Copy your results to data/ (or pass --data-dir to the analysis scripts)
python3 analysis/plot_wss.py     --data-dir experiments/results/emr/
python3 analysis/plot_cat_mba.py --data-dir experiments/results/
```

## Directory Structure

```
benchmarks/
├── bench/              C source for all microbenchmarks
│   ├── victim/         pointer_chase_nocap (linked-list traversal)
│   ├── aggressor/      stream_wb, stream_nt, forced_turnover, ...
│   ├── lib/            msr, hugepage, pmu helpers
│   └── Makefile
├── data/               Bundled CSV results from paper runs
├── setup/              System freeze scripts (require root)
│   ├── emr_freeze.sh   EMR (8592+, 320 MB LLC)
│   └── spr_freeze.sh   SPR (8462Y+, 60 MB LLC)
├── experiments/        Measurement orchestration scripts
│   ├── wss_sweep.py    WSS sweep (EMR and SPR)
│   ├── cat_mba.py      CAT/MBA single-condition measurement (called by driver)
│   └── cat_mba_driver.sh  Full 11-condition CAT/MBA run (requires root)
├── analysis/           Figure generation
│   ├── plot_wss.py     WSS sweep figure
│   ├── plot_cat_mba.py CAT/MBA double-dissociation figure
│   └── requirements.txt
├── figures/            Generated figures (created by make figures)
└── Makefile
```

## Paper Figure → Script Mapping

| Figure | Script | Input data |
|--------|--------|------------|
| WSS sweep tax (EMR + SPR) | `analysis/plot_wss.py` | `data/emr_{cxl8,local4}.csv`, `data/spr_{cxl8,local4}.csv` |
| CAT/MBA double dissociation | `analysis/plot_cat_mba.py` | `data/catmba_s{2,3,4,5}_*.csv` (11 files) |

## Experimental Protocol

All measurements use the **frozen protocol**:
- CPU governor: `performance`, turbo disabled (`no_turbo=1`)
- NUMA balancing: off, THP: `madvise`
- Pre-allocated 2 MB hugepages on victim and CXL nodes
- n=30 trials × 10 s/trial, 8 s warmup, 2 s cooldown
- Metric: cycles/load via RDTSC (TSC-frequency-based, P-state independent)

The victim (`pointer_chase_nocap`) does pointer chasing over a randomized linked list,
measuring LLC miss latency. The aggressors (`stream_wb`) stream write to large regions
on the CXL NUMA node, flooding the shared LLC.

## Key Results (EMR, 53% WSS)

| Condition | Slowdown |
|-----------|----------|
| Quiescent | 1.00× |
| CXL-8 baseline | **2.08×** |
| CAT 3-way (disjoint) | **0.99×** at 32 GB/s aggressor BW |
| MBA 30% | 2.04× (tax unchanged) |
| MBA 10% (min) | 1.46× (partial, BW destroyed) |
| Neg ctrl: L2-fit victim | 0.98× |
| Neg ctrl: SF-only turnover | 1.00× |

**Double dissociation**: CAT removes the tax at full BW; MBA cannot.
Mechanism: LLC capacity eviction (spatial displacement, not rate-based).
