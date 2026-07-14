# Progress Log

## 2026-07-01

- Started unattended native-first run for phases 2-10.
- Decision: `cat` policy and CMT occupancy stay deferred because resctrl group creation
  needs root/CAP_SYS_ADMIN.
- Finding/workaround: `libnuma.so.1` exists but `numa.h` is missing, so native NUMA
  allocation/placement is implemented with direct Linux `mbind` and `move_pages`
  syscalls instead of libnuma headers.

- 2026-07-01 16:05:46 KST: Decision: unattended run uses 1 GiB fact regions by default to keep per-run timeout bounded; override with BENCH_FACT_BYTES.

- 2026-07-01 16:05:46 KST: Phase 2 build/tests starting

- 2026-07-01 16:05:46 KST: Phase 2 build/tests passed

- 2026-07-01 16:05:46 KST: Phase 3 phase-0 anchors starting

- 2026-07-01 16:05:46 KST: START phase0:node2_stream_wb: --mode stream-smoke --policy wb --fact-node 2 --fact-bytes 1g --threads 1 --cpu-list 0 --warmups 3 --reps 30

- 2026-07-01 16:05:53 KST: DONE phase0:node2_stream_wb: status=ok cov=0.00618611853

- 2026-07-01 16:05:53 KST: START phase0:local_stream_wb: --mode stream-smoke --policy wb --fact-node 0 --fact-bytes 1g --threads 1 --cpu-list 0 --warmups 3 --reps 30

- 2026-07-01 16:05:59 KST: DONE phase0:local_stream_wb: status=ok cov=0.00979875548

- 2026-07-01 16:05:59 KST: FINDING node-2 WB read 6.17 GB/s outside 15.8±20% anchor

- 2026-07-01 16:05:59 KST: Phases 4-7 native matrix starting

- 2026-07-01 16:05:59 KST: START correctness:single_check: --mode single --policy wb --fact-node 2 --hot-node 0 --fact-bytes 256m --hot-bytes 2m --threads 1 --cpu-list 0 --warmups 1 --reps 3 --check

- 2026-07-01 16:06:03 KST: DONE correctness:single_check: status=ok cov=0.00877055473

- 2026-07-01 16:06:03 KST: START nta_stream:wb_pf0: --mode stream-nta --policy wb --pf-distance 0 --fact-node 2 --fact-bytes 1g --threads 1 --cpu-list 0 --warmups 3 --reps 30

- 2026-07-01 16:06:10 KST: DONE nta_stream:wb_pf0: status=ok cov=0.00878912063

- 2026-07-01 16:06:10 KST: START nta_stream:nta_pf0: --mode stream-nta --policy nta --pf-distance 0 --fact-node 2 --fact-bytes 1g --threads 1 --cpu-list 0 --warmups 3 --reps 30

- 2026-07-01 16:06:19 KST: DONE nta_stream:nta_pf0: status=ok cov=0.00671057683

- 2026-07-01 16:06:19 KST: START nta_stream:nta_pf1: --mode stream-nta --policy nta --pf-distance 1 --fact-node 2 --fact-bytes 1g --threads 1 --cpu-list 0 --warmups 3 --reps 30

- 2026-07-01 16:06:28 KST: DONE nta_stream:nta_pf1: status=ok cov=0.00826604894

- 2026-07-01 16:06:28 KST: START nta_stream:nta_pf2: --mode stream-nta --policy nta --pf-distance 2 --fact-node 2 --fact-bytes 1g --threads 1 --cpu-list 0 --warmups 3 --reps 30

- 2026-07-01 16:06:37 KST: DONE nta_stream:nta_pf2: status=ok cov=0.00551695266

- 2026-07-01 16:06:37 KST: START nta_stream:nta_pf4: --mode stream-nta --policy nta --pf-distance 4 --fact-node 2 --fact-bytes 1g --threads 1 --cpu-list 0 --warmups 3 --reps 30

- 2026-07-01 16:06:47 KST: DONE nta_stream:nta_pf4: status=ok cov=0.00843232605

