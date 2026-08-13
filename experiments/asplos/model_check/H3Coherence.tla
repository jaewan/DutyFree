---------------------------- MODULE H3Coherence ----------------------------
(* Task #29. An abstraction of the CHI-like directory protocol's H3 bypass,
   grounded in H3_IMPL_SPEC.md (Allocate_DirEntry's H3 gate, dir_sharers /
   Initiate_SF_Eviction back-invalidation, the RU/RSC/RSD/RUSC/RUSD pure-R
   states that carry no local data block). This is NOT a transcription of
   the SLICC state machine -- it drops per-message transport and TBE
   bookkeeping entirely and keeps only what the three safety properties
   below actually depend on: per-line epoch state, per-CPU cache occupancy,
   directory enrollment, and a version counter standing in for "the data."

   H3's real argument, restated in this model's terms: while a line's I1
   read-only epoch holds, Write is simply not enabled (the PTE fault, not a
   protocol decision) -- so the directory's only remaining job is to make
   sure a write *after* the epoch can still find and invalidate every
   surviving cached copy. H3 lets a streaming read skip directory enrollment
   (Allocate_DirEntry's early return). The four variants below are the
   soundness taxonomy: they agree on what a streaming read does (skip
   enrollment) and differ on what happens at epoch exit -- exactly the
   design axis the taxonomy in H3_MODELCHECK_H3_TAXONOMY.md picks apart. *)

EXTENDS Naturals, FiniteSets

CONSTANTS
  CPUs,           \* the coherent agents
  Lines,          \* cache lines / addresses in scope
  Variant,        \* "A" ReadOnce/no-retention | "B" epoch-tagged bulk-clear
                  \* "C" DeNovo-style self-invalidate | "D" retain-but-unenrolled (UNSOUND)
  H3Enabled       \* BOOLEAN: whether streaming reads may skip enrollment at all

ASSUME Variant \in {"A", "B", "C", "D"}
ASSUME H3Enabled \in BOOLEAN

VARIABLES
  epoch,          \* [Lines -> {"NotStreaming", "Streaming", "Draining"}]
  version,        \* [Lines -> Nat] -- increments on every real write
  frozenVersion,  \* [Lines -> Nat] -- version[l] snapshotted at StartEpoch(l)
  cache,          \* [CPUs -> [Lines -> {"I","S"}]]
  seenVersion,    \* [CPUs -> [Lines -> Nat]] -- version a cached copy last saw
  dirSharers      \* [Lines -> SUBSET CPUs] -- the actual coherence directory

vars == <<epoch, version, frozenVersion, cache, seenVersion, dirSharers>>

TypeOK ==
  /\ epoch \in [Lines -> {"NotStreaming", "Streaming", "Draining"}]
  /\ version \in [Lines -> Nat]
  /\ frozenVersion \in [Lines -> Nat]
  /\ cache \in [CPUs -> [Lines -> {"I", "S"}]]
  /\ seenVersion \in [CPUs -> [Lines -> Nat]]
  /\ dirSharers \in [Lines -> SUBSET CPUs]

Init ==
  /\ epoch = [l \in Lines |-> "NotStreaming"]
  /\ version = [l \in Lines |-> 0]
  /\ frozenVersion = [l \in Lines |-> 0]
  /\ cache = [c \in CPUs |-> [l \in Lines |-> "I"]]
  /\ seenVersion = [c \in CPUs |-> [l \in Lines |-> 0]]
  /\ dirSharers = [l \in Lines |-> {}]

(* An OS-side I1 epoch opens: freeze the version so any write attempt during
   the epoch is checkable against it (Inv3), and record the intent to make
   the mapping read-only (Write's guard enforces the actual PTE fault). *)
StartEpoch(l) ==
  /\ epoch[l] = "NotStreaming"
  /\ epoch' = [epoch EXCEPT ![l] = "Streaming"]
  /\ frozenVersion' = [frozenVersion EXCEPT ![l] = version[l]]
  /\ UNCHANGED <<version, cache, seenVersion, dirSharers>>

(* Ordinary (non-streaming) coherent read: always enrolls in the directory
   and retains -- this is H1+H2 with H3 off, and the path every non-H3
   sharer takes even during a streaming epoch (e.g. a co-runner touching the
   same line the ordinary way). *)
CoherentRead(c, l) ==
  /\ cache[c][l] = "I"
  /\ cache' = [cache EXCEPT ![c][l] = "S"]
  /\ seenVersion' = [seenVersion EXCEPT ![c][l] = version[l]]
  /\ dirSharers' = [dirSharers EXCEPT ![l] = @ \cup {c}]
  /\ UNCHANGED <<epoch, version, frozenVersion>>

(* The H3 bypass itself: Allocate_DirEntry's early return. dirSharers is
   deliberately left untouched -- that is the entire mechanism. Variant "A"
   additionally never even retains the line (ReadOnce), so there is nothing
   left to reconcile at epoch exit; B/C/D retain it for reuse but must
   reconcile that decision before the epoch can safely close. *)
StreamingRead(c, l) ==
  /\ H3Enabled
  /\ epoch[l] = "Streaming"
  /\ cache[c][l] = "I"
  /\ IF Variant = "A"
     THEN UNCHANGED <<cache, seenVersion>>
     ELSE /\ cache' = [cache EXCEPT ![c][l] = "S"]
          /\ seenVersion' = [seenVersion EXCEPT ![c][l] = version[l]]
  /\ UNCHANGED <<epoch, version, frozenVersion, dirSharers>>

(* Epoch exit -- the soundness taxonomy lives entirely in this one action. *)
EndEpoch(l) ==
  /\ epoch[l] = "Streaming"
  /\ UNCHANGED <<version, frozenVersion, dirSharers>>
  /\ IF Variant = "A"
       (* Nothing was ever retained (ReadOnce): exit is a pure formality. *)
     THEN /\ epoch' = [epoch EXCEPT ![l] = "NotStreaming"]
          /\ UNCHANGED <<cache, seenVersion>>
     ELSE IF Variant = "B"
       (* Epoch-tagged retention, bulk-cleared: one atomic step invalidates
          every unenrolled retained copy, then the line reopens for writes. *)
     THEN /\ epoch' = [epoch EXCEPT ![l] = "NotStreaming"]
          /\ cache' = [c \in CPUs |->
                        [cache[c] EXCEPT ![l] =
                          IF cache[c][l] = "S" /\ c \notin dirSharers[l]
                          THEN "I" ELSE cache[c][l]]]
          /\ UNCHANGED seenVersion
     ELSE IF Variant = "C"
       (* DeNovo-style self-invalidation: exit only *starts* the drain.
          Writes stay blocked (epoch # "NotStreaming") until every holder of
          an unenrolled copy has invalidated itself -- see FinishDrain. *)
     THEN /\ epoch' = [epoch EXCEPT ![l] = "Draining"]
          /\ UNCHANGED <<cache, seenVersion>>
       (* Variant "D" -- retain-but-unenrolled, rated UNSOUND: reopens the
          line for writes with NO reconciliation step at all. Any unenrolled
          retained copy simply survives, invisible to the directory. This is
          the "tolerate" fix the project rejected; it is here so the model
          checker demonstrates *why*, not just asserts it. *)
     ELSE /\ epoch' = [epoch EXCEPT ![l] = "NotStreaming"]
          /\ UNCHANGED <<cache, seenVersion>>

(* Variant C only: each holder of an unenrolled retained copy invalidates
   itself independently -- no central broadcast, no directory lookup,
   because the directory never knew about it in the first place. *)
SelfInvalidate(c, l) ==
  /\ Variant = "C"
  /\ epoch[l] = "Draining"
  /\ cache[c][l] = "S"
  /\ c \notin dirSharers[l]
  /\ cache' = [cache EXCEPT ![c][l] = "I"]
  /\ UNCHANGED <<epoch, version, frozenVersion, seenVersion, dirSharers>>

(* Variant C only: once no unenrolled retained copy remains, the drain is
   complete and the epoch can actually close for writes. *)
FinishDrain(l) ==
  /\ Variant = "C"
  /\ epoch[l] = "Draining"
  /\ \A c \in CPUs : ~(cache[c][l] = "S" /\ c \notin dirSharers[l])
  /\ epoch' = [epoch EXCEPT ![l] = "NotStreaming"]
  /\ UNCHANGED <<version, frozenVersion, cache, seenVersion, dirSharers>>

(* A write only ever takes effect once the line is fully closed
   ("NotStreaming"). While epoch[l] \in {"Streaming","Draining"} this action
   is not enabled at all -- modeling the write faulting against the
   still-read-only PTE instead of ever reaching the coherence fabric. A real
   write invalidates exactly the directory-tracked sharers, mirroring
   Initiate_SF_Eviction's back-invalidation of dir_sharers. *)
Write(l) ==
  /\ epoch[l] = "NotStreaming"
  /\ version' = [version EXCEPT ![l] = @ + 1]
  /\ cache' = [c \in CPUs |->
                [cache[c] EXCEPT ![l] = IF c \in dirSharers[l] THEN "I" ELSE cache[c][l]]]
  /\ dirSharers' = [dirSharers EXCEPT ![l] = {}]
  /\ UNCHANGED <<epoch, frozenVersion, seenVersion>>

Next ==
  \/ \E l \in Lines : StartEpoch(l) \/ EndEpoch(l) \/ FinishDrain(l) \/ Write(l)
  \/ \E c \in CPUs, l \in Lines :
       CoherentRead(c, l) \/ StreamingRead(c, l) \/ SelfInvalidate(c, l)

Spec == Init /\ [][Next]_vars

-----------------------------------------------------------------------------
(* Property 1 -- "no stale read is reachable while I1 holds": any cached
   copy of a line currently under the epoch (Streaming or mid-drain) must
   have seen the line's current version. This should hold for every
   variant, sound or not -- the epoch itself is never incoherent; per Inv3
   no write can touch version[l] while the epoch is open, so a copy formed
   during the epoch cannot go stale *during* it. *)
Inv1_NoStaleReadDuringEpoch ==
  \A l \in Lines :
    epoch[l] \in {"Streaming", "Draining"} =>
      \A c \in CPUs : cache[c][l] = "S" => seenVersion[c][l] = version[l]

(* Property 2 -- "the epoch-exit drain restores full coherence": once a line
   is open for writes again, every cached copy of it must be directory
   visible. This is exactly what Variant D violates: EndEpoch reopens the
   line while an unenrolled retained copy still sits in some CPU's cache,
   invisible to dirSharers. TLC is expected to find a counterexample here
   under Variant = "D" and nowhere else. *)
Inv2_CoherenceRestoredAtExit ==
  \A l \in Lines :
    epoch[l] = "NotStreaming" =>
      \A c \in CPUs : cache[c][l] = "S" => c \in dirSharers[l]

(* Property 3 -- "an I1 violation with H3 off still faults via the PTE":
   Write's guard never inspects H3Enabled at all, so this must hold
   regardless of the H3 knob. version[l] cannot move while the epoch is
   open; the only way to violate I1 is for a write to actually land, and
   that is checked here directly against the frozen snapshot rather than
   trusting Write's guard by inspection. *)
Inv3_WriteFaultsDuringEpoch ==
  \A l \in Lines :
    epoch[l] \in {"Streaming", "Draining"} => version[l] = frozenVersion[l]

(* version is otherwise unbounded (Write increments it forever) -- bound the
   state space for TLC. 2 versions is already enough to exercise every
   action at least once per line (StartEpoch, a streaming read, EndEpoch /
   drain, a post-epoch Write); it is not load-bearing for any property. *)
StateConstraint == \A l \in Lines : version[l] <= 2

=============================================================================
