All verified. The decisive safety finding: `UpdateDirState_FromSnpDataResp` clears `tbe.dir_ownerExists := false` when the dirty owner returns `SnpRespData_I_PD`, and `UpdateDataState_FromSnpDataResp` sets `dataDirty:=true`. So when `Initiate_MaintainCoherence` runs *after* the snoop drains, `has_non_ex_owner` is false and `dataDirty` reflects reality — the WB fires for dirty victims and is skipped for clean ones (fixing HAZARD 3). And `Initiate_Replacement_WB_BackInvalidate` would `assert`-fail on clean combined states like `SC_RSC` at HN, confirming `MaintainCoherence` is the *only* correct unified eviction primitive.

I now have every load-bearing fact confirmed against the live tree. Here is the synthesized spec.

---

# SYNTHESIS: Safest implementable design — finite snoop-filter + directory-only back-invalidation + H3 bypass

## Skeleton chosen and why

**Base = DESIGN safety** (rated SOUND; the only design whose eviction primitive is correct for *all* victim states). **Grafts:**
- From REVIEW mirror HAZARD 1/2/3: the three catastrophic fixes.
- **New safest sub-decision (eliminates HAZARD 1 and HAZARD 7 by construction):** do **not** convert the `directory` member to a pointer. Keep `PerfectCacheMemory directory` exactly as-is, and add a **separate nullable `CacheMemory * sf`**, wired only at the HNF, dereferenced only when `sf_finite`. This mirrors the existing `prefetch::Base * prefetcher` + `use_prefetcher` guard pattern (CHI-cache.sm:51,194). Consequence: the `sf_finite=false` path is *literally the current code* → byte-identical regression gate holds by construction; non-HN controllers never touch `sf` → no NULL deref; no set-associative `allocate` panic possible when `sf_finite=false` (HAZARD 7 gone).
- From DESIGN safety: `Initiate_MaintainCoherence`-based unified eviction (fixes HAZARD 3 dynamically), `isSFEvict` routing flag, dedicated `SF_Eviction` event with pure-R vs combined transition rows.

**Invariant this design rests on (assert-documented):** `sf_finite == true ⟹ is_HN == true ⟹ sf != NULL`. Enforced in Python (only `CHI_HNFController` sets both `sf_finite` and `self.sf`).

---

## Ordered edit list

| # | File:line | Change |
|---|---|---|
| 1 | CHI-cache.sm:817 | Add `CacheMemory * sf;` **after** the unchanged `PerfectCacheMemory directory` line |
| 2 | CHI-cache.sm:901 (ReplacementMsg) | Add `bool isSFEvict, default="false";` |
| 3 | CHI-cache.sm:~445 | Add event `CheckSFFill` |
| 4 | CHI-cache.sm:~450 | Add event `SF_Eviction, in_trans="yes"` |
| 5 | CHI-cache-funcs.sm:83-89 | Rewrite `getDirEntry` to branch on `sf_finite` |
| 6 | CHI-cache-funcs.sm (new, after getDirEntry) | Add `dirTagPresent` / `dirDeallocate` helpers |
| 7 | CHI-cache-actions.sm:3454-3457 | Rewrite `Allocate_DirEntry` (H3 gate + finite-defer + unchanged else) |
| 8 | CHI-cache-actions.sm:3459-3462 | Rewrite `Deallocate_DirEntry` to use `dirDeallocate` |
| 9 | CHI-cache-actions.sm:3441-3443 | `Finalize_UpdateDirectoryFromTBE` else-branch → `dirTagPresent`/`dirDeallocate` |
| 10 | CHI-cache-actions.sm (new, near CheckCacheFill) | Add `CheckSFFill` action |
| 11 | CHI-cache-actions.sm (new, near Initiate_Replacement_WB_BackInvalidate) | Add `Initiate_SF_Eviction` action |
| 12 | CHI-cache-ports.sm:284 | `replTriggerInPort`: add `isSFEvict → SF_Eviction` branch |
| 13 | CHI-cache-transitions.sm:~113 | Add `CheckSFFill` driver transition |
| 14 | CHI-cache-transitions.sm:~892 | Add 3 `SF_Eviction` transitions (pure-R / combined / I) |
| 15 | CHI-cache-transitions.sm:986 | Add `SF_Eviction` to the BUSY `StallLocalEviction` transition |
| 16 | CHI_config_8592.py:~922 | Add `class SFDirectory(RubyCache)` |
| 17 | CHI_config_8592.py:730 | Build finite `SFDirectory`, assign `self._cntrl.sf` |