- 2026-07-01 16:06:47 KST: START nta_stream:nta_pf8: --mode stream-nta --policy nta --pf-distance 8 --fact-node 2 --fact-bytes 1g --threads 1 --cpu-list 0 --warmups 3 --reps 30

- 2026-07-01 16:07:06 KST: DONE nta_stream:nta_pf8: status=ok cov=0.00469856405

- 2026-07-01 16:07:06 KST: START nta_stream:nta_pf16: --mode stream-nta --policy nta --pf-distance 16 --fact-node 2 --fact-bytes 1g --threads 1 --cpu-list 0 --warmups 3 --reps 30

- 2026-07-01 16:07:22 KST: DONE nta_stream:nta_pf16: status=ok cov=0.000797352495

- 2026-07-01 16:07:22 KST: START nta_stream:nta_pf32: --mode stream-nta --policy nta --pf-distance 32 --fact-node 2 --fact-bytes 1g --threads 1 --cpu-list 0 --warmups 3 --reps 30

- 2026-07-01 16:07:34 KST: DONE nta_stream:nta_pf32: status=ok cov=0.00190374504

- 2026-07-01 16:07:34 KST: START nta_stream:nta_pf64: --mode stream-nta --policy nta --pf-distance 64 --fact-node 2 --fact-bytes 1g --threads 1 --cpu-list 0 --warmups 3 --reps 30

- 2026-07-01 16:07:43 KST: DONE nta_stream:nta_pf64: status=ok cov=0.00700642875

- 2026-07-01 16:07:43 KST: START nta_stream:nta_pf128: --mode stream-nta --policy nta --pf-distance 128 --fact-node 2 --fact-bytes 1g --threads 1 --cpu-list 0 --warmups 3 --reps 30

- 2026-07-01 16:07:52 KST: DONE nta_stream:nta_pf128: status=ok cov=0.0100162062

- 2026-07-01 16:07:52 KST: START nta_stream:nta_pf256: --mode stream-nta --policy nta --pf-distance 256 --fact-node 2 --fact-bytes 1g --threads 1 --cpu-list 0 --warmups 3 --reps 30

- 2026-07-01 16:08:01 KST: DONE nta_stream:nta_pf256: status=ok cov=0.00825692284

- 2026-07-01 16:08:01 KST: START nta_stream:nta_pf512: --mode stream-nta --policy nta --pf-distance 512 --fact-node 2 --fact-bytes 1g --threads 1 --cpu-list 0 --warmups 3 --reps 30

- 2026-07-01 16:08:10 KST: DONE nta_stream:nta_pf512: status=ok cov=0.0071190548

- 2026-07-01 16:08:10 KST: PREFETCHNTA disassembly present=True

- 2026-07-01 16:08:10 KST: START single:2MB_wb: --mode single --policy wb --pf-distance 0 --fact-node 2 --hot-node 0 --fact-bytes 1g --hot-bytes 2097152 --threads 1 --cpu-list 0 --warmups 3 --reps 30

- 2026-07-01 16:09:35 KST: DONE single:2MB_wb: status=ok cov=0.00379880352

- 2026-07-01 16:09:35 KST: START single:2MB_nta: --mode single --policy nta --pf-distance 32 --fact-node 2 --hot-node 0 --fact-bytes 1g --hot-bytes 2097152 --threads 1 --cpu-list 0 --warmups 3 --reps 30

- 2026-07-01 16:11:01 KST: DONE single:2MB_nta: status=ok cov=0.00299654962

- 2026-07-01 16:11:01 KST: START single:25pct_wb: --mode single --policy wb --pf-distance 0 --fact-node 2 --hot-node 0 --fact-bytes 1g --hot-bytes 83886080 --threads 1 --cpu-list 0 --warmups 3 --reps 30

- 2026-07-01 16:12:47 KST: DONE single:25pct_wb: status=ok cov=0.0082677394

