/*
 * amd_delta_aggressor.c -- delta-audit controls for AMD flush-behind.
 *
 * Built against tmp_dutyfree_exp/src/common.h on broker:
 *   gcc -O2 -march=native -mavx2 -pthread -I/home/domin/tmp_dutyfree_exp/src \
 *     -o /home/domin/tmp_dutyfree_exp/bin/amd_delta_aggressor \
 *     amd_delta_aggressor.c -lnuma -lm
 */
#include "common.h"

#define FLUSH_BATCH_LINES 64

typedef enum {
    MODE_FLUSHBEHIND = 0,
    MODE_WB_PLUS_FLUSH = 1,
} delta_mode_t;

typedef struct {
    int core;
    delta_mode_t mode;
    char *stream_buf;
    char *flush_buf;
    size_t stream_sz;
    size_t flush_sz;
    size_t flush_distance;
    int flush_repeats;
    double flush_ratio;
    double target_gbps_per_thread;
    volatile int *go;
    volatile int *stop;
    uint64_t stream_bytes;
    uint64_t flush_ops;
} tctx_t;

static __attribute__((noinline))
void touch_line(const char *p)
{
    register __m256i s0 asm("ymm0") = _mm256_load_si256((const __m256i *)p);
    register __m256i s1 asm("ymm1") = _mm256_load_si256((const __m256i *)(p + 32));
    asm volatile("" :: "x"(s0), "x"(s1));
}

static __attribute__((noinline))
uint64_t stream_wb(const char *buf, size_t sz)
{
    const char *end = buf + sz;
    for (const char *p = buf; p < end; p += CACHELINE)
        touch_line(p);
    return sz;
}

static __attribute__((noinline))
uint64_t stream_flushbehind(const char *buf, size_t sz, size_t flush_distance,
                            int flush_repeats, uint64_t *flush_ops)
{
    const char *flush_p = buf;
    const char *end = buf + sz;
    unsigned batch = 0;

    for (const char *p = buf; p < end; p += CACHELINE) {
        touch_line(p);
        while ((size_t)(p + CACHELINE - flush_p) > flush_distance) {
            for (int r = 0; r < flush_repeats; r++) {
                _mm_clflushopt((void *)flush_p);
                (*flush_ops)++;
                if (++batch >= FLUSH_BATCH_LINES) {
                    _mm_sfence();
                    batch = 0;
                }
            }
            flush_p += CACHELINE;
        }
    }
    if (batch > 0)
        _mm_sfence();
    return sz;
}

static __attribute__((noinline))
void flush_resident_line(char *p, uint64_t *flush_ops, unsigned *batch)
{
    touch_line(p);
    _mm_clflushopt((void *)p);
    (*flush_ops)++;
    if (++(*batch) >= FLUSH_BATCH_LINES) {
        _mm_sfence();
        *batch = 0;
    }
}

static __attribute__((noinline))
uint64_t stream_wb_plus_flush(char *stream_buf, size_t stream_sz,
                              char *flush_buf, size_t flush_sz,
                              double flush_ratio, uint64_t *flush_ops)
{
    const char *end = stream_buf + stream_sz;
    char *fp = flush_buf;
    char *fend = flush_buf + flush_sz;
    double credit = 0.0;
    unsigned batch = 0;

    for (const char *p = stream_buf; p < end; p += CACHELINE) {
        touch_line(p);
        credit += flush_ratio;
        while (credit >= 1.0) {
            flush_resident_line(fp, flush_ops, &batch);
            fp += CACHELINE;
            if (fp >= fend)
                fp = flush_buf;
            credit -= 1.0;
        }
    }
    if (batch > 0)
        _mm_sfence();
    return stream_sz;
}

static volatile int g_ready = 0;

static void *thread_fn(void *arg)
{
    tctx_t *t = (tctx_t *)arg;
    pin_thread(t->core);

    for (int p = 0; p < 2; p++) {
        stream_wb(t->stream_buf, t->stream_sz);
        if (t->flush_buf)
            stream_wb(t->flush_buf, t->flush_sz);
    }

    __atomic_fetch_add(&g_ready, 1, __ATOMIC_RELEASE);
    while (!__atomic_load_n(t->go, __ATOMIC_ACQUIRE))
        _mm_pause();

    uint64_t t0 = getns();
    while (!__atomic_load_n(t->stop, __ATOMIC_ACQUIRE)) {
        if (t->mode == MODE_FLUSHBEHIND) {
            t->stream_bytes += stream_flushbehind(t->stream_buf, t->stream_sz,
                                                  t->flush_distance,
                                                  t->flush_repeats,
                                                  &t->flush_ops);
        } else {
            t->stream_bytes += stream_wb_plus_flush(t->stream_buf, t->stream_sz,
                                                    t->flush_buf, t->flush_sz,
                                                    t->flush_ratio,
                                                    &t->flush_ops);
        }
        if (t->target_gbps_per_thread > 0.0) {
            double target_bps = t->target_gbps_per_thread * 1e9;
            uint64_t target_ns = (uint64_t)((double)t->stream_bytes * 1e9 / target_bps);
            while (!__atomic_load_n(t->stop, __ATOMIC_ACQUIRE) && getns() - t0 < target_ns)
                _mm_pause();
        }
    }
    return NULL;
}

static volatile sig_atomic_t g_stop_sig = 0;
static void sighandler(int s) { (void)s; g_stop_sig = 1; }

