#!/usr/bin/env bash
# W8 / T3: build vmlinux with CONFIG_PAT_STREAMING=y for the gem5 FS contract test.
#
# Committed before it is run (W1's launcher was typed at the shell and never
# committed, and reconstructing it cost a session).
#
# gcc: the host default is gcc 15.2, which is newer than Linux 6.8 supports.
# gcc-13 is installed and is the newest the tree accepts. Recorded here rather
# than left to whatever `cc` happens to be.
set -euo pipefail
K=${K:-$HOME/DutyFree/linux}
FRAG=${FRAG:-$(cd "$(dirname "$0")" && pwd)/streaming_gem5.fragment}
J=${J:-64}                       # -j 64 of 256, per the session prompt's courtesy cap
CC=${CC:-gcc-13}

cd "$K"
echo "== tree: $(git log --oneline -1)"
echo "== cc  : $($CC --version | head -1)"
make CC="$CC" -j"$J" x86_64_defconfig
./scripts/kconfig/merge_config.sh -m .config "$FRAG"
make CC="$CC" olddefconfig

# Gate T3.1 -- the symbol actually survived olddefconfig. `default n` plus an
# unmet dependency silently drops it, which is the failure this checks for.
for s in CONFIG_PAT_STREAMING CONFIG_X86_PAT CONFIG_PAT_STREAMING_KUNIT_TEST; do
  if grep -q "^${s}=y" .config; then echo "  OK  ${s}=y"
  else echo "  FAIL ${s} is not =y:"; grep -- "${s}" .config || echo "    (absent)"; exit 3; fi
done

time make CC="$CC" -j"$J" vmlinux
ls -la vmlinux
