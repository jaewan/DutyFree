# Artifact Manifest

Maps each paper claim to the script, data file, and expected output that supports it.

## Paper Claims and Verification

### Claim 1: WB streaming tax grows with WSS / LLC fraction (EMR)

**Expected result**: At WSS=170 MB (53% of 320 MB LLC), CXL-8 aggressor causes ~2.1× victim slowdown;
at WSS=80 MB (25%), smaller tax; at WSS=320 MB (100%), similar or higher.

| Item | Path |
|------|------|
| Input data | `data/emr_cxl8.csv` |
| Script | `analysis/plot_wss.py` |
| Figure | `figures/wss_sweep.pdf` |
| Reproduction | `python3 experiments/wss_sweep.py --platform emr --sweep cxl8` |

**Expected CSVs from fresh run**: `experiments/results/emr/emr_cxl8.csv`

Key values in bundled data (EMR, CXL-8):
- WSS=80 MB (25% LLC): Q≈78.5, A≈102 cycles/load, slowdown ~1.3×
- WSS=170 MB (53% LLC): Q≈81.5, A≈169 cycles/load, slowdown ~2.1×
- WSS=320 MB (100% LLC): Q≈81, A≈~200+ cycles/load

---

### Claim 2: Local DRAM aggressors also cause tax, but smaller (EMR)

**Expected result**: `local4` sweep shows tax at 53% WSS, but lower than `cxl8`.

| Item | Path |
|------|------|
| Input data | `data/emr_local4.csv` |
| Script | `analysis/plot_wss.py` |
| Reproduction | `python3 experiments/wss_sweep.py --platform emr --sweep local4` |

---

### Claim 3: Tax exists on SPR (cross-socket CXL)

**Expected result**: SPR shows tax at 53% WSS (32 MB / 60 MB LLC) with CXL-8 aggressors.

| Item | Path |
|------|------|
| Input data | `data/spr_cxl8.csv`, `data/spr_local4.csv` |
| Script | `analysis/plot_wss.py` |
| Reproduction | `python3 experiments/wss_sweep.py --platform spr --sweep all` (on SPR machine) |

---

### Claim 4: Mechanism is LLC capacity eviction (CAT/MBA double dissociation)

**Expected result**:
- CAT with disjoint ways → tax eliminated at full aggressor BW (0.99× at 32 GB/s)
- MBA 30% throttle → tax unchanged (2.04×, BW reduced to 24 GB/s)
- MBA 10% minimum → tax partially reduced (1.46×, BW destroyed to 8.7 GB/s)

| Item | Path |
|------|------|
| Input data | `data/catmba_s{2,3,4,5}_*.csv` (11 files) |
| Script | `analysis/plot_cat_mba.py` |
| Figure | `figures/cat_mba.pdf` |
| Reproduction | `sudo bash experiments/cat_mba_driver.sh` (EMR, requires root + resctrl) |

Key data files and conditions:

| File | Condition | Expected slowdown |
|------|-----------|-------------------|
| `data/catmba_s2_quiescent.csv` | No aggressor | 1.00× |
| `data/catmba_s2_cxl8_baseline.csv` | CXL-8, all ways shared | 2.08× |
| `data/catmba_s3_cat_full.csv` | CAT full (= unpartitioned) | 2.03× |
| `data/catmba_s3_cat_3ways.csv` | CAT 3 disjoint ways for aggressor | **0.99×** |
| `data/catmba_s3_cat_1way.csv` | CAT 1 disjoint way for aggressor | **0.99×** |
| `data/catmba_s4_mba_100.csv` | MBA 100% (no throttle) | 2.03× |
| `data/catmba_s4_mba_30.csv` | MBA 30% | 2.04× |
| `data/catmba_s4_mba_20.csv` | MBA 20% | 1.82× |
| `data/catmba_s4_mba_10.csv` | MBA 10% (minimum) | 1.46× |
| `data/catmba_s5_neg_l2fit.csv` | L2-fit victim, CXL-8 aggressor | 0.98× |
| `data/catmba_s5_neg_turnover.csv` | SF-only turnover (no LLC eviction) | 1.00× |

---

### Claim 5: Negative controls confirm LLC pathway

**Expected result**: L2-fit victim (WSS=2 MB) is immune to CXL LLC flooding (0.98×);
forced SF turnover (32 MB << 320 MB LLC) causes no victim slowdown (1.00×).

| Item | Path |
|------|------|
| Input data | `data/catmba_s5_neg_l2fit.csv`, `data/catmba_s5_neg_turnover.csv` |
| Script | `analysis/plot_cat_mba.py` |
| Reproduction | Included in `cat_mba_driver.sh` Step 5 |

---

## System Configuration

All measurements were taken under the **frozen protocol** documented in `setup/emr_freeze.sh`.
The frozen system state captured during paper runs is in `data/emr_system_state.txt` (if present).

Hardware summary:
- EMR: Intel Xeon Platinum 8592+, 320 MB LLC (20 ways, 16 MB/way), kernel 7.0.0-22-generic, microcode 0x210002d3
- SPR: Intel Xeon Platinum 8462Y+, 60 MB LLC, same kernel family

## Estimated Reproduction Time

| Experiment | Time | Hardware |
|------------|------|----------|
| `wss_sweep.py` EMR all | ~45 min | EMR machine, no root needed |
| `wss_sweep.py` SPR all | ~20 min | SPR machine (smaller LLC → shorter warmup) |
| `cat_mba_driver.sh` | ~2 hours | EMR machine, root + resctrl required |
| `make figures` (bundled data) | <1 min | Any machine with Python + matplotlib |
