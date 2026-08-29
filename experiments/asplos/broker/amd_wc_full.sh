#!/usr/bin/env bash
# (b) The real WC path, matched rate. Offline the CXL window, load the WC/UC
# module, VALIDATE the reconstruction, run the experiment, RESTORE.
#
# The window is online System RAM on this host, so mapping it WC while the
# kernel holds it WB would alias cache attributes on live pages. It is therefore
# offlined first and re-onlined on every exit path, including failure.
set -uo pipefail
BASE=0x18400000000
LEN=$((8*1024*1024*1024))
KMOD=$HOME/DutyFree/amd_cat/kmod
A=/home/domin/tmp_dutyfree_exp/bin/aggressor
V=/home/domin/tmp_dutyfree_exp/bin/victim
OFF=/tmp/offlined_blocks.txt; : > "$OFF"
OUT=$HOME/DutyFree/amd_cat/data/wc_matched.jsonl

restore() {
  echo "== RESTORE =="
  pkill -f 'bin/aggressor' 2>/dev/null
  sudo -n rmmod cxl_memtype_RECONSTRUCTED 2>/dev/null && echo "  module unloaded"
  local n=0
  while read -r b; do
    sudo -n sh -c "echo online > /sys/devices/system/memory/$b/state" 2>/dev/null && n=$((n+1))
  done < "$OFF"
  echo "  re-onlined $n blocks; node2 MemTotal = $(awk '/MemTotal/{print $4}' /sys/devices/system/node/node2/meminfo) kB"
}
trap restore EXIT

echo "== offlining node2 (was $(awk '/MemTotal/{print $4}' /sys/devices/system/node/node2/meminfo) kB) =="
ok=0
for l in /sys/devices/system/node/node2/memory*; do
  b=$(basename "$l")
  sudo -n sh -c "echo offline > /sys/devices/system/memory/$b/state" 2>/dev/null && { echo "$b" >> "$OFF"; ok=$((ok+1)); }
done
echo "  offlined $ok blocks; node2 now $(awk '/MemTotal/{print $4}' /sys/devices/system/node/node2/meminfo) kB"
[ "$ok" -gt 0 ] || { echo "FAIL no blocks offlined" >&2; exit 3; }

echo "== finding a contiguous OFFLINE window (37 blocks held unmovable pages) =="
BS=$(cat /sys/devices/system/memory/block_size_bytes)
BS=$((16#$BS))
read -r NEWBASE NEWLEN < <(python3 - "$BS" <<'PYX'
import sys, os, glob
bs=int(sys.argv[1])
off=[]
for d in glob.glob("/sys/devices/system/memory/memory*"):
    n=int(os.path.basename(d)[6:])
    try:
        if open(d+"/state").read().strip()=="offline": off.append(n)
    except OSError: pass
off.sort()
# longest run of consecutive offline blocks inside the CXL window
lo=0x18400000000//bs
best=(0,None); cur=[]
for n in off:
    if n < lo: continue
    if cur and n==cur[-1]+1: cur.append(n)
    else: cur=[n]
    if len(cur)>best[0]: best=(len(cur),cur[0])
cnt,start=best
if not start or cnt<4: print("0 0")
else:
    # leave a block of margin at each end
    print((start+1)*bs, min(8*1024**3, (cnt-2)*bs))
PYX
)
echo "  contiguous offline window: base=$NEWBASE len=$NEWLEN ($((NEWLEN>>20)) MiB)"
[ "$NEWLEN" -gt 0 ] || { echo "FAIL no contiguous offline window >=4 blocks" >&2; exit 5; }
BASE=$NEWBASE; LEN=$NEWLEN
echo "== loading module =="
sudo -n insmod "$KMOD/cxl_memtype_RECONSTRUCTED.ko" base=$BASE len=$LEN 2>&1 | head -2
[ -e /dev/cxl_wc ] || { echo "FAIL /dev/cxl_wc absent" >&2; exit 4; }
sudo -n chmod a+r /dev/cxl_wc /dev/cxl_uc 2>/dev/null
echo "  devices: $(ls /dev/cxl_wc /dev/cxl_uc 2>/dev/null | tr '\n' ' ')"

echo "== VALIDATION vs frozen figures (single core: WB 12.43, WC 3.20 GB/s) =="
for m in wb_load wc_ntdqa; do
  bw=$($A -m $m -t 1 -c 1 -N 2 -s 64 -d 6 2>&1 | grep '^aggregate:' | awk '{print $2}')
  echo "   $m = ${bw:-FAIL} GB/s"
done

echo "== bandwidth calibration for rate matching =="
for t in 7 10 14; do
  cl=$(python3 -c "
c=[str(x) for x in range(1,8)]+[str(256+x) for x in range(1,8)]
print(','.join(c[:$t]))")
  bw=$($A -m wc_ntdqa -t $t -c $cl -N 2 -s 64 -d 6 2>&1 | grep '^aggregate:' | awk '{print $2}')
  echo "   wc_ntdqa t=$t -> ${bw:-FAIL} GB/s"
done

echo "== EXPERIMENT: matched-rate allocation dissociation =="
python3 - "$OUT" <<'PY'
import json,subprocess,sys,time,os
A="/home/domin/tmp_dutyfree_exp/bin/aggressor"; V="/home/domin/tmp_dutyfree_exp/bin/victim"
C7="1,2,3,4,5,6,7"; C14="1,2,3,4,5,6,7,257,258,259,260,261,262,263"
ARMS=[("quiescent",None,None,0),("wb_load",  "wb_load", C7, 7),
      ("wc_7",     "wc_ntdqa",C7, 7),("wc_14","wc_ntdqa",C14,14)]
out=sys.argv[1]; recs=[]
def one(name,mode,cores,t,rep):
    agg=None;bw=None
    if mode:
        agg=subprocess.Popen(f"{A} -m {mode} -t {t} -c {cores} -N 2 -s 64 -d 12 > /tmp/wc_agg.log 2>&1",shell=True)
        time.sleep(2)
    p=subprocess.run(f"{V} -c 0 -w 4096 -P -d 5 -W 2",shell=True,capture_output=True,text=True)
    line=next((l for l in p.stdout.splitlines() if l.startswith("VICTIM")),"")
    d={}
    for tok in line.split():
        if "=" in tok:
            k,v=tok.split("=",1)
            try: d[k]=float(v)
            except ValueError: d[k]=v
    if agg:
        agg.wait(timeout=30)
        for l in open("/tmp/wc_agg.log",errors="replace"):
            if l.startswith("aggregate:"): bw=float(l.split()[1])
    r=dict(arm=name,rep=rep,cyc_per_access=d.get("cyc_per_access"),
           l2_miss_rate=d.get("l2_miss_rate"),agg_gbps=bw)
    print(f"   {name:10s} rep{rep} cyc/acc={r['cyc_per_access']:9.2f} "
          f"L2miss={r['l2_miss_rate']:6.2f}% bw={bw if bw else 0:6.2f}",flush=True)
    return r
for rep in range(1,7):
    order=ARMS[rep%len(ARMS):]+ARMS[:rep%len(ARMS)]
    for (n,m,c,t) in order: recs.append(one(n,m,c,t,rep))
with open(out,"w") as f:
    for x in recs: f.write(json.dumps(x)+"\n")
print(f"   wrote {len(recs)} -> {out}")
PY
echo "== experiment done; restoring =="
