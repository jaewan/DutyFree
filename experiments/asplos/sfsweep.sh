#!/usr/bin/env bash
# Victim-alone SF-size sweep: find the SF entry count where cyc/iter returns to
# the infinite-SF baseline (~33.83) with no aggressor (i.e., SF just holds the
# victim's ~42K-line working set without self-thrashing).
set -u
for cfg in 2048:16 4096:16 8192:16 16384:16 32768:16; do
  s=${cfg%:*}; w=${cfg#*:}; ent=$((s*w))
  HNF_SF_SETS=$s HNF_SF_WAYS=$w HNF_DMT=0 /tmp/b4run.sh sfk_${ent} alone 1 0 &
done
wait
echo "SWEEP_DONE" > /tmp/sfsweep.done