- 2026-07-01 16:12:47 KST: START single:25pct_nta: --mode single --policy nta --pf-distance 32 --fact-node 2 --hot-node 0 --fact-bytes 1g --hot-bytes 83886080 --threads 1 --cpu-list 0 --warmups 3 --reps 30

- 2026-07-01 16:14:38 KST: DONE single:25pct_nta: status=ok cov=0.00939706784

- 2026-07-01 16:14:38 KST: START single:53pct_wb: --mode single --policy wb --pf-distance 0 --fact-node 2 --hot-node 0 --fact-bytes 1g --hot-bytes 177838489 --threads 1 --cpu-list 0 --warmups 3 --reps 30

- 2026-07-01 16:16:33 KST: DONE single:53pct_wb: status=ok cov=0.00834711059

- 2026-07-01 16:16:33 KST: START single:53pct_nta: --mode single --policy nta --pf-distance 32 --fact-node 2 --hot-node 0 --fact-bytes 1g --hot-bytes 177838489 --threads 1 --cpu-list 0 --warmups 3 --reps 30

- 2026-07-01 16:18:33 KST: DONE single:53pct_nta: status=ok cov=0.00806296285

- 2026-07-01 16:18:33 KST: START single:100pct_wb: --mode single --policy wb --pf-distance 0 --fact-node 2 --hot-node 0 --fact-bytes 1g --hot-bytes 335544320 --threads 1 --cpu-list 0 --warmups 3 --reps 30

- 2026-07-01 16:20:47 KST: DONE single:100pct_wb: status=ok cov=0.0101391248

- 2026-07-01 16:20:47 KST: START single:100pct_nta: --mode single --policy nta --pf-distance 32 --fact-node 2 --hot-node 0 --fact-bytes 1g --hot-bytes 335544320 --threads 1 --cpu-list 0 --warmups 3 --reps 30

- 2026-07-01 16:23:02 KST: DONE single:100pct_nta: status=ok cov=0.00294940175

- 2026-07-01 16:23:02 KST: START hot_probe:2MB_t1: --mode hot-probe --policy wb --fact-bytes 1g --hot-bytes 2097152 --threads 1 --cpu-list 0 --warmups 3 --reps 30

- 2026-07-01 16:25:17 KST: DONE hot_probe:2MB_t1: status=ok cov=0.00146104048

- 2026-07-01 16:25:17 KST: START morsel:2MB_t1_wb: --mode morsel --policy wb --fact-node 2 --hot-node 0 --fact-bytes 1g --hot-bytes 2097152 --threads 1 --cpu-list 0 --morsel 1m --warmups 3 --reps 30

- 2026-07-01 16:26:20 KST: Finding/workaround: hot-probe initially used per-probe atomic scheduling; patched future runs to use morsel-sized chunks so quiescent baseline measures probe work rather than scheduler overhead.

- 2026-07-01 16:26:40 KST: DONE morsel:2MB_t1_wb: status=ok cov=0.00358129633

- 2026-07-01 16:26:40 KST: START hot_probe:2MB_t2: --mode hot-probe --policy wb --fact-bytes 1g --hot-bytes 2097152 --threads 2 --cpu-list 0-1 --warmups 3 --reps 30

- 2026-07-01 16:27:02 KST: DONE hot_probe:2MB_t2: status=ok cov=0.00167368052

- 2026-07-01 16:27:02 KST: START morsel:2MB_t2_wb: --mode morsel --policy wb --fact-node 2 --hot-node 0 --fact-bytes 1g --hot-bytes 2097152 --threads 2 --cpu-list 0-1 --morsel 1m --warmups 3 --reps 30

- 2026-07-01 16:27:43 KST: DONE morsel:2MB_t2_wb: status=ok cov=0.00194879658

- 2026-07-01 16:27:43 KST: START hot_probe:2MB_t4: --mode hot-probe --policy wb --fact-bytes 1g --hot-bytes 2097152 --threads 4 --cpu-list 0-3 --warmups 3 --reps 30

- 2026-07-01 16:27:54 KST: DONE hot_probe:2MB_t4: status=ok cov=0.00240455954