The 10 `Allocate_DirEntry;` call-sites (transitions.sm:187,204,275,284,310,338,584,593,603,612) are **untouched** — the defer/H3 logic lives inside the action.

---

## Exact final SLICC

### Edit 1 — CHI-cache.sm:817 (leave `directory` as-is; add pointer)
```slicc
  // Directory (infinite; used when sf_finite == false, and by all non-HN nodes)
  PerfectCacheMemory directory, template="<Cache_DirEntry>";

  // Finite snoop-filter backing store. Non-null ONLY at the HNF; dereferenced
  // ONLY when sf_finite (see invariant). Mirrors the nullable `prefetcher`
  // pointer + `use_prefetcher` guard pattern.
  CacheMemory * sf;
```

### Edit 2 — CHI-cache.sm ReplacementMsg (:897-903)
```slicc
  structure(ReplacementMsg, interface="Message") {
    Addr addr;
    Addr from_addr;
    int slot; // set only when unify_repl_TBEs is set
    bool isSFEvict, default="false"; // true => finite-SF (directory) eviction
    bool functionalRead(Packet *pkt) { return false; }
    bool functionalRead(Packet *pkt, WriteMask &mask) { return false; }
    bool functionalWrite(Packet *pkt) { return false; }
  }
```

### Edit 3,4 — CHI-cache.sm events (next to CheckCacheFill :444 and eviction events :448-450)
```slicc
    CheckSFFill, desc="Ensure finite-SF has room for this dir entry; evict an SF victim if full";
```
```slicc
    SF_Eviction, in_trans="yes", desc="Finite-SF capacity eviction: back-invalidate all upstream sharers of a directory-tracked victim";
```

### Edit 5 — CHI-cache-funcs.sm:83-89 (`getDirEntry`)
```slicc
DirEntry getDirEntry(Addr addr), return_by_pointer = "yes" {
  if (sf_finite) {
    // finite SF (HNF only; sf is non-null by invariant)
    if (sf.isTagPresent(addr)) {
      return static_cast(DirEntry, "pointer", sf.lookup(addr));
    } else {
      return OOD;
    }
  } else {
    if (directory.isTagPresent(addr)) {
      return directory.lookup(addr);
    } else {
      return OOD;
    }
  }
}
```

### Edit 6 — CHI-cache-funcs.sm (new helpers, immediately after `getDirEntry`)
```slicc
bool dirTagPresent(Addr addr) {
  if (sf_finite) {
    return sf.isTagPresent(addr);
  } else {
    return directory.isTagPresent(addr);
  }
}

void dirDeallocate(Addr addr) {
  if (sf_finite) {
    assert(sf.isTagPresent(addr));
    sf.deallocate(addr);
  } else {
    assert(directory.isTagPresent(addr));
    directory.deallocate(addr);
  }
}
```

### Edit 7 — CHI-cache-actions.sm:3454-3457 (`Allocate_DirEntry`)
```slicc
action(Allocate_DirEntry, desc="") {
  assert(is_valid(tbe));
  // B3 (H3): a STREAMING line skips SF enrollment entirely. Also suppress the
  // CompAck sharer-record so the transaction finalizes to I (no dir entry is
  // ever expected at Finalize). Gated by enable_H3_streaming_bypass (default off).
  if (enable_H3_streaming_bypass && is_HN && tbe.isStreaming) {
    tbe.updateDirOnCompAck := false;
    return;
  }
  if (sf_finite) {
    // Finite SF (HNF only): defer to CheckSFFill, which allocates now if there
    // is room, else evicts a victim and retries. pushFront keeps allocation
    // ahead of the read pipeline -- same ordering as the synchronous path.
    tbe.actions.pushFront(Event:CheckSFFill);
  } else {
    // Unchanged legacy path: infinite PerfectCacheMemory.
    assert(directory.isTagPresent(address) == false);
    directory.allocate(address);
  }
}
```

