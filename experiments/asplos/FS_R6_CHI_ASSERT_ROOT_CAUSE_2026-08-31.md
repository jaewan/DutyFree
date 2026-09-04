# r6 FS `stream_mprot` CHI assertion: root cause and disposition

## Disposition

`atomic_2cpu_w8_fs_e2e_r6_16g` is a failed, non-reportable campaign.  Its WB
gate is retained as an individually valid artifact, but it must not be paired
with a future STREAMING arm.  A fresh r7 checkpoint and campaign are required.

## Failure

The r6 `stream_mprot` arm aborted at simulated tick `2529883815500` in
`Finalize_UpdateCacheFromTBE`:

```
CHI-cache-actions.sm:3457: assert(tbe.dataBlkValid.isFull())
```

The original run used `RUBY_RANDOMIZATION=1`.  A first replay omitted that
environment variable and passed the failure tick, so it is not evidence.  The
configuration-equivalent randomized replay reproduced the assertion at the
same tick and address (`0x3400080`).  That replay necessarily names the
current `vmlinux`, whose SHA no longer matches r6, so it is diagnostic evidence
only; its checkpoint, image, simulator binary, RNG setting, geometry, and
failure tick match r6.

## Root cause

This was not an H2 fill-bypass failure.  The failing request is a DMA-RNI
`ReadOnce` in upstream-owned combined state (`UD_RU` or `UC_RU`).  In inherited
CHI code, `Initiate_ReadOnce_HitUpstream` set `tbe.dataValid = true` to retain
the combined state when DCT forwarded the owner's data directly to the DMA
requester.  It did not materialize `tbe.dataBlk` or its validity mask.  The HNF
then finalized a retained cache state with `dataValid == true` and an empty
mask; the assertion correctly stopped the simulator before a potentially
uninitialized TBE could overwrite the cache entry.

The path predates STREAMING (gem5 commit `9bfffe0f34`).  STREAMING changed
message ordering sufficiently to expose it.  It is therefore recorded as an
apparatus defect, not as evidence for or against STREAMING.

## Repair and required evidence

The repair copies the already-resident cache entry into the TBE and fills its
mask in exactly the existing `cache_entry valid && tbe.dataValid false` branch.
It preserves the finalization assertion and the combined state: the retained
copy may be stale relative to the upstream owner, and that fact remains encoded
by `*_RU`.

The rebuilt simulator passed a randomized diagnostic restore through
`2529900000000`, more than 16 million ticks beyond the original assertion,
without a CHI panic.  It is still not a measurement run.  Required next
evidence is the clean, provenance-bound r7 checkpoint followed by the full
serial S1 gates and then S2 calibration.
