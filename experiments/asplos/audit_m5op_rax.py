#!/usr/bin/env python3
"""
Audit every gem5 m5op (magic instruction `0f 04 OP 00`) call site in an ELF
guest binary and decide whether any value the program still needs is live in
%rax across the instruction.

Why this is needed: gem5 decodes the magic instruction as
`BasicOperate::gem5Op` (arch/x86/isa/decoder/two_byte_opcodes.isa:159-166),
whose body ends in `Rax = result;` -- written UNCONDITIONALLY. For a void
m5op, pseudo_inst.hh:140 leaves `result = 0`, so the instruction zeroes %rax.
The wrappers in this tree declare no output operand and only "memory" as
clobbered, so the compiler believes %rax survives. Whether that belief is
harmful is a property of the compiler's SCHEDULE, not of the source, so it can
only be settled by disassembling the binary that actually ran.

Method
------
1. Enumerate sites by RAW BYTE SCAN of the PROGBITS sections, NOT from
   objdump's instruction stream. `0f 04` is an invalid opcode, so objdump
   renders it `(bad)` and desynchronizes; where the source emits two m5ops back
   to back (e.g. dump_stats() then reset_stats()) the second falls inside the
   first's desync shadow and never appears as a decoded line. An
   objdump-driven enumerator silently misses it. A byte scan is
   alignment-independent and cannot. This is not hypothetical: it hid two real
   sites in cxl_join_bench.gem5wbrk.
2. Walk the instruction stream forward from site+4, restarting objdump at each
   further m5op so the stream stays synchronized, and consuming objdump's
   multi-line byte continuations in order rather than treating them as
   instruction boundaries.
3. Look for a READ of %rax before any WRITE of %rax. A read-before-write means
   the compiler kept a live value there across an instruction that clobbers it
   => UNSAFE.

Terminating conditions, and why each is the conservative choice:
  - write to %rax/%eax (incl. the `xor %eax,%eax` / `sub %eax,%eax` zeroing
    idioms, lea, pop %rax, mov ...,%rax): the clobbered value is dead. SAFE.
  - `call`: %rax is caller-saved and the integer return register, so the
    compiler already cannot expect a value to survive a call and therefore
    never places a live value in %rax across one. SAFE.
  - a further m5op: also zeroes %rax, but is not a USE of it. Step over.
  - unconditional `jmp`: followed, up to two hops, since the question is only
    whether %rax is read before it is redefined. INDETERMINATE if unresolved.
  - `ret`: %rax is the return value register. If it is neither read nor written
    between the m5op and the ret, the function returns whatever the m5op left.
    INDETERMINATE, for manual adjudication -- safe iff the function is void.
  - conditional branch: sets flags, not %rax; the scan continues.

Known limits, stated because verdicts were adjudicated against them by hand:
  - Multi-byte NOP padding (`nopw 0x0(%rax,%rax,1)`) names %rax in an
    addressing-mode filler chosen for its encoding length. It is not a use, and
    is excluded explicitly.
  - The walk is linear plus two jmp hops. It does not do full CFG liveness, so
    a value live only along a path reached by a conditional branch could in
    principle be missed. Every non-SAFE verdict this tool produced was checked
    by hand against a widened disassembly window.
"""

import re
import subprocess
import sys
import collections

# Selector bytes actually used by wrappers in this tree, plus the rest of the
# range gem5 defines, so an unknown op is not silently skipped.
M5OP_NAMES = {
    0x21: "exit",
    0x40: "reset_stats",
    0x41: "dump_stats",
    0x42: "dump_reset_stats",
    0x43: "checkpoint",
    0x50: "work_begin",
    0x51: "work_end",
    0x53: "quiesce",
    0x54: "wake_cpu",
    0x55: "set_streaming",
    0x56: "bind_pool",
    0x57: "flush_range",
    0x5a: "switch_cpu",
    0x62: "add_symbol",
}

RAX_ALIASES = ("%rax", "%eax", "%ax", "%al", "%ah")

LINE = re.compile(r"^\s*([0-9a-f]+):\s+((?:[0-9a-f]{2} )+)\s*(.*)$")


def objdump(path, extra=()):
    cmd = ["objdump", "-d", *extra, path]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    return out


def parse(out):
    """Return list of (addr, bytes_list, text) and a map addr -> symbol."""
    insns = []
    symbols = {}
    cur_sym = None
    for line in out.splitlines():
        m = re.match(r"^([0-9a-f]+) <(.+)>:$", line)
        if m:
            cur_sym = m.group(2)
            symbols[int(m.group(1), 16)] = cur_sym
            continue
        m = LINE.match(line)
        if not m:
            continue
        addr = int(m.group(1), 16)
        bs = m.group(2).split()
        insns.append((addr, bs, m.group(3).strip(), cur_sym))
    return insns, symbols


