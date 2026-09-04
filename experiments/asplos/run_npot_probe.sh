#!/usr/bin/env bash
# Empirical confirmation that a non-power-of-two Ruby set count costs real,
# reachable LLC capacity --- i.e. that reading CacheMemory::init() is right.
#
# Instrument: cyclic sequential sweep of a 6 MiB working set (npot_probe).
# Under LRU this is a step function in reachable capacity C:
#   C >= 6 MiB -> ~0 memory-side reads after the first pass
#   C <  6 MiB -> ~6 MiB of memory-side reads per pass
#
# Four cells. All four request an LLC that could hold 6 MiB *if the requested
# size were realized*; they differ only in whether (size/assoc)/64 is a power
# of two.
#
#   cell   --l3_size   --l3_assoc   sets = (size/assoc)/64   pow2?   realized
#   A      5MiB        20           4096                     yes     5.00 MiB
#   B      7680KiB     20           6144                     NO      5.00 MiB?
#   C      10MiB       20           8192                     yes     10.00 MiB
#   D      7680KiB     15           8192                     yes     7.50 MiB
#
# A is the floor control (a genuinely 5 MiB cache), C the ceiling control.
# D is the decisive control: the SAME requested 7680KiB as the r5 campaign, at
# an assoc that makes the set count a power of two. B and D therefore differ
# only in set-count arithmetic, not in requested bytes.
#
# Registered predictions, written before the runs (see NONPOW2_SETS_* record):
#   P1  A thrashes: memory read traffic ~= passes * 6 MiB, HNF demand hits ~0.
#   P2  C and D fit: memory read traffic ~= 6 MiB total (cold only).
#   P3  B behaves as A, NOT as D.  Stronger form: because B reaches exactly the
#       same 4096 sets x 20 ways at the same start_index_bit as A, every
#       simulated quantity in B should equal A's.
#   Falsifier: if B behaves as D, the source reading is wrong and everything
#   downstream of it must stop.
set -uo pipefail
G=${DUTYFREE_GEM5:-/home/domin/DutyFree/gem5}
cd "$G" || { echo "FAIL no $G" >&2; exit 2; }
BIN=${BIN:-build_Intel_8592/gem5.opt}
P=$G/testcase/dutyfree/npot_probe
for f in "$BIN" "$P"; do [ -x "$f" ] || { echo "FAIL missing $f" >&2; exit 2; }; done

OUTROOT=${OUTROOT:-$G/logs/se_npot_probe}
WS_KB=${WS_KB:-6144}
PASSES=${PASSES:-3}
mkdir -p "$OUTROOT"

# The campaign's own CHI config, with the campaign's own PF_OFF_CORES=0 to
# silence the L1D/L2 prefetchers: a capacity probe should not have to argue
# about what a stream prefetcher did.  (CHI_config_8592_nopf.py is not usable
# here --- it leaves system.ruby.hnf.cntrl.sf unset and fatals.)  LRU at the
# HNF so "thrash" and "fit" are exact rather than probabilistic: TreePLRU at
# assoc 20 is 2x-biased, see GEM5_TREEPLRU_NONPOW2_BIAS_2026-08-28.md.
COMMON="configs/deprecated/example/se.py --ruby --topology=Pt2Pt \
--chi-config=$G/configs/ruby/CHI_config_8592.py \
--num-l3caches=1 --num-dirs=1 --cpu-type=TimingSimpleCPU --num-cpus=1 \
--cpu-clock=1.9GHz \
--l1d_size=48KiB --l1d_assoc=12 --l1i_size=32KiB --l1i_assoc=8 \
--l2_size=2MiB --l2_assoc=16 \
--mem-type=SimpleMemory --mem-size=256GiB --cxl-mem-size=128GiB \
--dram-latency=98ns --cxl-latency=203ns"

one() {  # $1=cell $2=l3_size $3=l3_assoc
  local cell=$1 sz=$2 as=$3 out
  out=$OUTROOT/npot_${cell}
  rm -rf "$out"
  env HNF_RP=lru HNF_SF_FINITE=0 HNF_H3=0 HNF_DMT=0 HNF_FWD_UNIQUE=0 \
      SEQ_OUT=1024 PF_OFF_CORES=0 \
    "$BIN" --outdir="$out" $COMMON \
      --l3_size="$sz" --l3_assoc="$as" \
      -c "$P" --options "$WS_KB $PASSES" > "$out.log" 2>&1
  echo "DONE_$? CELL=$cell L3_SIZE=$sz L3_ASSOC=$as WS_KB=$WS_KB PASSES=$PASSES \
GEM5_SHA=$(sha256sum "$BIN" | cut -d' ' -f1) $(date +%s)" >> "$out.log"
}
export -f one; export BIN COMMON P OUTROOT WS_KB PASSES

echo "== reachable-LLC-capacity probe: 4 cells, ws=${WS_KB}KiB, passes=$PASSES"
echo "== binary $(sha256sum "$BIN" | cut -d' ' -f1)"
{ echo "A 5MiB 20"; echo "B 7680KiB 20"; echo "C 10MiB 20"; echo "D 7680KiB 15"; } \
  | xargs -P 4 -n 3 bash -c 'one "$0" "$1" "$2"'
echo "== all four cells returned"