- 2026-07-01 16:27:54 KST: START morsel:2MB_t4_wb: --mode morsel --policy wb --fact-node 2 --hot-node 0 --fact-bytes 1g --hot-bytes 2097152 --threads 4 --cpu-list 0-3 --morsel 1m --warmups 3 --reps 30

- 2026-07-01 16:28:15 KST: DONE morsel:2MB_t4_wb: status=ok cov=0.00420681152

- 2026-07-01 16:28:15 KST: START hot_probe:2MB_t8: --mode hot-probe --policy wb --fact-bytes 1g --hot-bytes 2097152 --threads 8 --cpu-list 0-7 --warmups 3 --reps 30

- 2026-07-01 16:28:21 KST: DONE hot_probe:2MB_t8: status=ok cov=0.00614475338

- 2026-07-01 16:28:21 KST: START morsel:2MB_t8_wb: --mode morsel --policy wb --fact-node 2 --hot-node 0 --fact-bytes 1g --hot-bytes 2097152 --threads 8 --cpu-list 0-7 --morsel 1m --warmups 3 --reps 30

- 2026-07-01 16:28:33 KST: DONE morsel:2MB_t8_wb: status=ok cov=0.00714778502

- 2026-07-01 16:28:33 KST: START hot_probe:2MB_t16: --mode hot-probe --policy wb --fact-bytes 1g --hot-bytes 2097152 --threads 16 --cpu-list 0-15 --warmups 3 --reps 30

- 2026-07-01 16:28:35 KST: DONE hot_probe:2MB_t16: status=ok cov=0.00777980311

- 2026-07-01 16:28:35 KST: START morsel:2MB_t16_wb: --mode morsel --policy wb --fact-node 2 --hot-node 0 --fact-bytes 1g --hot-bytes 2097152 --threads 16 --cpu-list 0-15 --morsel 1m --warmups 3 --reps 30

- 2026-07-01 16:28:42 KST: DONE morsel:2MB_t16_wb: status=ok cov=0.00589150336

- 2026-07-01 16:28:42 KST: START hot_probe:25pct_t1: --mode hot-probe --policy wb --fact-bytes 1g --hot-bytes 83886080 --threads 1 --cpu-list 0 --warmups 3 --reps 30

- 2026-07-01 16:29:38 KST: DONE hot_probe:25pct_t1: status=ok cov=0.00557383324

- 2026-07-01 16:29:38 KST: START morsel:25pct_t1_wb: --mode morsel --policy wb --fact-node 2 --hot-node 0 --fact-bytes 1g --hot-bytes 83886080 --threads 1 --cpu-list 0 --morsel 1m --warmups 3 --reps 30

- 2026-07-01 16:31:21 KST: DONE morsel:25pct_t1_wb: status=ok cov=0.00339690668

- 2026-07-01 16:31:21 KST: START hot_probe:25pct_t2: --mode hot-probe --policy wb --fact-bytes 1g --hot-bytes 83886080 --threads 2 --cpu-list 0-1 --warmups 3 --reps 30

- 2026-07-01 16:31:49 KST: DONE hot_probe:25pct_t2: status=ok cov=0.00431602784

- 2026-07-01 16:31:49 KST: START morsel:25pct_t2_wb: --mode morsel --policy wb --fact-node 2 --hot-node 0 --fact-bytes 1g --hot-bytes 83886080 --threads 2 --cpu-list 0-1 --morsel 1m --warmups 3 --reps 30

- 2026-07-01 16:32:42 KST: DONE morsel:25pct_t2_wb: status=ok cov=0.00345150236

- 2026-07-01 16:32:42 KST: START hot_probe:25pct_t4: --mode hot-probe --policy wb --fact-bytes 1g --hot-bytes 83886080 --threads 4 --cpu-list 0-3 --warmups 3 --reps 30

- 2026-07-01 16:32:56 KST: DONE hot_probe:25pct_t4: status=ok cov=0.00481262348

