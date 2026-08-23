/*
 * amd_flushbehind_aggressor.c — Phase 2.4: AMD flush-behind streamer,
 * the cross-vendor discriminator between the occupancy model and the
 * capacity model for the AMD CAT residual (see
 * PHASE2_AMD_FLUSHBEHIND_PREREGISTRATION.md, written before this file).
 *
 * Extends the tmp_dutyfree_exp harness (reuses common.h, matches
 * aggressor.c's per-thread-slice-of-a-shared-CXL-buffer convention) with a
 * clflushopt-at-distance-D kernel per thread, mirroring the Intel-side
 * stream_wb_flushbehind.c design: each thread reads sequentially through
 * its own slice and issues clflushopt on lines more than flush_distance
 * bytes behind its own read pointer, batched sfence every 64 lines.
 *
 * flush_distance_kb == 0 means off (no flushing, full residency -- same as
 * aggressor.c's plain wb_load mode, included in the D sweep as the
 * already-established A1 gate point, not a new measurement).
 *
 * Build:  gcc -O2 -march=native -mavx2 -pthread -o amd_flushbehind_aggressor \
 *           amd_flushbehind_aggressor.c -lnuma -lm
 * Usage:  ./amd_flushbehind_aggressor -t 7 -c 1,2,3,4,5,6,7 -N 2 -s 64 -d 16 \
 *           -f 256   (KiB; 0 = off)
 */
#include "common.h"

#define FLUSH_BATCH_LINES 64

typedef struct {
    int core;
    char *buf;
    size_t sz;
    size_t flush_distance;  /* bytes; 0 = off */
    volatile int *go;
    volatile int *stop;
    uint64_t total_bytes;
} tctx_t;

static __attribute__((noinline))
uint64_t kern_flushbehind(const char *buf, size_t sz, size_t flush_distance)
{
    const char *p = buf;
    const char *end = buf + sz;
    register __m256i s0 asm("ymm0") = _mm256_setzero_si256();
    register __m256i s1 asm("ymm1") = _mm256_setzero_si256();

    if (flush_distance == 0) {
        for (; p < end; p += CACHELINE) {
            s0 = _mm256_xor_si256(s0, _mm256_load_si256((const __m256i *)(p)));
            s1 = _mm256_xor_si256(s1, _mm256_load_si256((const __m256i *)(p + 32)));
        }
        asm volatile("" :: "x"(s0), "x"(s1));
        return sz;
    }

    const char *flush_p = buf;
    unsigned batch = 0;
    for (; p < end; p += CACHELINE) {
        s0 = _mm256_xor_si256(s0, _mm256_load_si256((const __m256i *)(p)));
        s1 = _mm256_xor_si256(s1, _mm256_load_si256((const __m256i *)(p + 32)));
        while ((size_t)(p + CACHELINE - flush_p) > flush_distance) {
            _mm_clflushopt((void *)flush_p);
            flush_p += CACHELINE;
            if (++batch >= FLUSH_BATCH_LINES) {
                _mm_sfence();
                batch = 0;
            }
        }
    }
    if (batch > 0) _mm_sfence();
    asm volatile("" :: "x"(s0), "x"(s1));
    return sz;
}

static volatile int g_ready = 0;

static void *thread_fn(void *arg)
{
    tctx_t *t = (tctx_t *)arg;
    pin_thread(t->core);

    /* Warm-up passes (unflushed, to populate + train), matching aggressor.c */
    uint64_t w_start = getns();
    for (int p = 0; p < 2; p++) {
        kern_flushbehind(t->buf, t->sz, 0);
        if (getns() - w_start > 30000000000ULL) break;
    }

    __atomic_fetch_add(&g_ready, 1, __ATOMIC_RELEASE);
    while (!__atomic_load_n(t->go, __ATOMIC_ACQUIRE))
        _mm_pause();

    while (!__atomic_load_n(t->stop, __ATOMIC_ACQUIRE)) {
        t->total_bytes += kern_flushbehind(t->buf, t->sz, t->flush_distance);
    }
    return NULL;
}

static volatile sig_atomic_t g_stop_sig = 0;
static void sighandler(int s) { (void)s; g_stop_sig = 1; }

int main(int argc, char **argv)
{
    int nthreads = 7, cores[128], ncores = 0, duration = 16, node = CXL_NUMA_NODE;
    size_t per_mb = 64, flush_kb = 0;
    int opt;
    while ((opt = getopt(argc, argv, "t:c:s:d:N:f:h")) != -1) {
        switch (opt) {
        case 't': nthreads = atoi(optarg); break;
        case 'c': ncores = parse_corelist(optarg, cores, 128); break;
        case 's': per_mb = (size_t)atoi(optarg); break;
        case 'd': duration = atoi(optarg); break;
        case 'N': node = atoi(optarg); break;
        case 'f': flush_kb = (size_t)atoi(optarg); break;
        default:
            fprintf(stderr, "Usage: %s -t <n> -c <corelist> [-s <per_thread_MB>] "
                    "[-d <sec>] [-N <mem_node>] [-f <flush_distance_KiB>, 0=off]\n", argv[0]);
            return 1;
        }
    }
    if (nthreads < 1 || ncores < nthreads) { fprintf(stderr, "need >= %d cores\n", nthreads); return 1; }

    size_t per_sz = per_mb * 1024UL * 1024;
    size_t total_sz = per_sz * (size_t)nthreads;
    size_t flush_distance = flush_kb * 1024UL;

    char *base = (char *)alloc_wb_cxl(total_sz);
    if (!base) { fprintf(stderr, "[amd_flushbehind] FATAL: could not map CXL memory.\n"); return 1; }
    fprintf(stderr, "[amd_flushbehind] mapped %zu MB, %d threads, node=%d, flush_distance=%zu KiB (0=off)\n",
            total_sz / (1024 * 1024), nthreads, node, flush_kb);

    signal(SIGINT, sighandler); signal(SIGTERM, sighandler);
    volatile int go = 0, stop = 0;
    pthread_t tids[128]; tctx_t ctx[128];
    g_ready = 0;
    for (int i = 0; i < nthreads; i++) {
        ctx[i] = (tctx_t){ .core = cores[i], .buf = base + (size_t)i * per_sz, .sz = per_sz,
                            .flush_distance = flush_distance, .go = &go, .stop = &stop };
        pthread_create(&tids[i], NULL, thread_fn, &ctx[i]);
    }
    while (__atomic_load_n(&g_ready, __ATOMIC_ACQUIRE) < nthreads) _mm_pause();
    usleep(10000);
    fprintf(stderr, "[amd_flushbehind] GO\n");
    uint64_t t0 = getns();
    __atomic_store_n(&go, 1, __ATOMIC_RELEASE);
    for (int s = 0; s < duration && !g_stop_sig; s++) sleep(1);
    __atomic_store_n(&stop, 1, __ATOMIC_RELEASE);

    double agg_bytes = 0;
    for (int i = 0; i < nthreads; i++) {
        pthread_join(tids[i], NULL);
        agg_bytes += (double)ctx[i].total_bytes;
    }
    double elapsed = (double)(getns() - t0) / 1e9;
    double agg_bw = agg_bytes / elapsed / 1e9;
    printf("RESULT mode=flushbehind threads=%d flush_kb=%zu bw_gbps=%.3f\n",
           nthreads, flush_kb, agg_bw);

    munmap(base, total_sz);
    return 0;
}