def sections(path):
    """Executable PROGBITS sections as (name, vaddr, file_off, size)."""
    out = subprocess.run(["readelf", "-S", "-W", path],
                         capture_output=True, text=True).stdout
    secs = []
    for line in out.splitlines():
        m = re.match(r"\s*\[\s*\d+\]\s+(\S+)\s+(\S+)\s+([0-9a-f]+)\s+"
                     r"([0-9a-f]+)\s+([0-9a-f]+)", line)
        if m and m.group(2) == "PROGBITS":
            secs.append((m.group(1), int(m.group(3), 16),
                         int(m.group(4), 16), int(m.group(5), 16)))
    return secs


def find_sites(path):
    """Locate m5op sites by RAW BYTE SCAN of the section image.

    Deliberately not driven by objdump's instruction stream. `0f 04` is an
    invalid opcode, so objdump desynchronizes after every m5op; when two m5ops
    are emitted back to back -- which happens wherever the source calls e.g.
    dump_stats() immediately followed by reset_stats() -- the second one falls
    inside the first one's desync shadow and never appears as a decoded line.
    An objdump-driven enumerator silently misses it. A raw byte scan is
    alignment-independent and cannot.
    """
    data = open(path, "rb").read()
    syms = symbol_table(path)
    sites = []
    for name, va, off, size in sections(path):
        blob = data[off:off + size]
        for i in range(len(blob) - 3):
            if (blob[i] == 0x0F and blob[i + 1] == 0x04
                    and blob[i + 2] in M5OP_NAMES and blob[i + 3] == 0x00):
                a = va + i
                sites.append((a, blob[i + 2], sym_for(syms, a)))
    return sorted(sites)


def symbol_table(path):
    out = subprocess.run(["nm", "-C", "--defined-only", "-n", path],
                         capture_output=True, text=True).stdout
    syms = []
    for line in out.splitlines():
        m = re.match(r"^([0-9a-f]+)\s+[TtWwi]\s+(.*)$", line)
        if m:
            syms.append((int(m.group(1), 16), m.group(2)))
    return syms


def sym_for(syms, addr):
    best = None
    for a, n in syms:
        if a <= addr:
            best = n
        else:
            break
    return best or "?"


def is_m5op_at(path_bytes_cache, path, addr):
    """True if a 4-byte m5op begins at virtual address `addr`."""
    data = path_bytes_cache.setdefault(path, open(path, "rb").read())
    for name, va, off, size in sections(path):
        if va <= addr < va + size:
            i = off + (addr - va)
            b = data[i:i + 4]
            return (len(b) == 4 and b[0] == 0x0F and b[1] == 0x04
                    and b[2] in M5OP_NAMES and b[3] == 0x00)
    return False


def writes_rax(text):
    """Does this instruction define %rax (making a prior value dead)?"""
    if not text or "(bad)" in text:
        return False
    parts = text.split(None, 1)
    mnem = parts[0]
    ops = parts[1] if len(parts) > 1 else ""
    # strip comment
    ops = ops.split("#")[0]
    ops = ops.split("<")[0]
    if mnem.startswith("j") or mnem.startswith("ret") or mnem.startswith("call"):
        return False
    if mnem in ("pop", "popq") and any(r in ops for r in ("%rax", "%eax")):
        return True
    # cmp/test/push read but do not write their operands
    if mnem.startswith(("cmp", "test", "push")):
        return False
    dest = ops.split(",")[-1].strip() if "," in ops else ops.strip()
    if dest in ("%rax", "%eax", "%ax", "%al"):
        # xchg/add/sub/or/and etc. read-modify-write: they READ too.
        if mnem.startswith(("add", "sub", "or", "and", "xor", "adc", "sbb",
                            "shl", "shr", "sar", "rol", "ror", "imul", "inc",
                            "dec", "not", "neg", "xchg")):
            # xor %eax,%eax and sub %eax,%eax are idioms that only WRITE
            srcs = ops.split(",")[0].strip() if "," in ops else ""
            if mnem.startswith(("xor", "sub")) and srcs == dest:
                return True
            return "rmw"
        return True
    return False


def reads_rax(text):
    if not text or "(bad)" in text:
        return False
    parts = text.split(None, 1)
    mnem = parts[0]
    ops = parts[1] if len(parts) > 1 else ""
    ops = ops.split("#")[0].split("<")[0]
    if not any(r in ops for r in RAX_ALIASES):
        return False
    # Multi-byte NOP padding is encoded as e.g. `nopw 0x0(%rax,%rax,1)`. The
    # operand is an addressing-mode filler chosen for its encoding length; the
    # instruction has no effect and does not use the value in %rax.
    if mnem.startswith("nop"):
        return False
    # `xor %eax,%eax` / `sub %eax,%eax` are zeroing IDIOMS: architecturally the
    # source is read, but the result does not depend on it, so the incoming
    # value is dead. Treat as a pure write, not a read.
    parts2 = ops.split(",")
    if (mnem.startswith(("xor", "sub")) and len(parts2) == 2
            and parts2[0].strip() == parts2[1].strip()):
        return False
    # A pure write to %rax as destination is not a read.
    w = writes_rax(text)
    if w is True:
        # still a read if rax also appears as a source or in a memory operand
        srcs = ",".join(ops.split(",")[:-1])
        if any(r in srcs for r in RAX_ALIASES):
            return True
        # memory operand using rax as base/index on the dest side, e.g.
        # mov (%rax),%rax  -> dest is %rax but source dereferences rax
        return False
    return True