- 2026-07-01 16:32:56 KST: START morsel:25pct_t4_wb: --mode morsel --policy wb --fact-node 2 --hot-node 0 --fact-bytes 1g --hot-bytes 83886080 --threads 4 --cpu-list 0-3 --morsel 1m --warmups 3 --reps 30

- 2026-07-01 16:33:23 KST: DONE morsel:25pct_t4_wb: status=ok cov=0.00526266616

- 2026-07-01 16:33:23 KST: START hot_probe:25pct_t8: --mode hot-probe --policy wb --fact-bytes 1g --hot-bytes 83886080 --threads 8 --cpu-list 0-7 --warmups 3 --reps 30

- 2026-07-01 16:33:31 KST: DONE hot_probe:25pct_t8: status=ok cov=0.00500716046

- 2026-07-01 16:33:31 KST: START morsel:25pct_t8_wb: --mode morsel --policy wb --fact-node 2 --hot-node 0 --fact-bytes 1g --hot-bytes 83886080 --threads 8 --cpu-list 0-7 --morsel 1m --warmups 3 --reps 30

- 2026-07-01 16:33:46 KST: DONE morsel:25pct_t8_wb: status=ok cov=0.00584877882

- 2026-07-01 16:33:46 KST: START hot_probe:25pct_t16: --mode hot-probe --policy wb --fact-bytes 1g --hot-bytes 83886080 --threads 16 --cpu-list 0-15 --warmups 3 --reps 30

- 2026-07-01 16:33:50 KST: DONE hot_probe:25pct_t16: status=ok cov=0.00632300092

- 2026-07-01 16:33:50 KST: START morsel:25pct_t16_wb: --mode morsel --policy wb --fact-node 2 --hot-node 0 --fact-bytes 1g --hot-bytes 83886080 --threads 16 --cpu-list 0-15 --morsel 1m --warmups 3 --reps 30

- 2026-07-01 16:33:58 KST: DONE morsel:25pct_t16_wb: status=ok cov=0.00802793908

- 2026-07-01 16:33:58 KST: START hot_probe:53pct_t1: --mode hot-probe --policy wb --fact-bytes 1g --hot-bytes 177838489 --threads 1 --cpu-list 0 --warmups 3 --reps 30

- 2026-07-01 16:34:57 KST: DONE hot_probe:53pct_t1: status=ok cov=0.00510244704

- 2026-07-01 16:34:57 KST: START morsel:53pct_t1_wb: --mode morsel --policy wb --fact-node 2 --hot-node 0 --fact-bytes 1g --hot-bytes 177838489 --threads 1 --cpu-list 0 --morsel 1m --warmups 3 --reps 30

- 2026-07-01 16:36:48 KST: DONE morsel:53pct_t1_wb: status=ok cov=0.00439012671

- 2026-07-01 16:36:48 KST: START hot_probe:53pct_t2: --mode hot-probe --policy wb --fact-bytes 1g --hot-bytes 177838489 --threads 2 --cpu-list 0-1 --warmups 3 --reps 30

- 2026-07-01 16:37:18 KST: DONE hot_probe:53pct_t2: status=ok cov=0.00571087392

- 2026-07-01 16:37:18 KST: START morsel:53pct_t2_wb: --mode morsel --policy wb --fact-node 2 --hot-node 0 --fact-bytes 1g --hot-bytes 177838489 --threads 2 --cpu-list 0-1 --morsel 1m --warmups 3 --reps 30

- 2026-07-01 16:38:14 KST: DONE morsel:53pct_t2_wb: status=ok cov=0.00635772637

- 2026-07-01 16:38:14 KST: START hot_probe:53pct_t4: --mode hot-probe --policy wb --fact-bytes 1g --hot-bytes 177838489 --threads 4 --cpu-list 0-3 --warmups 3 --reps 30

- 2026-07-01 16:38:30 KST: DONE hot_probe:53pct_t4: status=ok cov=0.00520253937

- 2026-07-01 16:38:30 KST: START morsel:53pct_t4_wb: --mode morsel --policy wb --fact-node 2 --hot-node 0 --fact-bytes 1g --hot-bytes 177838489 --threads 4 --cpu-list 0-3 --morsel 1m --warmups 3 --reps 30

