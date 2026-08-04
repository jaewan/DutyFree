#!/usr/bin/env python3
import re, sys
def g(s, pat):
    for ln in open(s):
        if re.search(pat, ln):
            try: return float(ln.split()[1])
            except: pass
    return None
for n in sys.argv[1:]:
    s = f"/tmp/{n}/stats.txt"
    ss = g(s, r"^simSeconds\b")
    br0 = g(s, r"system\.mem_ctrls0\.bytesRead::total") or 0
    br1 = g(s, r"system\.mem_ctrls1\.bytesRead::total") or 0
    ac = g(s, r"^system\.cpu1\.numCycles\b")
    # aggressor active time from its own committed cycles (proxy: cpu1 numCycles ~ whole sim; use simSeconds)
    print(f"{n}: simSec={ss*1e3:.3f}ms  DRAM0_read={br0/1e6:.2f}MB  CXL1_read={br1/1e6:.1f}MB  "
          f"CXL_BW={br1/ss/1e9:.2f}GB/s  totRead_BW={(br0+br1)/ss/1e9:.2f}GB/s")
