# Frozen config: hash_join fused-null audit

Dated 2026-08-10. Scope: H2-only gem5 SE/Ruby/CHI fused morsel
discriminator for `benchmarks/e2e/hash_join/GEM5_FUSED_NULL_PREREGISTRATION.md`.

## T1 discriminator geometry

| knob | value |
|---|---|
| gem5 binary | `/home/domin/DutyFree-Gem5/build_Intel_8592/gem5.opt` |
| gem5 config | `gem5/configs/deprecated/example/se.py` |
| CHI config | `gem5/configs/ruby/CHI_config_8592.py` |
| workload binary | `benchmarks/e2e/hash_join/build/cxl_join_bench.gem5` |
| CPU model | O3CPU, 1.9 GHz |
| num CPUs | 2 |
| worker threads | 1 |
| topology | Ruby `Pt2Pt`, 1 HNF/LLC slice, 1 dir |
| L1D | 48 KiB, 12-way |
| L1I | 32 KiB, 8-way |
| L2 | 256 KiB, 8-way |
| LLC | 5 MiB, 20-way |
| memory model | `SimpleMemory` |
| DRAM/CXL latency | 98 ns / 203 ns |
| memory size | 256 GiB DRAM, 128 GiB CXL |
| fact stream | 16 MiB, `--fact-node 1` |
| hot set | 2,778,726 bytes, 53% of 5 MiB |
| morsel | 1 MiB |
| warmups/reps | 1 / 3 |
| randomization | `RUBY_RANDOMIZATION=1` |
| prefetch/MSHR env | `L1_MSHR=16 PF_DEGREE_L1=4 PF_DEGREE_L2=8 PF_PAGE=4KiB` |

## Ratio disclosures

| ratio | value |
|---|---:|
| L2:LLC | 256 KiB / 5 MiB = 5.0% |
| hot/LLC | 2,778,726 / 5,242,880 = 53.0% |
| hot/L2 | 2,778,726 / 262,144 = 10.6x |
| hardware-reference hot/L2 | about 85x |

## Arms

| arm | workload |
|---|---|
| `t1_q` | `--mode probe-workload --policy wb` |
| `t1_wb` | `--mode morsel --policy wb` |
| `t1_h2` | `--mode morsel --policy stream` |

Loaded arms must be compared only to `t1_q` from this same config.