- 2026-07-01 16:38:59 KST: DONE morsel:53pct_t4_wb: status=ok cov=0.0106364501

- 2026-07-01 16:38:59 KST: START hot_probe:53pct_t8: --mode hot-probe --policy wb --fact-bytes 1g --hot-bytes 177838489 --threads 8 --cpu-list 0-7 --warmups 3 --reps 30

- 2026-07-01 16:39:08 KST: DONE hot_probe:53pct_t8: status=ok cov=0.00848520951

- 2026-07-01 16:39:08 KST: START morsel:53pct_t8_wb: --mode morsel --policy wb --fact-node 2 --hot-node 0 --fact-bytes 1g --hot-bytes 177838489 --threads 8 --cpu-list 0-7 --morsel 1m --warmups 3 --reps 30

- 2026-07-01 16:39:24 KST: DONE morsel:53pct_t8_wb: status=ok cov=0.00781943862

- 2026-07-01 16:39:24 KST: START hot_probe:53pct_t16: --mode hot-probe --policy wb --fact-bytes 1g --hot-bytes 177838489 --threads 16 --cpu-list 0-15 --warmups 3 --reps 30

- 2026-07-01 16:39:29 KST: DONE hot_probe:53pct_t16: status=ok cov=0.00781844964

- 2026-07-01 16:39:29 KST: START morsel:53pct_t16_wb: --mode morsel --policy wb --fact-node 2 --hot-node 0 --fact-bytes 1g --hot-bytes 177838489 --threads 16 --cpu-list 0-15 --morsel 1m --warmups 3 --reps 30

- 2026-07-01 16:39:38 KST: DONE morsel:53pct_t16_wb: status=ok cov=0.0112489632

- 2026-07-01 16:39:38 KST: START hot_probe:100pct_t1: --mode hot-probe --policy wb --fact-bytes 1g --hot-bytes 335544320 --threads 1 --cpu-list 0 --warmups 3 --reps 30

- 2026-07-01 16:40:54 KST: DONE hot_probe:100pct_t1: status=ok cov=0.00333745643

- 2026-07-01 16:40:54 KST: START morsel:100pct_t1_wb: --mode morsel --policy wb --fact-node 2 --hot-node 0 --fact-bytes 1g --hot-bytes 335544320 --threads 1 --cpu-list 0 --morsel 1m --warmups 3 --reps 30

- 2026-07-01 16:43:12 KST: DONE morsel:100pct_t1_wb: status=ok cov=0.00355121147

- 2026-07-01 16:43:12 KST: START hot_probe:100pct_t2: --mode hot-probe --policy wb --fact-bytes 1g --hot-bytes 335544320 --threads 2 --cpu-list 0-1 --warmups 3 --reps 30

- 2026-07-01 16:43:51 KST: DONE hot_probe:100pct_t2: status=ok cov=0.00237606975

- 2026-07-01 16:43:51 KST: START morsel:100pct_t2_wb: --mode morsel --policy wb --fact-node 2 --hot-node 0 --fact-bytes 1g --hot-bytes 335544320 --threads 2 --cpu-list 0-1 --morsel 1m --warmups 3 --reps 30

- 2026-07-01 16:45:01 KST: DONE morsel:100pct_t2_wb: status=ok cov=0.00544276426

- 2026-07-01 16:45:01 KST: START hot_probe:100pct_t4: --mode hot-probe --policy wb --fact-bytes 1g --hot-bytes 335544320 --threads 4 --cpu-list 0-3 --warmups 3 --reps 30

- 2026-07-01 16:45:21 KST: DONE hot_probe:100pct_t4: status=ok cov=0.00577048501

- 2026-07-01 16:45:21 KST: START morsel:100pct_t4_wb: --mode morsel --policy wb --fact-node 2 --hot-node 0 --fact-bytes 1g --hot-bytes 335544320 --threads 4 --cpu-list 0-3 --morsel 1m --warmups 3 --reps 30

