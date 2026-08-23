#!/usr/bin/env bash
# Compare the live instrument sources on each host against the vendored copy.
#
# Vendoring created a second copy of sources that every host still BUILDS FROM
# ~/tmp_dutyfree_exp. That is a drift hazard, not a fix for one, unless
# something checks. This is that check. Run it before any campaign that will be
# cited, and keep the output with the campaign's artifacts.
#
#   ./check_drift.sh              # all known hosts
#   ./check_drift.sh local c4     # a subset
#
# Exit 0 = every source present on every checked host matches the manifest.
#      1 = drift: data produced after it has ambiguous provenance.
#      2 = a host was unreachable.
# A source simply ABSENT on a host is reported, not counted as drift:
# amd_flushbehind_aggressor.c exists only on moscxl.
set -u
cd "$(dirname "$0")"

HOSTS=("$@"); [ ${#HOSTS[@]} -eq 0 ] && HOSTS=(local broker c4)
declare -A REAL=( [local]=mos181 [broker]=moscxl [c4]=mos182 )

echo "vendored manifest:"; sed 's/^/  /' MANIFEST.md5; echo

rc=0
for h in "${HOSTS[@]}"; do
    files=$(awk '{print "~/tmp_dutyfree_exp/" $2}' MANIFEST.md5 | tr '\n' ' ')
    cmd="md5sum $files 2>/dev/null"
    if [ "$h" = local ]; then out=$(eval "$cmd"); else out=$(ssh -o BatchMode=yes "$h" "$cmd"); fi
    label="${REAL[$h]:-$h} ($h)"

    if [ -z "$out" ]; then printf '%-18s UNREACHABLE\n' "$label"; rc=2; continue; fi

    bad=0 absent=""
    while read -r want path; do
        got=$(awk -v p="/$path" '$2 ~ p"$" {print $1}' <<<"$out")
        if   [ -z "$got" ];        then absent="$absent $path"
        elif [ "$got" != "$want" ]; then
            [ $bad -eq 0 ] && printf '%-18s DRIFT\n' "$label"
            printf '    %-32s %s (manifest %s)\n' "$path" "$got" "$want"; bad=1; rc=1
        fi
    done < MANIFEST.md5

    [ $bad -eq 0 ] && printf '%-18s match\n' "$label"
    [ -n "$absent" ] && printf '    absent on this host:%s\n' "$absent"
done
exit $rc