### Edit 8 — CHI-cache-actions.sm:3459-3462 (`Deallocate_DirEntry`)
```slicc
action(Deallocate_DirEntry, desc="") {
  dirDeallocate(address);
}
```

### Edit 9 — CHI-cache-actions.sm Finalize_UpdateDirectoryFromTBE else-branch (:3440-3444)
```slicc
  } else {
    assert((tbe.dir_ownerExists == false) && tbe.dir_sharers.isEmpty());
    if (dirTagPresent(address)) {
      dirDeallocate(address);
    }
  }
```
(The `if`-branch — the pure-R/combined final states — is unchanged; it reaches the entry via `getDirEntry`, which already routes to `sf` when finite.)

### Edit 10 — CHI-cache-actions.sm new `CheckSFFill` (clone of CheckCacheFill, retargeted to `sf`)
```slicc
action(CheckSFFill, desc="Ensure a finite-SF dir slot is free; evict an SF victim if full") {
  assert(is_valid(tbe));
  assert(is_HN);          // sf_finite is only ever true at the HNF
  bool execute_next := true;

  if (sf.isTagPresent(address)) {
    // already allocated on a prior pass (or combined-state re-touch): nothing to do
  } else if (sf.cacheAvail(address)) {
    sf.allocateVoid(address, new DirEntry);
  } else {
    // no room in this set: pick a victim, evict it, and re-run after it drains
    execute_next := false;
    Addr victim_addr := sf.cacheProbe(address);
    DirEntry victim_dir := getDirEntry(victim_addr);
    TBE victim_tbe := getCurrentActiveTBE(victim_addr);
    assert(is_valid(victim_dir));
    if (is_invalid(victim_tbe) && is_valid(victim_dir)) {
      DPRINTF(RubySlicc, "SF eviction for %#x victim: %#x state=%s\n",
                          address, victim_addr, victim_dir.state);
      enqueue(replTriggerOutPort, ReplacementMsg, 0) {
        out_msg.addr := victim_addr;
        out_msg.from_addr := address;
        out_msg.isSFEvict := true;
        // unify_repl_TBEs is False at the HNF, so no out_msg.slot
      }
    } else {
      // victim busy: its own transaction will wake us on completion
      victim_tbe.wakeup_pending_tgr := true;
    }
    stall_and_wait(triggerInPort, victim_addr);
  }

  if (execute_next) {
    triggerInPort.dequeue(clockEdge());
    clearPendingAction(tbe);
    processNextState(address, tbe, cache_entry);
  } else {
    wakeupPendingSnps(tbe);
  }
}
```

### Edit 11 — CHI-cache-actions.sm new `Initiate_SF_Eviction`
```slicc
action(Initiate_SF_Eviction, desc="HN back-invalidate all sharers of a directory-tracked victim; WB any pulled/held dirty data") {
  assert(is_HN);
  assert(is_valid(tbe));
  assert(tbe.dir_sharers.count() > 0);   // guaranteed for RU/RSC/RSD/RUSC/RUSD + all combined dir states
  tbe.dataToBeInvalid := true;           // we are dropping this line's data (if any)
  // SnpCleanInvalid arms expected_snp_resp via setExpectedForInvSnoop(tbe,false)
  // and pulls SnpRespData_I_PD from any dirty owner. Its responses clear
  // dir_ownerExists and set dataDirty BEFORE MaintainCoherence runs.
  tbe.actions.push(Event:SendSnpCleanInvalid);
  // MaintainCoherence is HN-safe and clean-aware: it emits WriteNoSnp+WBData
  // IFF (post-snoop) tbe.dataDirty && !has_non_ex_owner, else it is a no-op.
  // This is why a clean pure-R (RSC/RUSC) or clean-UC-owner RU victim does NOT
  // hit the Send_WBData asserts. It also queues the closing TagArrayWrite.
  tbe.actions.push(Event:MaintainCoherence);
}
```