- 2026-07-01 16:45:58 KST: DONE morsel:100pct_t4_wb: status=ok cov=0.00557871438

- 2026-07-01 16:45:58 KST: START hot_probe:100pct_t8: --mode hot-probe --policy wb --fact-bytes 1g --hot-bytes 335544320 --threads 8 --cpu-list 0-7 --warmups 3 --reps 30

- 2026-07-01 16:46:09 KST: DONE hot_probe:100pct_t8: status=ok cov=0.00688440245

- 2026-07-01 16:46:09 KST: START morsel:100pct_t8_wb: --mode morsel --policy wb --fact-node 2 --hot-node 0 --fact-bytes 1g --hot-bytes 335544320 --threads 8 --cpu-list 0-7 --morsel 1m --warmups 3 --reps 30

- 2026-07-01 16:46:28 KST: DONE morsel:100pct_t8_wb: status=ok cov=0.00745283296

- 2026-07-01 16:46:28 KST: START hot_probe:100pct_t16: --mode hot-probe --policy wb --fact-bytes 1g --hot-bytes 335544320 --threads 16 --cpu-list 0-15 --warmups 3 --reps 30

- 2026-07-01 16:46:35 KST: DONE hot_probe:100pct_t16: status=ok cov=0.00941661564

- 2026-07-01 16:46:35 KST: START morsel:100pct_t16_wb: --mode morsel --policy wb --fact-node 2 --hot-node 0 --fact-bytes 1g --hot-bytes 335544320 --threads 16 --cpu-list 0-15 --morsel 1m --warmups 3 --reps 30

- 2026-07-01 16:46:46 KST: DONE morsel:100pct_t16_wb: status=ok cov=0.0068782131

- 2026-07-01 16:46:46 KST: START cat_stub:single_cat: --mode single --policy cat

- 2026-07-01 16:46:46 KST: DEFERRED cat_stub:single_cat: deferred: --policy cat needs resctrl control-group privilege

- 2026-07-01 16:46:46 KST: Phase 8 GEM5 seam build starting

- 2026-07-01 16:46:49 KST: Phase 8 GEM5 seam sanity rc=0

- 2026-07-01 16:46:49 KST: Phase 10 RESULTS.md written

- 2026-07-01 16:46:49 KST: All phases complete

- 2026-07-01 16:47:49 KST: Corrected hot_probe:2MB_t1 appended after scheduling fix.

- 2026-07-01 16:47:54 KST: Phase 10 RESULTS.md written

## 2026-07-02 Gate A focused fix

- Diagnosis: prior stream loop used one volatile accumulator, creating a serial loop bottleneck; local 7.97 GB/s and CXL 6.17 GB/s were too close, indicating loop/core bottleneck rather than memory.
- Patch: added explicit page pre-fault before timing, smaps AnonHugePages reporting, THP hint for --huge2m fallback, and an unrolled read loop with eight independent accumulators.

- 2026-07-02 01:44:57 KST: Patch: explicit AVX-512 stream read path and in-process timed-loop fault counters added for Gate A.

- 2026-07-02 01:46:26 KST: Patch: switched pure stream loop from AVX-512 to AVX2-width loads to avoid AVX-512 downclock while retaining independent MLP.

- 2026-07-02 01:47:58 KST: Patch: pure stream loop now interleaves four disjoint sequential streams over the same region to increase MLP while reading every byte once.

- 2026-07-02 01:50:21 KST: Patch: increased pure stream MLP from four to eight independent sequential ranges.

- 2026-07-02 01:52:45 KST: Gate A HARD STOP: best stable node-2 WB stream is 8.8069 GB/s on CPU48 with 2 MB pages and four independent streams; target band is 12.64-18.96 GB/s. Local node-0 same loop/core is 16.4443 GB/s, so binding is valid and local is notably higher. Timed loop faults are zero; hugepages confirmed via KernelPageSize/MMUPageSize=2048 kB.

## 2026-07-02 CXL characterization/recalibration

