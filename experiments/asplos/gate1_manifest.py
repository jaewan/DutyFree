#!/usr/bin/env python3
"""
Gate 1 manifest dumper -- the gem5-side equivalent of the silicon
campaign's env_manifest.py. Walks a completed run's config.json
(post-instantiation, not the command line's stated intent) and extracts
the specific parameters Gate 1's reconciliation table needs, plus
run provenance (commit SHA, dirty-tree flag, command line, env vars).

Usage: python3 gate1_manifest.py <outdir> [--cmdline "..."] [--gem5-repo PATH]
Writes <outdir>/manifest.json.

Principle enforced here, per REPO_DISCIPLINE.md #2/#3: every field below
comes from the INSTANTIATED config tree (config.json), never from a
script's env-var defaults or a comment's claim about what "should" have
happened.
"""
import json, os, subprocess, sys, argparse


def sh(cmd, cwd=None):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
    return r.stdout.strip()


def load_config(outdir):
    with open(os.path.join(outdir, "config.json")) as f:
        return json.load(f)


def find_by_path_suffix(cfg, suffix, path=""):
    """Yield (full_path, node) for every node whose path ends with `suffix`."""
    if isinstance(cfg, dict):
        name = cfg.get("name") or ""
        full = f"{path}.{name}" if path else name
        if full.endswith(suffix) or suffix in full:
            yield full, cfg
        for k, v in cfg.items():
            if isinstance(v, (dict, list)):
                yield from find_by_path_suffix(v, suffix, full if "name" in cfg else path)
    elif isinstance(cfg, list):
        for item in cfg:
            yield from find_by_path_suffix(item, suffix, path)


def find_all_types(cfg, want_types, path="", out=None):
    """Recursively collect every node whose 'type' is in want_types."""
    if out is None:
        out = []
    if isinstance(cfg, dict):
        t = cfg.get("type")
        name = cfg.get("name") or ""
        full = f"{path}.{name}" if path else name
        if t in want_types:
            out.append((full, t, cfg))
        for k, v in cfg.items():
            if isinstance(v, (dict, list)):
                find_all_types(v, want_types, full, out)
    elif isinstance(cfg, list):
        for item in cfg:
            find_all_types(item, want_types, path, out)
    return out


CACHE_TYPES = {"RubyCache", "SFDirectory"}
RP_TYPES = {"TreePLRURP", "BRRIPRP", "RRIPRP", "DRRIPRP", "RandomRP", "NRURP", "LRURP", "FIFORP"}
PREFETCHER_TYPES = None  # discovered dynamically: anything with "Prefetcher" in type name