### Edit 12 — CHI-cache-ports.sm:284 (`replTriggerInPort`, add first branch)
```slicc
    peek(replTriggerInPort, ReplacementMsg) {
      TBE tbe := getCurrentActiveTBE(in_msg.addr);
      CacheEntry cache_entry := getCacheEntry(in_msg.addr);
      Event trigger := Event:null;
      if (in_msg.isSFEvict) {
        // finite-SF capacity eviction: victim state (pure-R vs combined) selects
        // the SF_Eviction transition row.
        trigger := Event:SF_Eviction;
      } else if (is_valid(cache_entry) &&
          ((upstreamHasUnique(cache_entry.state) && dealloc_backinv_unique) ||
          (upstreamHasShared(cache_entry.state) && dealloc_backinv_shared))) {
        trigger := Event:Global_Eviction;
      } else {
        if (is_HN) {
          trigger := Event:LocalHN_Eviction;
        } else {
          trigger := Event:Local_Eviction;
        }
      }
      trigger(trigger, in_msg.addr, cache_entry, tbe);
    }
```

### Edit 13 — CHI-cache-transitions.sm:~113 (`CheckSFFill` driver)
```slicc
// goes to BUSY_INTR as we may need to accept snoops while waiting on an SF eviction
transition({BUSY_INTR,BUSY_BLKD}, CheckSFFill, BUSY_INTR) {
  CheckSFFill;
  // CheckSFFill either does dequeue+clearPending+ProcessNextState, or stalls
  // on the victim (execute_next=false) exactly like CheckCacheFill.
}
```

### Edit 14 — CHI-cache-transitions.sm:~892 (SF_Eviction transitions)
```slicc
// Directory-only (pure-R) SF victims: NO cache block to free.
transition({RU,RSC,RSD,RUSC,RUSD}, SF_Eviction, BUSY_BLKD) {ReplTBEAvailable} {
  Initiate_Replacement;      // allocs repl TBE; copyCacheAndDir loads dir_sharers, tolerates null cache_entry
  Initiate_SF_Eviction;
  Profile_Eviction;          // guards cache_entry use with is_valid -> safe with no block
  Deallocate_DirEntry;       // frees the SF slot now (before Pop wakes the filler)
  Pop_ReplTriggerQueue;      // wakeup_port(triggerInPort, victim) -> filler's CheckSFFill reruns, cacheAvail now true
  ProcessNextState;
}

// Combined (cache-block + dir) SF victims: additionally free the L3 block.
// Deallocate_CacheBlock uses tbe.dataBlk (already copied by copyCacheAndDir),
// so early dealloc is safe -- identical pattern to Global_Eviction.
transition({UD_RSC,SD_RSC,UC_RSC,SC_RSC,UD_RU,UC_RU,UD_RSD,SD_RSD}, SF_Eviction, BUSY_BLKD) {ReplTBEAvailable} {
  Initiate_Replacement;
  Initiate_SF_Eviction;
  Profile_Eviction;
  Deallocate_CacheBlock;
  Deallocate_DirEntry;
  Pop_ReplTriggerQueue;
  ProcessNextState;
}

// Victim raced to I (already invalidated) before the SF eviction was handled.
transition(I, SF_Eviction) {
  Pop_ReplTriggerQueue;
}
```

### Edit 15 — CHI-cache-transitions.sm:986 (BUSY staller: add SF_Eviction)
```slicc
transition({BUSY_BLKD,BUSY_INTR},
           {Global_Eviction, Local_Eviction, LocalHN_Eviction, SF_Eviction}) {
  StallLocalEviction;
}
```