static void usage(const char *p)
{
    fprintf(stderr,
        "Usage: %s -m flushbehind|wb_plus_flush -t <n> -c <cores> [-d sec]\n"
        "          [-s stream_MB] [-F flush_repeats] [-f flush_distance_KiB]\n"
        "          [-q flush_ops_per_stream_line] [-S flushbuf_MB] [-N cxl_node]\n"
        "          [-R total_target_stream_GBps]\n",
        p);
    exit(1);
}

int main(int argc, char **argv)
{
    delta_mode_t mode = MODE_FLUSHBEHIND;
    int nthreads = 7, cores[128], ncores = 0, duration = 18, node = CXL_NUMA_NODE;
    size_t stream_mb = 64, flush_mb = 4, flush_kb = 256;
    int flush_repeats = 1;
    double flush_ratio = 0.69;
    double target_gbps_total = 0.0;
    int opt;

    while ((opt = getopt(argc, argv, "m:t:c:d:s:S:f:F:q:N:R:h")) != -1) {
        switch (opt) {
        case 'm':
            if (strcmp(optarg, "flushbehind") == 0)
                mode = MODE_FLUSHBEHIND;
            else if (strcmp(optarg, "wb_plus_flush") == 0)
                mode = MODE_WB_PLUS_FLUSH;
            else
                usage(argv[0]);
            break;
        case 't': nthreads = atoi(optarg); break;
        case 'c': ncores = parse_corelist(optarg, cores, 128); break;
        case 'd': duration = atoi(optarg); break;
        case 's': stream_mb = (size_t)atoi(optarg); break;
        case 'S': flush_mb = (size_t)atoi(optarg); break;
        case 'f': flush_kb = (size_t)atoi(optarg); break;
        case 'F': flush_repeats = atoi(optarg); break;
        case 'q': flush_ratio = atof(optarg); break;
        case 'N': node = atoi(optarg); break;
        case 'R': target_gbps_total = atof(optarg); break;
        default: usage(argv[0]);
        }
    }

    if (nthreads < 1 || ncores < nthreads || flush_repeats < 1)
        usage(argv[0]);

    size_t stream_sz = stream_mb * 1024UL * 1024;
    size_t total_stream_sz = stream_sz * (size_t)nthreads;
    char *stream_base = (char *)alloc_wb_cxl(total_stream_sz);
    if (!stream_base) {
        fprintf(stderr, "FATAL: could not allocate CXL stream buffer on node %d\n", node);
        return 1;
    }

    size_t flush_sz = flush_mb * 1024UL * 1024;
    size_t total_flush_sz = flush_sz * (size_t)nthreads;
    char *flush_base = NULL;
    if (mode == MODE_WB_PLUS_FLUSH) {
        flush_base = (char *)alloc_wb_node(total_flush_sz, LOCAL_NUMA_NODE);
        if (!flush_base) {
            fprintf(stderr, "FATAL: could not allocate disjoint flush buffer\n");
            return 1;
        }
    }

    signal(SIGINT, sighandler);
    signal(SIGTERM, sighandler);
    volatile int go = 0, stop = 0;
    pthread_t tids[128];
    tctx_t ctx[128];
    g_ready = 0;

    for (int i = 0; i < nthreads; i++) {
        ctx[i] = (tctx_t){
            .core = cores[i],
            .mode = mode,
            .stream_buf = stream_base + (size_t)i * stream_sz,
            .flush_buf = flush_base ? flush_base + (size_t)i * flush_sz : NULL,
            .stream_sz = stream_sz,
            .flush_sz = flush_sz,
            .flush_distance = flush_kb * 1024UL,
            .flush_repeats = flush_repeats,
            .flush_ratio = flush_ratio,
            .target_gbps_per_thread = target_gbps_total > 0.0 ? target_gbps_total / (double)nthreads : 0.0,
            .go = &go,
            .stop = &stop,
        };
        pthread_create(&tids[i], NULL, thread_fn, &ctx[i]);
    }

    while (__atomic_load_n(&g_ready, __ATOMIC_ACQUIRE) < nthreads)
        _mm_pause();
    usleep(10000);
    uint64_t t0 = getns();
    __atomic_store_n(&go, 1, __ATOMIC_RELEASE);
    for (int s = 0; s < duration && !g_stop_sig; s++)
        sleep(1);
    __atomic_store_n(&stop, 1, __ATOMIC_RELEASE);

    double stream_bytes = 0.0, flush_ops = 0.0;
    for (int i = 0; i < nthreads; i++) {
        pthread_join(tids[i], NULL);
        stream_bytes += (double)ctx[i].stream_bytes;
        flush_ops += (double)ctx[i].flush_ops;
    }
    double elapsed = (double)(getns() - t0) / 1e9;
    printf("RESULT mode=%s threads=%d stream_bw_gbps=%.3f flush_mops=%.3f "
           "flush_ops=%.0f elapsed=%.6f flush_repeats=%d flush_ratio=%.6f\n",
           mode == MODE_FLUSHBEHIND ? "flushbehind" : "wb_plus_flush",
           nthreads, stream_bytes / elapsed / 1e9, flush_ops / elapsed / 1e6,
           flush_ops, elapsed, flush_repeats, flush_ratio);

    if (flush_base)
        munmap(flush_base, total_flush_sz);
    munmap(stream_base, total_stream_sz);
    return 0;
}
