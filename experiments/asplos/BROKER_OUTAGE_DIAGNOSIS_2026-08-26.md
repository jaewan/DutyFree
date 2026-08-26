# moscxl (broker, EPYC 9754) — outage diagnosis, day 4

Written 2026-08-26. This host now blocks the single experiment that decides the
paper's claim structure (`CLAIM_REWRITE_2026-08-26.md`: the narrow-aggressor CAT
cell on the 9754). Recording what the failure actually is, so the next attempt
does not re-run the same three guesses.

## What we knew before today

`ssh broker` fails with `kex_exchange_identification: read: Connection reset by
peer`. Host pings at 0.487 ms, port 9812 reports open. Tried: direct,
`ProxyJump` via `c4`, and originating from `c4` on ports 22 and 9812. All fail.

## What today's probing establishes

Probing the listener directly rather than through `ssh`:

| observation | measurement |
|---|---|
| ICMP | 2/2, 0.476--0.495 ms; ARP entry `REACHABLE`, `7c:c2:55:9e:65:1c` |
| open ports (22, 80, 443, 623, 5900, 9100, 9812, 9813, 2222) | **only 9812** |
| bytes received on 9812 before close | **zero, always** |
| time held before RST | **5.10, 5.11, 5.10 s** --- constant |
| 25 rapid consecutive attempts | 25/25 accepted-then-silent, 0 banners |
| same probe sourced from `c4` (different IP) | **identical**: accepted-then-silent |

Four hypotheses are eliminated by that table:

- **Not our key, config, or client.** No byte is ever exchanged; failure precedes
  version negotiation, let alone authentication.
- **Not a per-source ban.** `hosts.deny`, `fail2ban`, and OpenSSH's
  `PerSourcePenalties` are all keyed on source address, and `c4` sees exactly the
  same behaviour from a different address.
- **Not `MaxStartups` overflow.** Random early drop is probabilistic; 25/25 with
  zero successes is deterministic.
- **Not a firewall drop.** A DROP rule gives no TCP handshake and a REJECT gives
  a refusal. We complete the handshake, are held 5.1 s, and are then reset.

## What it leaves

A listener that completes the TCP handshake, writes nothing, and resets on a
**fixed 5-second timer**. Two readings fit, and both have the same consequence:

1. **`sshd` accepts but cannot fork a session child** --- PID, memory, or fd
   exhaustion, or a full root filesystem. The kernel is healthy (it answers ICMP
   and completes handshakes); userspace is not. Plausible here: we ran heavy
   16-thread benchmark batches on this host and have killed runners mid-flight
   more than once.
2. **9812 is a forwarder** (socat, `docker-proxy`, an nginx stream block) whose
   backend `sshd` is gone. The constant 5.1 s is then the forwarder's own
   backend-connect timeout, which is exactly the kind of number that does not
   vary by 10 ms across attempts. Port 22 being closed rather than filtered is
   consistent with there being no host-level `sshd` at all.

The 5.10/5.11/5.10 s constancy is the strongest single clue and it favours
reading 2, because a fork failure would close promptly rather than after a
timer.

## Consequence

**No network path in exists.** Every remaining avenue is out-of-band:

- BMC/IPMI. Port 623 is closed on 192.168.60.180, so if a BMC exists it is on a
  different address; we have no documented BMC address for this host, and I am
  not scanning the lab subnet to look for one.
- Physical console, or a power cycle by someone with access.

If reading 2 is right, a reboot fixes it and so does restarting whatever serves
9812. If reading 1 is right, only a reboot does.

## What is blocked, precisely

Only one thing, and it is load-bearing:

> A narrow-aggressor CAT cell on the 9754 --- 1 or 2 of 16 ways to the streaming
> class, complement enforced to the victim --- against the `tab:amdcat` arms.

`tab:amdcat`'s 9.87x residual is now the paper's only surviving hardware
refutation of partitioning, and it was measured at an 8/8 equal split. Intel's
winning geometry is a narrow mask, and that cell has never been run on this host.
If the narrow AMD mask leaves a large residual, the cross-vendor argument is
sharper than what is currently written; if it returns the victim to ~0.99x, then
no platform in the paper needs the mechanism for neighbour protection.

Nothing else in the paper depends on this host. The AMD numbers already
published (E1's 12.43/3.20, the 19.89x/9.87x/0.99x triple) are measured and
recorded; they do not need re-running.
