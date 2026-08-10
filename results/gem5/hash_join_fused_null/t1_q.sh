set -euo pipefail
cd /home/domin/DutyFree
RUBY_RANDOMIZATION=1 L1_MSHR=16 PF_DEGREE_L1=4 PF_DEGREE_L2=8 PF_PAGE=4KiB /home/domin/DutyFree-Gem5/build_Intel_8592/gem5.opt --outdir=/home/domin/DutyFree/results/gem5/hash_join_fused_null/stats/t1_q \
  /home/domin/DutyFree/gem5/configs/deprecated/example/se.py --cmd=/home/domin/DutyFree/benchmarks/e2e/hash_join/build/cxl_join_bench.gem5 \
  --options='--mode probe-workload --policy wb --fact-bytes 16m --fact-node 1 --hot-node 0 --hot-bytes 2778726 --threads 1 --cpu-list 0 --warmups 1 --reps 3 ' \
  --ruby --topology=Pt2Pt --chi-config=/home/domin/DutyFree/gem5/configs/ruby/CHI_config_8592.py \
  --num-l3caches=1 --num-dirs=1 --cpu-type=O3CPU --num-cpus=2 --cpu-clock=1.9GHz \
  --l1d_size=48KiB --l1d_assoc=12 --l1i_size=32KiB --l1i_assoc=8 \
  --l2_size=256KiB --l2_assoc=8 \
  --l3_size=5MiB --l3_assoc=20 \
  --mem-type=SimpleMemory --mem-size=256GiB --cxl-mem-size=128GiB \
  --dram-latency=98ns --cxl-latency=203ns
