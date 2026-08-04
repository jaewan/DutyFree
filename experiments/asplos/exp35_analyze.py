import statistics as st, collections
rows=collections.defaultdict(list); bw=collections.defaultdict(list)
for ln in open("/tmp/exp35_results.tsv"):
    a=ln.strip().split("\t")
    if len(a)!=5 or a[0]=="arm": continue
    arm,rep,smba,b,ip=a
    if ip=="NA": continue
    rows[arm].append(float(ip)); bw[arm].append(float(b))
base=st.median(rows["baseline"])
full=24.1
print("baseline IPC median=%.4f  n=%d" % (base, len(rows["baseline"])))
order=["wb_full","cat_8_8","wc_nonalloc","smba_2048","smba_256","smba_192",
       "smba_128","smba_96","smba_64","smba_48","smba_32","cat_smba_512","cat_smba_128"]
print("%-14s %2s %7s %7s %6s %6s" % ("arm","n","aggBW","IPC","tax","%ofBW"))
for k in order:
    if k not in rows: continue
    ip=st.median(rows[k]); b=st.median(bw[k]); tax=base/ip; pct=100*b/full
    print("%-14s %2d %7.2f %7.4f %6.2f %6.0f" % (k,len(rows[k]),b,ip,tax,pct))
