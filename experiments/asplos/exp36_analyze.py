import statistics as st, collections
rows=collections.defaultdict(list); bw=collections.defaultdict(list)
for ln in open("/tmp/exp36_results.tsv"):
    a=ln.rstrip("\n").split("\t")
    if len(a)!=7 or a[0]=="arm": continue
    arm,rep,node,cores,cat,b,ip=a
    if ip=="NA": continue
    rows[arm].append(float(ip)); bw[arm].append(float(b))
base=st.median(rows["baseline"])
print("baseline IPC=%.4f n=%d" % (base,len(rows["baseline"])))
order=["cxl_nocat","cxl_cat","dram_nocat","dram_cat",
       "cxlcat_t1","cxlcat_t2","cxlcat_t3","cxlcat_t5","diffccx"]
print("%-11s %2s %7s %7s %6s" % ("arm","n","aggBW","IPC","tax"))
for k in order:
    if k not in rows: continue
    ip=st.median(rows[k]); b=st.median(bw[k]); tax=base/ip
    print("%-11s %2d %7.2f %7.4f %6.2f" % (k,len(rows[k]),b,ip,tax))
print("--- key contrasts ---")
def tax(k): return base/st.median(rows[k]) if k in rows else float('nan')
print("CXL+CAT residual   = %.2fx" % tax("cxl_cat"))
print("DRAM+CAT residual  = %.2fx  (#1: ~equal => residual NOT CXL-specific)" % tax("dram_cat"))
print("diff-CCX tax       = %.2fx  (#3: placement partial if >1.05)" % tax("diffccx"))