### Edit 16 — CHI_config_8592.py:~922 (near `HNFCache`)
```python
class SFDirectory(RubyCache):
    # Finite snoop-filter / coherence directory backing store for the HNF.
    # DirEntry carries no DataBlk, so data-array latency is irrelevant.
    dataAccessLatency = 0
    tagAccessLatency = 1
```

### Edit 17 — CHI_config_8592.py:730 (`CHI_HNF.__init__`, alongside `ll_cache`)
```python
        ll_cache = llcache_type(start_index_bit=intlvHighBit + 1)
        self._cntrl = CHI_HNFController(
            ruby_system, ll_cache, NULL, addr_ranges
        )

        # Finite snoop filter (B2/H3). Default HUGE => cacheAvail never fails =>
        # never evicts => behaves as the infinite PerfectCacheMemory. Shrink via
        # env for the B4 finite-SF arm. Indexed exactly like the LLC slice so
        # per-HNF interleaving lines up.
        sf_finite = bool(int(os.environ.get("HNF_SF_FINITE", 0)))
        if sf_finite:
            sf_ways = int(os.environ.get("HNF_SF_WAYS", 16))
            sf_sets = int(os.environ.get("HNF_SF_SETS", 1 << 16))  # 65536*16 ~= 1M entries default
            self._cntrl.sf = SFDirectory(
                size=sf_sets * sf_ways * 64,   # 64B line granularity
                assoc=sf_ways,
                start_index_bit=intlvHighBit + 1,
            )
            self._cntrl.sf_finite = True
        # else: leave self._cntrl.sf unset (NULL) and sf_finite False (default)
```
Confirm `CHI_HNFController.__init__` (line 333) already reads `self.sf_finite`/`self.enable_H3_streaming_bypass` from env (B1, lines 361-362). If it *sets* `self.sf_finite` from env there, keep that as the single source of truth and gate the `self.sf` construction on the same value; do not set it in two places. **The hard rule: `self.sf` is assigned iff `self.sf_finite` is True, and only for the HNF.**

---

## Response-map accounting (deallocation proof)

Repl TBE reaches `Final`→`Finalize_DeallocateRequest`→`deallocateReplacementTBE` only when `processNextState` (ports.sm:457-460) sees `expected_req_resp.expected() + expected_snp_resp.expected() == 0 && pendAction==null`. `Send_SnpCleanInvalid` (actions.sm:1851) sets `retToSrc:=false` and arms via `setExpectedForInvSnoop(tbe,false)` (funcs.sm:1027). Per victim state (`copyCacheAndDir`, funcs.sm:872):

| Victim | `dataMaybeDirtyUpstream`/`ownerExists` | Armed `expected_snp_resp` (count=`dir_sharers.count()`) | Actual replies | Drains via | Post-snoop `dataDirty` → WB? |
|---|---|---|---|---|---|
| RSC, RUSC | false / false | `SnpResp_I` × N | all sharers `SnpResp_I` | `Receive_SnpResp` | false → **no WB** (MaintainCoherence no-op) |
| RU (owner UD) | true / true, N=1 | `SnpRespData_I_PD` **or** `SnpResp_I`, count 1 | owner `SnpRespData_I_PD` | `Receive_SnpDataResp` | true → **WB** |
| RU (owner UC, clean) | true / true, N=1 | same armed set (both types) | owner `SnpResp_I` (no data) | `Receive_SnpResp` | false → **no WB** (this is the HAZARD-3 fix) |
| RSD, RUSD | true / true, N | `SnpRespData_I_PD` + `SnpResp_I`, count N | SD owner PD-data, others `SnpResp_I` | both | true → **WB** |
| Combined clean (SC_RSC, UC_RSC…) | false / false | `SnpResp_I` × N | `SnpResp_I` | `Receive_SnpResp` | HN block clean → no WB; HN block dirty (UD_RSC) → WB from `tbe.dataBlk` |
| Combined dirty-owner (UD_RSD, SD_RSD…) | true / true | `SnpRespData_I_PD` + `SnpResp_I` | owner PD-data, others `SnpResp_I` | both | true → **WB** |

