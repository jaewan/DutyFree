# Action item for whoever has BIOS/physical access to mos181 (EMR host)

**One-line summary**: the CXL card in slot `27:00.0` negotiates PCIe x8
instead of its advertised x16 capability, and single-core CXL read bandwidth
is capped around ~8.9 GB/s as a result (vs. ~14.2 GB/s the same core gets
from local DRAM). Full diagnosis in `REPRO_FAILURE.md` in this directory.

## What's confirmed (no BIOS access needed, already done)

- Not a CPU frequency/governor artifact (turbostat confirms full 1.9 GHz,
  100% busy during the measurement).
- Not a software/kernel-choice artifact (a scalar loop and a 4-register
  AVX2-unrolled loop agree on both nodes: ~8-9 GB/s on CXL, ~14.2 GB/s local).
- Not a downstream switch/bridge issue — `27:00.0` is a Root Complex
  Integrated Endpoint wired directly to the CPU's on-die CXL root port, no
  intermediate device to blame.
- The card itself is a Montage Technology M88MX5891 (Samsung-branded),
  replacing a Micron CXL 2.0 Device 6400 that was in this slot as of May 2026
  (see `../e4_hygiene/PLATFORMS.md`) — a physical swap happened at some point
  between then and now.

## What needs physical/BIOS access

1. **Check BIOS CXL/PCIe bifurcation settings** for the slot/riser hosting
   `27:00.0` on this board (Intel `M50FCP2SBSTD`, BIOS
   `SE5C741.86B.01.02.0005.2512081849`). Look for any setting that would
   split/limit lanes to that slot to x8.
2. **Physically inspect the riser/slot wiring** if the BIOS setting doesn't
   explain it — some server risers only route 8 of 16 physical lanes to a
   given card slot regardless of BIOS configuration.
3. **After any change**, re-verify with:
   ```
   lspci -vvv -s 27:00.0 | grep -E "LnkCap|LnkSta"
   gcc -O2 -march=native -mavx2 -o /tmp/mlp_probe experiments/phase1/e2_h1_speed/mlp_probe.c -lnuma
   /tmp/mlp_probe 1 2 16 8   # cpu=1 node=2(CXL) region=16GiB duration=8s
   ```
   If `LnkSta` reads `x16` and `avg_bw_gbps` moves well above ~9, the fix
   worked — re-run E2a/E2b/E3 at that point.

## What does NOT need this fix first

The genuine Intel paper reproduction gate (8-thread aggregate ~34 GB/s WB,
2.03x/0.99x tax numbers in `tab:catmba`/`tab:h1bw`) has not been tested in
this campaign and does not depend on the single-core question above — an
aggregate multi-thread ceiling is not automatically bounded by one thread's
core-side MLP limit. That should be tested directly, independent of this
BIOS item.