def walk(path, cache, start, limit=40):
    """Linear instruction stream from `start`.

    Two objdump artefacts have to be handled or the walk silently reads
    garbage:

    1. objdump splits a long instruction's bytes over several output lines,
       the continuation lines carrying an address in the MIDDLE of that
       instruction and no mnemonic. Those lines must be consumed in order and
       ignored, never treated as instruction boundaries.
    2. `0f 04` is an invalid opcode, so objdump desynchronizes on every m5op.
       When the walk reaches a further m5op we must restart objdump at that
       address + 4 rather than trust the desynced stream.
    """
    seq = []
    pc = start
    guard = 0
    while len(seq) < limit and guard < 16:
        guard += 1
        out = objdump(path, extra=[f"--start-address=0x{pc:x}",
                                   f"--stop-address=0x{pc + 400:x}"])
        insns, _ = parse(out)
        insns = [i for i in insns if i[0] >= pc]
        if not insns:
            break
        restarted = False
        for a, bs, text, _s in insns:
            if len(seq) >= limit:
                break
            if is_m5op_at(cache, path, a):
                # chained m5op: also zeroes %rax, but is not a USE of it
                seq.append((a, " ".join(bs[:4]), "<m5op>"))
                pc = a + 4
                restarted = True
                break
            seq.append((a, " ".join(bs), text))
        if not restarted:
            break
    return seq


def analyse(path, window=40):
    sites = find_sites(path)
    cache = {}
    results = []
    for addr, sel, sym in sites:
        verdict = "INDETERMINATE"
        why = "scan ran off the end of the window"
        trace = []
        stream = list(walk(path, cache, addr + 4, window))
        followed = 0
        i = 0
        while i < len(stream):
            a, bs, text = stream[i]
            i += 1
            trace.append((a, bs, text))
            if text == "<m5op>":
                # a chained m5op: also zeroes %rax, but is not a USE of it
                continue
            mnem = text.split(None, 1)[0] if text else ""
            if reads_rax(text):
                verdict = "UNSAFE"
                why = f"reads %rax at {a:x}: {text}"
                break
            if writes_rax(text) is True:
                verdict = "SAFE"
                why = f"%rax redefined at {a:x} before any use: {text}"
                break
            if mnem.startswith("call"):
                verdict = "SAFE"
                why = (f"call at {a:x} before any use of %rax; %rax is "
                       f"caller-saved and the return register, so no live "
                       f"value can be held in it across a call")
                break
            if mnem.startswith("ret"):
                verdict = "INDETERMINATE"
                why = (f"ret at {a:x} with %rax neither read nor written; "
                       f"safe iff the function returns void")
                break
            if mnem == "jmp":
                # Follow one hop: the question is only whether %rax is read
                # before it is redefined, and an unconditional jmp to a known
                # target keeps that decidable.
                m = re.search(r"([0-9a-f]{4,})", text.split(None, 1)[1])
                if m and followed < 2:
                    followed += 1
                    tgt = int(m.group(1), 16)
                    trace.append((tgt, "", f"-- follow jmp -> {tgt:#x} --"))
                    stream = stream[:i] + list(walk(path, cache, tgt, window))
                    i = len(trace) - 1
                    stream = list(walk(path, cache, tgt, window))
                    i = 0
                    continue
                verdict = "INDETERMINATE"
                why = f"unconditional jmp at {a:x}: {text} (follow by hand)"
                break
        results.append(dict(addr=addr, sel=sel,
                            name=M5OP_NAMES.get(sel, f"?{sel:#x}"),
                            sym=sym, verdict=verdict, why=why, trace=trace))
    return results


def main():
    for path in sys.argv[1:]:
        print("=" * 78)
        print(path)
        print("=" * 78)
        res = analyse(path)
        if not res:
            print("  no m5op sites found")
            continue
        counts = collections.Counter(r["verdict"] for r in res)
        for r in res:
            print(f"\n-- {r['addr']:#x}  {r['name']} (0x{r['sel']:02x})  in <{r['sym']}>")
            print(f"   VERDICT: {r['verdict']} -- {r['why']}")
            for a, bs, t in r["trace"][:10]:
                print(f"      {a:8x}: {bs:24s} {t}")
        print(f"\n  SUMMARY {path}: {dict(counts)}  ({len(res)} sites)")


if __name__ == "__main__":
    main()