def extract_manifest(cfg):
    m = {}

    # LLC / HNF caches
    llc_caches = find_all_types(cfg, CACHE_TYPES)
    m["caches"] = [
        {
            "path": path, "type": t,
            "size": node.get("size"), "assoc": node.get("assoc"),
            "dataAccessLatency": node.get("dataAccessLatency"),
            "tagAccessLatency": node.get("tagAccessLatency"),
            "resourceStalls": node.get("resourceStalls"),
            "start_index_bit": node.get("start_index_bit"),
        }
        for path, t, node in llc_caches
    ]

    # replacement policies
    rps = find_all_types(cfg, RP_TYPES)
    m["replacement_policies"] = [
        {"path": path, "type": t, "btp": node.get("btp"),
         "hit_priority": node.get("hit_priority"), "num_bits": node.get("num_bits")}
        for path, t, node in rps
    ]

    # prefetchers -- type name contains "Prefetcher" anywhere in the tree
    def walk_prefetchers(node, path="", out=None):
        if out is None:
            out = []
        if isinstance(node, dict):
            t = node.get("type", "")
            name = node.get("name") or ""
            full = f"{path}.{name}" if path else name
            if "Prefetcher" in t or "prefetch" in name.lower():
                out.append({
                    "path": full, "type": t,
                    "degree": node.get("degree"),
                    "latency": node.get("latency"),
                    "on_miss_only": node.get("on_miss_only"),
                })
            for k, v in node.items():
                if isinstance(v, (dict, list)):
                    walk_prefetchers(v, full, out)
        elif isinstance(node, list):
            for item in node:
                walk_prefetchers(item, path, out)
        return out

    m["prefetchers"] = walk_prefetchers(cfg)

    # MSHRs (num_mshrs field wherever it appears)
    def walk_mshrs(node, path="", out=None):
        if out is None:
            out = []
        if isinstance(node, dict):
            name = node.get("name") or ""
            full = f"{path}.{name}" if path else name
            if "mshrs" in node or "num_mshrs" in node:
                out.append({"path": full, "mshrs": node.get("mshrs"), "num_mshrs": node.get("num_mshrs")})
            for k, v in node.items():
                if isinstance(v, (dict, list)):
                    walk_mshrs(v, full, out)
        elif isinstance(node, list):
            for item in node:
                walk_mshrs(item, path, out)
        return out

    m["mshrs"] = walk_mshrs(cfg)

    # snoop filter / finite-SF state (SFDirectory already caught in caches;
    # also grab HNF controller-level sf_finite flag if present)
    hnf_ctrls = find_all_types(cfg, {"CHI_Cache_Controller"})
    m["hnf_controllers"] = [
        {"path": path, "sf_finite": node.get("sf_finite")}
        for path, t, node in hnf_ctrls
    ]

    # core count
    cpus = find_all_types(cfg, {"BaseO3CPU", "TimingSimpleCPU", "AtomicSimpleCPU"})
    m["num_cpus"] = len(cpus)
    m["cpu_types"] = sorted(set(t for _, t, _ in cpus))

    # DRAM/CXL latency-bearing memory controllers
    mems = find_all_types(cfg, {"SimpleMemory"})
    m["memories"] = [
        {"path": path, "latency": node.get("latency"), "range": node.get("range")}
        for path, t, node in mems
    ]

    # line size (search for cache_line_size anywhere near the top)
    def find_line_size(node):
        if isinstance(node, dict):
            if "cache_line_size" in node:
                return node["cache_line_size"]
            for v in node.values():
                if isinstance(v, (dict, list)):
                    r = find_line_size(v)
                    if r is not None:
                        return r
        elif isinstance(node, list):
            for item in node:
                r = find_line_size(item)
                if r is not None:
                    return r
        return None

    m["cache_line_size"] = find_line_size(cfg)

    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("outdir")
    ap.add_argument("--cmdline", default=None)
    ap.add_argument("--gem5-repo", default=os.path.expanduser("~/DutyFree-Gem5"))
    args = ap.parse_args()

    cfg = load_config(args.outdir)
    manifest = extract_manifest(cfg)

    # Build-side provenance (REPO_DISCIPLINE.md #7): a manifest that only
    # records the run-time simulation config can't catch a wrong Kconfig
    # baked into the binary itself -- the Intel_8592 variant's own config
    # was undiscoverable from the repo alone until this was added.
    binary_path = None
    for tok in (args.cmdline or "").split():
        if tok.endswith("gem5.opt") or tok.endswith("gem5.fast") or tok.endswith("gem5.debug"):
            binary_path = tok
            break
    variant_dir = None
    build_config_hash = None
    build_config_text = None
    if binary_path:
        # .../build_<variant>/gem5.opt -> variant = <variant>
        parts = binary_path.replace("\\", "/").split("/")
        for p in parts:
            if p.startswith("build_"):
                variant_dir = p
                break
        if variant_dir:
            cfg_path = os.path.join(args.gem5_repo, variant_dir, "gem5.build", "config")
            if os.path.exists(cfg_path):
                with open(cfg_path) as f:
                    build_config_text = f.read()
                import hashlib
                build_config_hash = hashlib.sha256(build_config_text.encode()).hexdigest()[:16]

    manifest["_provenance"] = {
        "outdir": os.path.abspath(args.outdir),
        "commit_sha": sh("git rev-parse HEAD", cwd=args.gem5_repo),
        "commit_subject": sh("git log -1 --format=%s", cwd=args.gem5_repo),
        "dirty_tree": bool(sh("git status --porcelain", cwd=args.gem5_repo)),
        "branch": sh("git rev-parse --abbrev-ref HEAD", cwd=args.gem5_repo),
        "cmdline": args.cmdline,
        "build_variant": variant_dir,
        "build_config_hash": build_config_hash,
        "build_config_text": build_config_text,
        "build_opts_tracked_in_git": (
            bool(sh(f"git ls-files build_opts/{variant_dir.replace('build_', '')}",
                     cwd=args.gem5_repo))
            if variant_dir else None
        ),
        "env": {
            k: os.environ[k] for k in [
                "HNF_SF_FINITE", "HNF_SF_SETS", "HNF_SF_WAYS", "HNF_H3", "HNF_DMT",
                "HNF_MSHR", "L1_MSHR", "L2_MSHR", "PF_DEGREE_L1", "PF_DEGREE_L2",
                "PF_OFF_CORES", "LLC_RP", "LLC_RP_HP", "LLC_RP_LEADERS",
                "ALL_CXL", "RUBY_RANDOMIZATION", "SEED",
            ] if k in os.environ
        },
        # Per-process memory-pool placement (REPO_DISCIPLINE.md #3 lesson,
        # discovered the hard way): se.py hardcodes cpu0 -> DRAM pool,
        # cpu1+ -> CXL pool whenever --cxl-mem-size is set (ALL_CXL=1
        # overrides everyone onto CXL). This determines which SimpleMemory
        # controller (and therefore which latency) each process's traffic
        # actually lands on -- config.json alone does not surface this, it
        # has to be cross-checked against per-controller stats.txt traffic
        # (bytesRead/numReads by mem_ctrls index) to confirm which process
        # landed where, same as this manifest's `memories` field does for
        # the controllers themselves.
        "mem_pool_policy": (
            "ALL_CXL forces every process onto CXL pool 1"
            if os.environ.get("ALL_CXL", "0") not in ("0", "", "false", "False")
            else "default: cpu0 -> DRAM pool 0, cpu1+ -> CXL pool 1"
        ),
    }

    outpath = os.path.join(args.outdir, "manifest.json")
    with open(outpath, "w") as f:
        json.dump(manifest, f, indent=2)
    print(json.dumps(manifest, indent=2))
    print(f"\nwritten to {outpath}", file=sys.stderr)


if __name__ == "__main__":
    main()
