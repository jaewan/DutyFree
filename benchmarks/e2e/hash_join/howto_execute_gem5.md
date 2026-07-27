# gem5 Execution: hash_join W1-W4 (SE / FS, Intel EMR 8592)

Workloads:
  W1(original)     = H1 pure-stream input (full-read)
  W1(line-stride)  = H1 pure-stream input + --line-stride (one 8B load per 64B line)
  W2               = Quiescent hot-table baseline (probe-workload)
  W3               = Loaded morsel baseline (WB)
  W4               = Loaded morsel H2

SE mode runs W1-W4.
FS mode runs W1-W3.
FS W4 needs a Linux kernel change.
Only the Intel EMR (8592) configuration is validated so far.

## 0. Build

# gem5 -- DutyFree-Gem5 repo, branch intel_streaming_tax
cd DutyFree/gem5
python3.11 $(which scons) defconfig  build_Intel_8592 build_opts/X86
python3.11 $(which scons) setconfig  build_Intel_8592 PROTOCOL=CHI \
    RUBY_PROTOCOL_MESI_Two_Level=n RUBY_PROTOCOL_CHI=y NUMBER_BITS_PER_SET=256
python3.11 $(which scons) build_Intel_8592/gem5.opt -j$(nproc)

# SE workload binary
cd DutyFree/benchmarks/e2e/hash_join_gem5se && make   # -> build/cxl_join_bench.gem5se

# FS workload binary (section 2)
cd DutyFree/benchmarks/e2e/hash_join_gem5fs && make   # -> build/cxl_join_bench.gem5fs

---

## 1. SE mode

### 1.1 W1(original)

W1 streams a single fact buffer (sit on the CXL): set ALL_CXL=1 (gem5 SE has no mbind; this env is the simplest way to put every allocation on the CXL range).

cd DutyFree/gem5
env RUBY_RANDOMIZATION=1 ALL_CXL=1 \
    L1_MSHR=16 PF_DEGREE_L1=4 PF_DEGREE_L2=8 PF_PAGE=4KiB \
build_Intel_8592/gem5.opt --outdir=logs/se_w1_orig \
  configs/deprecated/example/se.py \
  --cmd=../benchmarks/e2e/hash_join_gem5se/build/cxl_join_bench.gem5se \
  --options="--mode stream-smoke --policy wb --fact-bytes 1g --fact-node 1 \
             --threads 1 --cpu-list 0 --warmups 1 --reps 3" \
  --ruby --topology=Pt2Pt --chi-config=configs/ruby/CHI_config_8592.py \
  --num-l3caches=1 --num-dirs=1 \
  --cpu-type=O3CPU --num-cpus=1 --cpu-clock=1.9GHz \
  --l1d_size=48KiB --l1d_assoc=12 --l1i_size=32KiB --l1i_assoc=8 \
  --l2_size=2MiB --l2_assoc=16 --l3_size=5MiB --l3_assoc=20 \
  --mem-type=SimpleMemory --mem-size=16GiB --cxl-mem-size=8GiB \
  --dram-latency=98ns --cxl-latency=203ns

### 1.2 W1(line-stride)

cd DutyFree/gem5
env RUBY_RANDOMIZATION=1 ALL_CXL=1 \
    L1_MSHR=16 PF_DEGREE_L1=4 PF_DEGREE_L2=8 PF_PAGE=4KiB \
build_Intel_8592/gem5.opt --outdir=logs/se_w1_ls \
  configs/deprecated/example/se.py \
  --cmd=../benchmarks/e2e/hash_join_gem5se/build/cxl_join_bench.gem5se \
  --options="--mode stream-smoke --policy wb --fact-bytes 1g --fact-node 1 \
             --threads 1 --cpu-list 0 --warmups 1 --reps 3 --line-stride" \
  --ruby --topology=Pt2Pt --chi-config=configs/ruby/CHI_config_8592.py \
  --num-l3caches=1 --num-dirs=1 \
  --cpu-type=O3CPU --num-cpus=1 --cpu-clock=1.9GHz \
  --l1d_size=48KiB --l1d_assoc=12 --l1i_size=32KiB --l1i_assoc=8 \
  --l2_size=2MiB --l2_assoc=16 --l3_size=5MiB --l3_assoc=20 \
  --mem-type=SimpleMemory --mem-size=16GiB --cxl-mem-size=8GiB \
  --dram-latency=98ns --cxl-latency=203ns

### 1.3 W2

