#!/usr/bin/env python3
"""Host exclusivity lock and pre-arm quiescence assertion.

The 2026-08-21 panel ran four investigations concurrently on mos181 and
destroyed at least one member's CAT gate: an aggressor on cpus 8-15 in L3
domain 0 while another member gated a victim in the same domain. Neither run
was recoverable and neither operator knew at the time. This module makes that
failure loud instead of silent.

Two mechanisms, both needed:
  - a lock file, so a second operator is told the host is reserved;
  - a quiescence assertion run immediately BEFORE each arm, so contamination
    that starts after the lock is taken still voids the arm rather than
    silently biasing it.

Usage:
    from hostguard import HostGuard
    with HostGuard("duckdb_join_campaign") as g:
        g.assert_quiescent(allow_cpus={40, 8, 9, 10, 11, 12, 13, 14, 15})
        ...run one arm...
"""
import json, os, pwd, socket, subprocess, sys, time
from pathlib import Path

LOCK = Path("/tmp/.dutyfree_host_lock.json")
# Processes that are part of the measurement harness or the ambient desktop and
# are not evidence of a competing experiment.
BENIGN = {
    "systemd", "kthreadd", "ksoftirqd", "rcu_sched", "migration", "kworker",
    "gnome-shell", "Xorg", "gdm", "gdm3", "gdm-session-wor", "dbus-daemon",
    "pipewire", "pipewire-pulse", "wireplumber", "desktop-launch", "sshd",
    "bash", "sh", "ps", "python3", "claude", "node", "tmux", "systemd-journal",
    "irqbalance", "polkitd", "NetworkManager", "packagekitd", "snapd", "code",
}
# Processes that are definitely a competing experiment on these hosts.
HOSTILE_SUBSTR = (
    "aggressor", "victim", "gem5", "db_bench", "hnsw_bench", "cxl_join_bench",
    "latency_chase", "pr", "bfs", "cc", "duckdb", "intra_app_corun",
)


class Contention(RuntimeError):
    pass


class HostGuard:
    def __init__(self, owner, force=False):
        self.owner = owner
        self.force = force
        self.host = socket.gethostname().split(".")[0]

    def __enter__(self):
        if LOCK.exists():
            try:
                held = json.loads(LOCK.read_text())
            except Exception:
                held = {"owner": "unparseable"}
            alive = held.get("pid") and Path(f"/proc/{held['pid']}").exists()
            if alive and not self.force:
                raise Contention(
                    f"{self.host} is reserved by {held.get('owner')} "
                    f"(pid {held.get('pid')}, since {held.get('since')}). "
                    "Wait, or pass force=True only if you have confirmed it is stale.")
            print(f"[hostguard] clearing stale lock from {held.get('owner')}")
        LOCK.write_text(json.dumps(
            {"owner": self.owner, "pid": os.getpid(), "host": self.host,
             "user": pwd.getpwuid(os.getuid()).pw_name,
             "since": time.strftime("%Y-%m-%dT%H:%M:%S%z")}, sort_keys=True) + "\n")
        print(f"[hostguard] {self.host} reserved by {self.owner} (pid {os.getpid()})")
        return self

    def __exit__(self, *exc):
        try:
            held = json.loads(LOCK.read_text())
            if held.get("pid") == os.getpid():
                LOCK.unlink()
                print("[hostguard] lock released")
        except Exception:
            pass
        return False

    def survey(self):
        """Everything on the box that could perturb a measurement."""
        # pid and pcpu first so both parse numerically; comm last because it can
        # contain spaces, which broke a naive pid,comm,pcpu,args split.
        out = subprocess.run(["ps", "-eo", "pid=,pcpu=,comm="], text=True,
                             capture_output=True).stdout.splitlines()
        busy, hostile = [], []
        me = {str(os.getpid()), str(os.getppid())}
        for line in out:
            f = line.split(None, 2)
            if len(f) < 3:
                continue
            pid, pcpu, comm = f[0], float(f[1]), f[2].strip()
            if pid in me:
                continue
            # Match on comm, never on argv: an argv that merely mentions a
            # binary name (this survey, an editor, a git command) is not a run.
            # That mistake has already cost this project a killed shell and
            # three false "still running" reports.
            if any(comm == h or comm.startswith(h) for h in HOSTILE_SUBSTR):
                hostile.append((pid, comm, pcpu))
            elif pcpu >= 20.0 and comm not in BENIGN:
                busy.append((pid, comm, pcpu))
        groups = [p.name for p in Path("/sys/fs/resctrl").iterdir()
                  if p.is_dir() and p.name not in
                  ("info", "mon_data", "mon_groups")] if Path("/sys/fs/resctrl").is_dir() else []
        load1 = float(Path("/proc/loadavg").read_text().split()[0])
        return {"hostile": hostile, "busy": busy, "resctrl_groups": groups,
                "loadavg1": load1}

    def assert_quiescent(self, max_load=4.0, expect_groups=()):
        """Raise if anything that could bias an arm is running. Call per arm."""
        s = self.survey()
        problems = []
        if s["hostile"]:
            problems.append(f"competing experiment processes: {s['hostile']}")
        if s["busy"]:
            problems.append(f"unexplained busy processes: {s['busy']}")
        extra = [g for g in s["resctrl_groups"] if g not in expect_groups]
        if extra:
            problems.append(f"foreign resctrl groups: {extra}")
        if s["loadavg1"] > max_load:
            problems.append(f"1-min loadavg {s['loadavg1']} > {max_load}")
        if problems:
            raise Contention(f"{self.host} not quiescent: " + "; ".join(problems))
        return s


if __name__ == "__main__":
    g = HostGuard("survey-only")
    s = g.survey()
    print(json.dumps(s, indent=2, sort_keys=True))
    print("VERDICT:", "quiescent" if not (s["hostile"] or s["busy"]) else "CONTENDED")
