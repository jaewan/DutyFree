#!/usr/bin/env python3
"""Diagnostic: verify CAT schemata takes effect and stays stable during a
live aggressor run, for the wb_cat drift investigation."""
import subprocess, time, os

RESCTRL = "/sys/fs/resctrl"
VGRP = f"{RESCTRL}/checkv"
AGRP = f"{RESCTRL}/checka"
BIN = "/home/domin/tmp_dutyfree_exp/bin"

subprocess.run("pkill -f bin/aggressor 2>/dev/null", shell=True)
time.sleep(0.3)
os.makedirs(VGRP, exist_ok=True)
os.makedirs(AGRP, exist_ok=True)
open(f"{VGRP}/cpus_list", "w").write("0")
open(f"{AGRP}/cpus_list", "w").write("1-7")
open(f"{VGRP}/schemata", "w").write("L3:0=ff00\nSMBA:0=2048\n")
open(f"{AGRP}/schemata", "w").write("L3:0=00ff\nSMBA:0=2048\n")
print("last_cmd_status:", open(f"{RESCTRL}/info/last_cmd_status").read().strip())
print("VGRP schemata readback:", open(f"{VGRP}/schemata").read().strip())
print("AGRP schemata readback:", open(f"{AGRP}/schemata").read().strip())
print("VGRP mode:", open(f"{VGRP}/mode").read().strip())
print("AGRP mode:", open(f"{AGRP}/mode").read().strip())

agg = subprocess.Popen(
    f"{BIN}/aggressor -m wb_load -t 7 -c 1,2,3,4,5,6,7 -N 2 -s 64 -d 12 "
    f"> /tmp/checkagg.log 2>&1", shell=True)
time.sleep(4)
print("DURING RUN VGRP schemata:", open(f"{VGRP}/schemata").read().strip())
print("DURING RUN AGRP schemata:", open(f"{AGRP}/schemata").read().strip())
print("DURING RUN last_cmd_status:", open(f"{RESCTRL}/info/last_cmd_status").read().strip())
agg.wait(timeout=20)

os.rmdir(VGRP)
os.rmdir(AGRP)
print("done")