DRAM/CXL placement uses gem5_bind_pool() (SE stand-in for mbind).
Default placement to the DRAM pool (hot table on DRAM)
and only the fact region is placed onto the CXL pool (--fact-node 1).

Number of cores / hot-bytes listed below.
Example N=8.
# N core / hot-bytes (= 53% of N x 5MiB LLC):
#   2 core  -> 5557452     4 core  -> 11114905
#   8 core  -> 22229811    16 core -> 44459622

cd DutyFree/gem5
env RUBY_RANDOMIZATION=1 \
    L1_MSHR=16 PF_DEGREE_L1=4 PF_DEGREE_L2=8 PF_PAGE=4KiB \
build_Intel_8592/gem5.opt --outdir=logs/se_w2_8c \
  configs/deprecated/example/se.py \
  --cmd=../benchmarks/e2e/hash_join_gem5se/build/cxl_join_bench.gem5se \
  --options="--mode probe-workload --policy wb --fact-bytes 1g \
             --hot-bytes 22229811 --fact-node 1 --hot-node 0 \
             --threads 8 --cpu-list 0-7 --warmups 1 --reps 3" \
  --ruby --topology=Pt2Pt --chi-config=configs/ruby/CHI_config_8592.py \
  --num-l3caches=8 --num-dirs=1 \
  --cpu-type=O3CPU --num-cpus=8 --cpu-clock=1.9GHz \
  --l1d_size=48KiB --l1d_assoc=12 --l1i_size=32KiB --l1i_assoc=8 \
  --l2_size=2MiB --l2_assoc=16 --l3_size=5MiB --l3_assoc=20 \
  --mem-type=SimpleMemory --mem-size=256GiB --cxl-mem-size=128GiB \
  --dram-latency=98ns --cxl-latency=203ns

### 1.4 W3

gem5 SE has no scheduler, so it implements threads by pinning one thread to one cpu (thread count must not exceed cpu count).
A morsel run spawns N worker threads plus a main thread that only waits, so it needs N+1 cpus.
Therefore --num-cpus = N+1, while --num-l3caches stays N (LLC scales with workers).
Example N=8 (num-cpus=9).

cd DutyFree/gem5
env RUBY_RANDOMIZATION=1 \
    L1_MSHR=16 PF_DEGREE_L1=4 PF_DEGREE_L2=8 PF_PAGE=4KiB \
build_Intel_8592/gem5.opt --outdir=logs/se_w3_8c \
  configs/deprecated/example/se.py \
  --cmd=../benchmarks/e2e/hash_join_gem5se/build/cxl_join_bench.gem5se \
  --options="--mode morsel --policy wb --fact-bytes 1g \
             --hot-bytes 22229811 --fact-node 1 --hot-node 0 \
             --threads 8 --cpu-list 0-8 --morsel 1m --warmups 1 --reps 3 --check" \
  --ruby --topology=Pt2Pt --chi-config=configs/ruby/CHI_config_8592.py \
  --num-l3caches=8 --num-dirs=1 \
  --cpu-type=O3CPU --num-cpus=9 --cpu-clock=1.9GHz \
  --l1d_size=48KiB --l1d_assoc=12 --l1i_size=32KiB --l1i_assoc=8 \
  --l2_size=2MiB --l2_assoc=16 --l3_size=5MiB --l3_assoc=20 \
  --mem-type=SimpleMemory --mem-size=256GiB --cxl-mem-size=128GiB \
  --dram-latency=98ns --cxl-latency=203ns

### 1.5 W4

Identical to W3 with --policy stream.
H2 is implemented as gem5_set_streaming.

cd DutyFree/gem5
env RUBY_RANDOMIZATION=1 \
    L1_MSHR=16 PF_DEGREE_L1=4 PF_DEGREE_L2=8 PF_PAGE=4KiB \
build_Intel_8592/gem5.opt --outdir=logs/se_w4_8c \
  configs/deprecated/example/se.py \
  --cmd=../benchmarks/e2e/hash_join_gem5se/build/cxl_join_bench.gem5se \
  --options="--mode morsel --policy stream --fact-bytes 1g \
             --hot-bytes 22229811 --fact-node 1 --hot-node 0 \
             --threads 8 --cpu-list 0-8 --morsel 1m --warmups 1 --reps 3 --check" \
  --ruby --topology=Pt2Pt --chi-config=configs/ruby/CHI_config_8592.py \
  --num-l3caches=8 --num-dirs=1 \
  --cpu-type=O3CPU --num-cpus=9 --cpu-clock=1.9GHz \
  --l1d_size=48KiB --l1d_assoc=12 --l1i_size=32KiB --l1i_assoc=8 \
  --l2_size=2MiB --l2_assoc=16 --l3_size=5MiB --l3_assoc=20 \
  --mem-type=SimpleMemory --mem-size=256GiB --cxl-mem-size=128GiB \
  --dram-latency=98ns --cxl-latency=203ns

