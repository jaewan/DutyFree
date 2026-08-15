# The ABI/motivation mismatch — diagnosis, and the resolution that strengthens the paper

Written 2026-08-16 at the lead's request: think hard about the gap a reviewer
reaches in one step. This is analysis and a recommendation, not an action.

## 1. The gap, stated precisely

**Motivation.** `Abstract.tex:10` and `Sec1_Introduction.tex:15` lead with
"column fragments, vector-index segments, sealed SSTables." Ray plasma objects
appear in the taxonomy. These are *files* and *`MAP_SHARED` shared memory*.

**Prototype.** `Sec4_Streaming.tex:139`: "the prototype admits anonymous and
device-DAX mappings," with the parenthetical "(fs-DAX files, the natural
carrier for column fragments, have no page cache, so admitting them past the
`MAP_SHARED` check is engineering rather than design; we have not done it.)"

So the paper motivates with carriers the artifact does not accept.

## 2. The first-order problem is placement, not capability

Reviewers routinely accept prototype limitations. What they do not accept is
learning about one late. The claim is made in the **abstract**; the concession
is a **parenthetical on page ~6**. A reviewer forms the objection on page 1 and
finds the answer five pages later, phrased as an aside. That sequencing is what
reads as evasion, independent of the engineering merits.

This part is free to fix: state the carrier scope where the motivation is made.
A paper that says up front "we demonstrate on anonymous and device-DAX carriers;
§4 explains what file-backed carriers additionally require" has *disclosed*,
and disclosure is what buys the benefit of the doubt this project has been
banking everywhere else.

## 3. The second-order problem: "engineering rather than design" is likely wrong

This is the part I would not let go to submission as written.

**I1** requires that "during an epoch, all CPU mappings of the frame are
read-only; no CPU, device, or remote host may write without ending the epoch."

- For **anonymous memory + `mprotect`**, I1 is enforceable per-mapping: the
  frames belong to one address space and the PTE permission bit carries it.
  This is what the prototype does, and it is sound.
- For a **shared, file-backed object**, per-mapping enforcement is not
  sufficient and not achievable. Another process can open the same file and
  write it; writeback can touch it. Nothing the mapper does establishes "no
  writer exists." The `MAP_SHARED` check is not an arbitrary gate that
  engineering can lift — it is standing in for a guarantee that regular files
  **do not provide**.

So admitting fs-DAX is not "engineering." It requires answering *where
object-level immutability comes from* for a shared carrier. That is a design
question, and the paper currently dismisses it in a parenthetical. A reviewer
who notices this gets to say the authors mischaracterised their own open
problem — much worse than the missing feature itself.

## 4. The resolution: sealed `memfd` is the carrier that proves the thesis

The fix is not to grind out fs-DAX. It is to notice that Linux **already ships
an object-level immutability declaration**, and it is the natural carrier for
exactly the motivating workload the paper handles worst.

`memfd_create` + `F_SEAL_WRITE`:

- is **`MAP_SHARED`**, so it addresses the Ray plasma case head-on;
- is **object-level**, not per-mapping: once sealed, no writable mapping exists
  and none can be created;
- is **kernel-enforced**, which makes it a *stronger* basis for I1 than the
  prototype's current `mprotect` route, not a weaker one.

*(Sealing semantics here are from general knowledge, not verified against this
prototype's tree — the `DutyFree-Linux` submodule is not checked out on this
machine. Verify `F_SEAL_WRITE`'s interaction with existing mappings before
building on it.)*

**And the alignment with Plasma is not a coincidence — it is the paper's
thesis, already deployed.** Plasma's object lifecycle is create → write →
**seal** → immutable, shared, read-only. That *is* the epoch, expressed at
application level, in a system the paper already cites as motivation. The chain
becomes:

> application declares immutability (Plasma seal / `F_SEAL_WRITE`)
> → OS carries the declaration as a memory type (I0/I1)
> → hardware exploits it (H2, and H3 which only a declaration can license)

One existing primitive at every layer, and a new one only at the hardware end —
which is precisely the paper's ask. This is the strongest available instance of
"**types license coherence exemptions; guesses cannot**": a seal is a
declaration no reuse predictor could ever infer, made by an application that
already bothers to make it.

Landing sealed-`memfd` support would convert the largest unresolved gap from
*"our artifact does not accept the motivating carriers"* into *"our artifact
accepts the carrier that demonstrates the argument end to end, and §4 enumerates
what the others additionally require."*

## 5. What I would put in the paper either way: the carrier table

Even at zero engineering cost, this table converts an apology into a
contribution — it makes the carrier question part of the design space rather
than a hole in it.

| carrier | how I1 is established | status |
|---|---|---|
| anonymous + `mprotect` | PTE permission; single address space | implemented |
| device-DAX | same; device-owned frames | implemented |
| sealed `memfd` (`F_SEAL_WRITE`) | kernel seal; object-level, survives sharing | **recommended next** |
| fs-DAX regular file | no per-mapping guarantee; needs object-level immutability (`chattr +i`, snapshot/COW, or a seal equivalent) | open **design** question |
| remote / multi-host | multi-host write exclusion | open, already stated |

The middle row is the paper's answer to "so which real object can you actually
take?" The fourth row, stated as a design requirement rather than an
engineering to-do, is a far better look than the current parenthetical.

## 6. Recommendation, with the fallback

**Preferred**, if the schedule allows: land sealed-`memfd` admission, re-lead
the motivation with sealed shared-memory objects (Plasma, Arrow IPC), and keep
SSTables/Parquet as the *natural extension* via file-backed carriers, with the
object-level-immutability requirement named as design.

**Fallback**, at zero engineering cost, if it does not: keep the prototype as
is, but (a) move the carrier scope to §1 where the claim is made, (b) replace
"engineering rather than design" with the honest requirement — file-backed
carriers need object-level immutability, and here is what would supply it — and
(c) add the table in §5. This defuses most of the reviewer reaction without
touching code.

Do **not** attempt fs-DAX under schedule pressure. It is the most work and the
least argumentative return of the three options.

## 7. One thing the lead should know independently

The prototype kernel is a submodule (`DutyFree-Linux`) that is **not checked
out here**, so I could not read the admission path or estimate the work. That
also means an artifact evaluator cloning this repository does not get the
kernel. Whatever is decided about the ABI, the artifact story needs the
prototype to be reachable.
