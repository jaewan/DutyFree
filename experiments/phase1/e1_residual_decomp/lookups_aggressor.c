/*
 * lookups_aggressor.c — E1 arm A4: "lookups-only" aggressor.
 *
 * Extends the tmp_dutyfree_exp harness (reuses common.h) with a mode not
 * present in aggressor.c: N threads repeatedly re-stream a single SHARED
 * buffer sized to stay L3-resident on one CCX (default 8 MiB, < 16 MiB
 * per-CCX L3 on Bergamo), allocated on LOCAL DRAM (not CXL). After an
 * explicit warm-up pass, every access should hit in L3: full-rate coherent
 * L3 lookups from N threads, no new fills, no CXL memory traffic. This
 * isolates "shared lookup/queue occupancy" (P1 hypothesis b) from "probe-
 * filter/back-invalidation churn" (hypothesis a) and from any CXL-path
 * effect, since A1/A2/A3 all touch memory beyond L3.
 *
 * Verify near-zero MBM bytes (resctrl) for this arm before trusting the
 * victim-tax result -- if MBM shows non-trivial GB/s, the buffer is not
 * actually staying L3-resident (e.g. contention evicted it) and the "no
 * fills" premise is false; report that as a finding, do not paper over it.
 *
 * Build:  gcc -O2 -march=native -mavx2 -pthread -lnuma -lm \
 *           -I <path-to-tmp_dutyfree_exp/src> -o lookups_aggressor lookups_aggressor.c
 * Usage:  ./lookups_aggressor -t <nthreads> -c <corelist> [-s <shared_MB>] [-d <seconds>] [-n <numa_node>]
 */
#include "common.h"

typedef struct {
    int core;
    char *buf;
    size_t sz;
    volatile int *go;
    volatile int *stop;
} lctx_t;

static __attribute__((noinline))
void kern_reread(const char *buf, size_t sz)
{
    register __m256i s0 asm("ymm0") = _mm256_setzero_si256();
    register __m256i s1 asm("ymm1") = _mm256_setzero_si256();
    const char *end = buf + sz;
    for (const char *p = buf; p < end; p += CACHELINE) {
        s0 = _mm256_xor_si256(s0, _mm256_load_si256((const __m256i *)(p)));
        s1 = _mm256_xor_si256(s1, _mm256_load_si256((const __m256i *)(p + 32)));
    }
    asm volatile("" :: "x"(s0), "x"(s1));
}

static void *thread_fn(void *arg)
{
    lctx_t *t = (lctx_t *)arg;
    pin_thread(t->core);
    /* Warm-up: populate + train, several passes so the buffer settles into L3 */
    for (int p = 0; p < 8; p++) kern_reread(t->buf, t->sz);
    while (!__atomic_load_n(t->go, __ATOMIC_ACQUIRE)) _mm_pause();
    while (!__atomic_load_n(t->stop, __ATOMIC_ACQUIRE))
        kern_reread(t->buf, t->sz);
    return NULL;
}

static volatile sig_atomic_t g_stop_sig = 0;
static void sighandler(int s) { (void)s; g_stop_sig = 1; }

int main(int argc, char **argv)
{
    int nthreads = 7, cores[128], ncores = 0, duration = 16, node = LOCAL_NUMA_NODE;
    size_t shared_mb = 8;
    int opt;
    while ((opt = getopt(argc, argv, "t:c:s:d:n:h")) != -1) {
        switch (opt) {
        case 't': nthreads = atoi(optarg); break;
        case 'c': ncores = parse_corelist(optarg, cores, 128); break;
        case 's': shared_mb = (size_t)atoi(optarg); break;
        case 'd': duration = atoi(optarg); break;
        case 'n': node = atoi(optarg); break;
        default:
            fprintf(stderr, "Usage: %s -t <n> -c <corelist> [-s <shared_MB>] [-d <sec>] [-n <numa_node>]\n", argv[0]);
            return 1;
        }
    }
    if (ncores < nthreads) { fprintf(stderr, "need >= %d cores\n", nthreads); return 1; }

    size_t sz = shared_mb * 1024UL * 1024;
    void *buf = alloc_wb_node(sz, node);
    if (!buf) { fprintf(stderr, "alloc failed\n"); return 1; }
    fprintf(stderr, "[lookups_agg] shared buf %zu MB on node %d, %d threads, %ds\n",
            shared_mb, node, nthreads, duration);

    signal(SIGINT, sighandler); signal(SIGTERM, sighandler);
    volatile int go = 0, stop = 0;
    pthread_t tids[128]; lctx_t ctx[128];
    for (int i = 0; i < nthreads; i++) {
        ctx[i] = (lctx_t){ .core = cores[i], .buf = buf, .sz = sz, .go = &go, .stop = &stop };
        pthread_create(&tids[i], NULL, thread_fn, &ctx[i]);
    }
    sleep(1); /* let warm-up passes finish */
    __atomic_store_n(&go, 1, __ATOMIC_RELEASE);
    fprintf(stderr, "[lookups_agg] GO\n");
    for (int s = 0; s < duration && !g_stop_sig; s++) sleep(1);
    __atomic_store_n(&stop, 1, __ATOMIC_RELEASE);
    for (int i = 0; i < nthreads; i++) pthread_join(tids[i], NULL);
    printf("RESULT mode=lookups_only threads=%d shared_mb=%zu\n", nthreads, shared_mb);
    munmap(buf, sz);
    return 0;
}