---

## 2. FS mode

Boot -> checkpoint -> restore (O3CPU + Ruby + EMR config)
Placement uses the guest kernel's real mbind (not gem5_bind_pool): the workload passes --fact-node 1 --hot-node 0 exactly as native.

### 2.1 Disk image + kernel (one-time)

# kernel: compile DutyFree/linux (STREAMING branch) -> vmlinux.
# gem5 FS boot notes:
#   (1) disable CPU_SUP_AMD + CPU_SUP_HYGON (else the AMD FCH MMIO read panics on gem5).
#   (2) kernel cmdline root=/dev/sda1.
#   (3) 4-cpu boot must use hack_back_ckpt_delay5.rcS (default rcS hits a livelock).

# disk image: download the gem5-resources x86-ubuntu-18.04 image,
# then install the FS binary into a copy (partition 1 at offset 1048576).
wget http://dist.gem5.org/dist/v22-1/images/x86/ubuntu-18-04/x86-ubuntu.img.gz
gunzip x86-ubuntu.img.gz
cp x86-ubuntu.img x86-ubuntu-18.04-img-hashjoin
sudo mount -o loop,offset=1048576 x86-ubuntu-18.04-img-hashjoin /mnt
sudo cp DutyFree/benchmarks/e2e/hash_join_gem5fs/build/cxl_join_bench.gem5fs /mnt/root/
sudo umount /mnt

# gem5 FS needs M5_PATH set to an existing dir (kernel/disk are absolute, so any
# existing dir works). The scripts default it to $HOME/.cache/gem5; override if
# your image lives elsewhere:  M5_PATH=/your/path scripts/fs_boot_checkpoint.sh 2

### 2.2 Boot + checkpoint

Atomic boot + checkpoint; example is 2-cpu (change the core count as needed).
The checkpoint is reusable: core/cache config is applied at restore, not stored here.
Memory layout is fixed (DRAM 128GiB + CXL 128GiB) for every core count.

cd DutyFree/gem5
DISK=x86-ubuntu-18.04-img-hashjoin scripts/fs_boot_checkpoint.sh 2

# 4-cpu needs delay5 (note 3); all other core counts use the plain command above.
SCRIPT_OVERRIDE=configs/boot/hack_back_ckpt_delay5.rcS \
  DISK=x86-ubuntu-18.04-img-hashjoin scripts/fs_boot_checkpoint.sh 4

# This produces a reusable boot checkpoint:
#   logs/fs_boot_ckpt/atomic_2cpu_hashjoin/

### 2.3 Restore + run (W1-W3)

Restore the checkpoint from 2.2 and run one workload.
Two inputs: the checkpoint name (atomic_2cpu_hashjoin) and an rcS holding the workload command (same --options as SE, but the FS binary path and no gem5-side placement env -- the guest kernel does mbind).

cd DutyFree/gem5

# (a) save the workload command as w3_2c.rcS -- example: W3 on 2 cpu
#   contents of w3_2c.rcS:
#     /root/cxl_join_bench.gem5fs --mode morsel --policy wb --fact-bytes 1g \
#       --hot-bytes 5557452 --fact-node 1 --hot-node 0 \
#       --threads 2 --cpu-list 0-1 --morsel 1m --warmups 1 --reps 3 --check
#     m5 exit

# (b) restore + run:  fs_restore_chi_8592.sh <checkpoint> <run-name> <rcS>
scripts/fs_restore_chi_8592.sh atomic_2cpu_hashjoin fs_w3_2c w3_2c.rcS

# (c) result (console + JSON):
#   logs/fs_restore_chi/fs_w3_2c/system.pc.com_1.device

# other workloads: reuse the same checkpoint, change only the rcS command line
#   W1(original):    --mode stream-smoke --policy wb   (drop --hot-bytes/--morsel/--check)
#   W1(line-stride): add --line-stride
#   W2:              --mode probe-workload --policy wb

### 2.4 FS W4 -- kernel change needed

The STREAMING kernel gates MAP_STREAMING to device-DAX fds; FS W4 needs that gate to accept anonymous/mbind memory.
