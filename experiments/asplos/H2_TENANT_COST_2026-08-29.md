# The streaming tenant's own cost under H2 is not zero --- it is negative. H2 is Pareto-improving in the model.

Found on 2026-08-29 while designing the "writeback-pressure workload" I had
called the critical path. **The workload already exists**, the number already
existed in the archived runs, and nobody had computed it. This is the number the
whole wedge argument rests on.

## What I had been claiming, and why it was wrong

I had stated repeatedly that "every mechanism we can actually execute costs the
tenant ~15%, and STREAMING's zero-cost claim exists only in the model, unmeasured."
The second half was false. The measurement was sitting in
`/tmp/sf_{wb,h2}_inf_s{1,2,3}` and in this week's own batch.

I had also stated that a gem5 workload in the admission regime needs to
"generate **writeback** pressure, since the HNF only fills on writebacks." That
framing was wrong in a way that mattered: it implied the workload must **dirty**
lines, which a read-only STREAMING contract (I1) forbids, making the requirement
look self-contradictory. In fact a read-only stream fills a victim-cache HNF
through **clean-eviction writebacks** --- L2 evicts clean data as `WriteEvictFull`,
which carries the block, and `alloc_on_writeback=true` admits it. The only real
requirement is a footprint exceeding the **2 MiB private L2**. The 512 KiB
verification workload failed for that reason alone, not for lack of dirty data.

## H2 does bite, and hard, at the HNF

Archived infinite-SF runs, TreePLRU, seed 1:

| HNF counter | WB | H2 | change |
|---|--:|--:|--:|
| `LocalHN_Eviction` | 4,424,887 | **31,669** | **-99.3%** |
| demand hits | 477,620 | 814,436 | +70.5% |
| demand misses | 1,818,082 | 1,048,397 | -42.3% |
| `numTagArrayWrites` | 14,566,485 | 8,923,548 | -38.7% |
| `reqOut.m_stall_time` | 2,054,056,062 | 1,308,229,628 | -36.3% |

H2 removes essentially every HNF eviction. The stream stops displacing the
neighbour, and interconnect stall time falls across every port.

## The tenant's own cost: +0.00% per instruction, +10.4% throughput

`cpu1` is the streaming aggressor. Its cycle count tracks simulation *duration*
(the run ends when `cpu0` finishes 3M iterations), so only **rates** are
meaningful. n=3 seeds, sd negligible.

| arm | IPC | total L2 misses/kcyc | **misses per instruction** |
|---|--:|--:|--:|
| WB | 0.1626 | 27.10 | --- |
| **H2** | 0.1794 (**+10.4%**) | 29.91 (**+10.4%**) | **+0.00%** |
| H2+H3 | 0.1196 (-26.4%) | 52.35 (+93.2%) | **+162.6%** |

**Misses per instruction is unchanged to two decimals.** The aggressor's
instruction stream and its per-instruction memory behaviour are identical; the
entire effect is that it runs **10.4% faster**. Stream bandwidth per cycle rises
by the same 10.4%.

Why: a stream has no reuse, so LLC residency was worth nothing to it, while the
congestion its own pollution created was costing it. Removing the pollution helps
the neighbour *and* the stream. **That is the paper's thesis, and it is the
measured outcome.**

### And it is policy-invariant

The H2 *recovery* figure is policy-sensitive (`-2.25` pp, TreePLRU -> LRU,
`HNFRP_ROBUSTNESS_OUTCOME_2026-08-28.md`). The tenant-cost result is not:

| policy | tenant IPC | misses/cyc | misses/instruction |
|---|--:|--:|--:|
| TreePLRU | +10.38% | +10.38% | **+0.00%** |
| LRU | +10.36% | +10.36% | **+0.00%** |

## This corrects a metric in the paper, in the paper's favour

`tab:sens`'s caption currently argues the aggressor is not merely throttled:

> "its L2-miss rate per cycle falls 3.9\%"

That figure is **demand misses only**. Including prefetch traffic --- which is most
of it, 15.7 of 27.1 misses/kcyc --- the tenant's total L2 traffic per cycle
**rises 10.4%**. The `-3.9%` reads as a small cost when the true result is a gain,
and it is computed on a metric that excludes two thirds of the stream's traffic.

Replacement, stronger and correct:

> Under H2 the aggressor's L2 misses **per instruction** are unchanged (+0.00%,
> n=3) while its throughput rises **10.4%**: it is not throttled, and declining to
> admit a no-reuse stream costs the stream nothing.

## The H3 number the pending decision needs

H3 costs the streaming tenant **-26.4% IPC** and **+162.6% L2 misses per
instruction** at an infinite SF. The `3.45%` the paper attributes to H3 is the
**victim-side** charge only; the tenant-side charge is an order of magnitude
larger and is nowhere in the paper. H2 alone is Pareto-improving; H2+H3 is not.

Directly relevant to the open question of whether H3 stays a contract clause.

## Scope and caveats

- One configuration: 5 MiB LLC / 20-way, 2 O3 CPUs, 2 MiB L2, infinite SF,
  `SimpleMemory` with `latency_var=0`, aggressor 16 GB read-only, victim 2650 KiB.
- `SimpleMemory` cannot model congestion latency, so the congestion relief H2
  buys the tenant is if anything **under**-modelled --- the +10.4% is a lower bound
  in the same direction as every other gem5 magnitude here.
- The +10.4% is a *throughput* gain in a bandwidth-saturated 2-core model. It
  should not be reported as a general claim that streams get faster; the
  defensible claim is **zero per-instruction cost**, with the throughput gain as
  a configuration-specific consequence of removed congestion.
- Not silicon. On silicon the executable proxies (partitioning 15.0--16.9%,
  flush-behind 14--17%) still charge the tenant, and that gap between proxy and
  type is exactly what the paper must state plainly.