- User accepted ~8.8-9.5 GB/s as likely device-specific single-core CXL ceiling; 15.8 GB/s paper anchor is superseded for this machine.
- Patch: added --stream-count {4,8}, --policy t0 for prefetcht0, and --mode latency pointer-chase.

- 2026-07-02 02:40:30 KST: Completed node-2 aggregate scaling characterization for 1,2,4,8,16 cores.

- 2026-07-02 02:41:06 KST: Fix: latency pointer-chase pre-fault moved before cycle initialization; prior placement corrupted next pointers.

- 2026-07-02 02:41:20 KST: Completed pointer-chase latency characterization for node 2 and node 0.

- 2026-07-02 02:43:13 KST: Completed bounded Step 2 MLP variants: prefetcht0 distance sweep and 8-stream variant.

- 2026-07-02 02:43:46 KST: Step 1/3 report written. Recalibrated CXL anchors: single-core 9.405 GB/s, aggregate ceiling 23.643 GB/s. Gate A recalibrated PASS for this host; stopping before Gate B as requested.

- 2026-07-02 02:54:36 KST: Pre-Gate-B verification: MLC absent; cxl CLI present; latency mode changed to Feistel-randomized dependent chain for 2 GiB pointer chase.

- 2026-07-02 02:56:23 KST: Pre-Gate-B verification complete: MLC absent; randomized 2 GiB pointer chase measured node2 199.16 ns vs node0 111.49 ns; CXL region0 physical range exactly matches node2 memory block range; pausing before Gate B.

## 2026-07-02 Gate B row-C pass

- Patch: corrected hash table entries from 24 bytes to the required 16 bytes using key=0 as empty sentinel. Added --mode breakdown for stream/hash/probe/aggregate/full cycles-per-tuple.

- 2026-07-02 03:14:03 KST: Completed Gate B hot-size sweep, wb-vs-nta join runs, and full-bandwidth NTA stream sweep.

- 2026-07-02 03:15:17 KST: Gate B summary written. Finding: quiescent-vs-WB same-core probe degradation is small/null across 53/100/125% LLC; NTA reduces fill counters but at lower stream bandwidth.

## 2026-07-02 morsel interference sweep

- Patch: added active_cycles_per_access to quiescent hot_probe and loaded morsel runs, accumulated across worker threads and repetitions.

- 2026-07-02 03:28:56 KST: Completed morsel quiescent-vs-loaded sweep for cores 1,2,4,8,16 and hot sets 53/100/125%.

- 2026-07-02 03:29:32 KST: Morsel sweep table and interpretation written. Finding: loaded morsel mode materially raises active probe cycles/access and MPKI versus quiescent, especially at 100/125% LLC.

- 2026-07-02 03:36:37 KST: Completed 53% morsel wb-vs-nta sweep for cores 1,2,4,8,16.

- 2026-07-02 03:37:17 KST: Morsel wb-vs-nta table written. NTA lowers MPKI at most core counts but does not recover active probe cycles; stream BW is lower. CAT attempt stopped at resctrl mkdir permission denied.

- 2026-07-02 03:44:05 KST: Completed sudo resctrl CAT 16-way 53% morsel loaded sweep for cores 1,2,4,8,16.

- 2026-07-02 03:44:37 KST: CAT same-core morsel test written. Result: CAT 16-way class worsened active probe cycles and MPKI versus unpartitioned; no leftover resctrl groups.

- 2026-07-02 04:09:26 KST: Capacity-vs-contention diagnostic and real-HW handoff section written. Finding: MPKI/cycle correlation is moderate, but extra MPKI does not explain the ~30 extra cycles; scope benefit as allocation-driven MPKI recovery plus possible contention component.

- 2026-07-02 04:18:28 KST: Completed local-node0 fact-stream morsel comparison for 53% LLC across cores 1,2,4,8,16.

- 2026-07-02 04:19:04 KST: Local-node0 vs CXL-node2 matched-aggressor morsel diagnostic written. Finding: matched bandwidth and nearly identical probe cycles; tax is generic cacheable-fill/LLC, not CXL-path-specific.