The arming set for the excl-owner case (`dataMaybeDirtyUpstream` true, count=1) contains **both** `SnpRespData_I_PD` and `SnpResp_I`, so a clean *or* dirty owner reply is always accepted — `expected()` provably reaches 0 for every state. When a dirty owner replies `SnpRespData_I_PD`, `UpdateDirState_FromSnpDataResp` (actions.sm:2337) clears `dir_ownerExists`, and `UpdateDataState_FromSnpDataResp` (actions.sm:2544) sets `dataDirty=dataValid=true`, `dataMaybeDirtyUpstream=false` — so when `MaintainCoherence` runs, `has_non_ex_owner==false` and `dataDirty==true` → the pulled data is written back (never lost). The WB itself (`Send_WriteNoSnp`) arms one `CompDBIDResp`/`DBIDResp` that drains normally. No armed type is ever unsatisfiable ⇒ no repl-TBE leak ⇒ no deadlock.

---

## (a) Incremental build + test order

Build: `cd ~/DutyFree-Gem5 && yes '' | ~/gem5-venv/bin/scons build_Intel_8592/gem5.opt -j128`

**Regression gate (must pass unchanged at every step):** xcore `alone/wb/st` with `HNF_SF_FINITE=0 HNF_H3=0` must reproduce **H2 ~94% recovery** (memory baseline alone 33.86 / WB 45.19 / ST 34.57). With this design the `sf_finite=false` path is the *original code* (getDirEntry else-branch, `directory.allocate`, no CheckSFFill pushed, H3 gate skipped since default off), so this is byte-identical **by construction**, not just approximately.

| Step | Edits | Knobs | Expected |
|---|---|---|---|
| 1 | 1,5,6,8,9,16 (types/helpers only; `Allocate_DirEntry` else unchanged) | `HNF_SF_FINITE=0 HNF_H3=0` | Builds green. xcore byte-identical (gate). Proves the nullable-`sf` + helper routing is inert when off. |
| 2 | +2,3,7,10,13 (CheckSFFill machinery) | `HNF_SF_FINITE=0` then `HNF_SF_FINITE=1 HNF_SF_SETS=65536 HNF_SF_WAYS=16` (huge) | Both byte-identical to gate: finite huge never hits `cacheAvail==false`, so CheckSFFill only ever takes the allocate arm. |
| 3 | +4,11,12,14,15,17 (SF_Eviction) | `HNF_SF_FINITE=1 HNF_SF_SETS=64 HNF_SF_WAYS=8` (512 entries). Start with a **read-only (RSC-only)** victim workload, then a writer to exercise dirty RSD/RU. | `SF eviction for …` DPRINTFs appear; run completes, no `TBEs full`/hang. Clean path first, then dirty. |
| 4 | (none) | `HNF_SF_FINITE=1 HNF_H3=1` small SF | Streaming reads produce **zero** SF allocations (no aggressor SF-eviction traffic) and complete to `I`. |

At each step diff the full stats file against step-0 baseline for the `HNF_SF_FINITE=0 HNF_H3=0` config to catch any accidental divergence.

---

## (b) Top 3 residual deadlock risks + what to watch

1. **Filler never re-woken after its SF victim drains** (stall/wakeup chain). The filler parks on `stall_and_wait(triggerInPort, victim_addr)`; it is re-driven only by `Pop_ReplTriggerQueue`'s `wakeup_port(triggerInPort, victim)` (actions.sm:3613) — which is the *last* action of every SF_Eviction row — or by `wakeupPendingTgrs` from the busy-victim's `Finalize_Deallocate*`. **Watch:** a hang with `RubySlicc` showing `SF eviction for X victim: Y` but no subsequent `GoToNextState` for X. Confirm every `SF_Eviction` transition ends in `Pop_ReplTriggerQueue`; confirm `Deallocate_DirEntry` precedes it so `sf.cacheAvail(address)` is true on rerun.

