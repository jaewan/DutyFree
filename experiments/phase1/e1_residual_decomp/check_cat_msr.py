#!/usr/bin/env python3
"""
Direct MSR-level verification of CAT enforcement, bypassing resctrl's
sysfs abstraction entirely. Reads IA32_PQR_ASSOC (0xC8F, holds the
CLOSID/RMID assigned to the executing core) and IA32_L3_QOS_MASK_n
(0xC90+n, the actual hardware way-mask for CLOSID n) directly via
/dev/cpu/N/msr, for cpu0 (victim) and cpu1 (aggressor) during a live
wb_cat-style run. This is the ground truth the resctrl sysfs schemata
file is supposed to reflect -- if these MSRs show the wrong mask despite
schemata reading back correctly, that's a kernel/hardware enforcement bug,
not a script bug.
"""
import os, struct, subprocess, time

PQR_ASSOC = 0xC8F
L3_MASK_BASE = 0xC90

RESCTRL = "/sys/fs/resctrl"
VGRP = f"{RESCTRL}/msrcheck_v"
AGRP = f"{RESCTRL}/msrcheck_a"
BIN = "/home/domin/tmp_dutyfree_exp/bin"


def read_msr(cpu, addr):
    fd = os.open(f"/dev/cpu/{cpu}/msr", os.O_RDONLY)
    try:
        val = os.pread(fd, 8, addr)
        return struct.unpack("<Q", val)[0]
    finally:
        os.close(fd)


def main():
    subprocess.run("pkill -f bin/aggressor 2>/dev/null", shell=True)
    time.sleep(0.3)
    os.makedirs(VGRP, exist_ok=True)
    os.makedirs(AGRP, exist_ok=True)
    open(f"{VGRP}/cpus_list", "w").write("0")
    open(f"{AGRP}/cpus_list", "w").write("1-7")
    open(f"{VGRP}/schemata", "w").write("L3:0=ff00\nSMBA:0=2048\n")
    open(f"{AGRP}/schemata", "w").write("L3:0=00ff\nSMBA:0=2048\n")

    agg = subprocess.Popen(
        f"{BIN}/aggressor -m wb_load -t 7 -c 1,2,3,4,5,6,7 -N 2 -s 64 -d 12 "
        f"> /tmp/msrcheck_agg.log 2>&1", shell=True)
    time.sleep(4)

    print("=== PQR_ASSOC (bits 0-9 = CLOSID on this AMD box, 16 closids -> 4 bits typically, but read raw) ===")
    for cpu in [0, 1, 2, 7, 8]:
        try:
            v = read_msr(cpu, PQR_ASSOC)
            print(f"cpu{cpu}: PQR_ASSOC=0x{v:016x}  (low32 CLOSID-ish field=0x{v & 0xffffffff:x}, "
                  f"high32 RMID-ish field=0x{(v >> 32) & 0xffffffff:x})")
        except Exception as e:
            print(f"cpu{cpu}: ERROR reading PQR_ASSOC: {e}")

    print()
    print("=== L3_QOS_MASK_n for n=0..15 (the actual programmed way-masks) ===")
    for n in range(16):
        try:
            v = read_msr(0, L3_MASK_BASE + n)
            print(f"L3_MASK_{n:2d} (0x{L3_MASK_BASE+n:x}): 0x{v:04x}")
        except Exception as e:
            print(f"L3_MASK_{n:2d}: ERROR: {e}")

    agg.terminate()
    try:
        agg.wait(timeout=10)
    except subprocess.TimeoutExpired:
        agg.kill()
        agg.wait()

    os.rmdir(VGRP)
    os.rmdir(AGRP)


if __name__ == "__main__":
    main()