2. **Expected-response map left non-empty** (repl TBE never deallocates). Guarded by the accounting table, but a mis-set `retToSrc` or a sharer replying an un-armed type would stall forever. **Watch:** `processNextState` DPRINTF `expected_snp_resp=N` stuck `> 0` on the repl TBE's address; and the `receiveResp`/`receiveData` panic "unexpected response type". Confirm `Send_SnpCleanInvalid` keeps `retToSrc:=false` (clean sharers must reply `SnpResp_I`, matching an armed slot).

3. **Repl-TBE / MSHR starvation under high SF-eviction concurrency** (livelock, not a true cycle). `SF_Eviction` is gated `{ReplTBEAvailable}` (`number_of_repl_TBEs=32` at HNF). Every repl-TBE holder completes without needing another repl TBE or SF slot, so it drains — but a shrunken SF (step 3) can drive many concurrent evictions. **Watch:** stat `avg_repl_TBE_occupancy` pinned at 32, `replTriggerQueue` backlog growing, throughput collapse without a hard hang. Mitigation: raise `HNF` `number_of_repl_TBEs` if B4 shows it.

Secondary (non-deadlock) items to note, not block on: combined dirty SF victims WB from `tbe.dataBlk` without a modeled `DataArrayRead` (minor latency under-count vs `Global_Eviction`); and confirm DMT is off in the B4 config or document that an H3 streaming ReadShared silently drops the exclusive-owner intent (acceptable for one-pass reads).

---

## (c) B4 experiment config

**SF sizing.** Baseline (infinite-equivalent): `HNF_SF_FINITE=0` (or finite with `HNF_SF_SETS=65536 HNF_SF_WAYS=16` ≈ 1M entries ≫ the 81,920-line / 5 MiB-20-way L3). **Pressure arm:** `HNF_SF_FINITE=1 HNF_SF_SETS=64 HNF_SF_WAYS=8` = **512 entries**, deliberately far smaller than the victim's read-shared footprint so SF capacity pressure and back-invalidation are visible. Sweep `HNF_SF_WAYS ∈ {8,16}` × `HNF_SF_SETS ∈ {64,128,256}` for a capacity curve.

**Arms** (aggressor = cold streaming scan disjoint from victim working set; victim = latency-sensitive reader):
| Arm | Knobs | Isolates |
|---|---|---|
| **WB** (baseline) | `HNF_SF_FINITE=1` small SF, `HNF_H2=0 HNF_H3=0` | Finite-SF back-invalidation tax with no mitigation |
| **H2** | + `HNF_H2=1` (streaming skips L3 *data* fill) | Data-array-pressure relief alone |
| **H2+H3** | + `HNF_H2=1 HNF_H3=1` (streaming skips L3 fill **and** SF enrollment) | Additional SF-pressure relief from enrollment elision |

Compare against the **infinite-SF** reference (`HNF_SF_FINITE=0`) to size the total finite-SF tax that H3 recovers.

**Metrics.** Victim IPC / avg memory access latency (primary); SF-eviction count and back-invalidation-snoop count (`SF eviction` DPRINTF tally / `SnpCleanInvalid` sent by HNF); SF miss/allocation rate; aggressor SF allocations (must be ~0 with H3); L3 data-array fills (H2 effect) vs SF allocations (H3 effect) decomposition; repl-TBE occupancy (starvation guard from risk 3). Success = H2+H3 recovers the finite-SF back-invalidation tax that H2 alone leaves on the table, approaching the infinite-SF reference, with zero aggressor SF footprint.

---

**Bottom line:** the dual-structure choice (keep `PerfectCacheMemory directory`, add nullable `CacheMemory * sf`) removes HAZARD 1 and HAZARD 7 structurally; `Initiate_MaintainCoherence` removes HAZARD 3; the `assert(is_HN)` in `CheckSFFill` is safe because `sf_finite` is HNF-only (HAZARD 2 avoided — the always-run allocate path stays in the `else` branch that has no `is_HN` gate). Regression gate is byte-identical by construction. All three reviews' FIXABLE items are incorporated.