/*
 * stream_wb_flushbehind.c — WB streaming aggressor with clflushopt at
 * distance D behind the read pointer (E2b: silicon emulation of H2's
 * non-allocation, bounding the stream's LLC footprint to ~D bytes).
 *
 * Extends stream_wb.c (same allocation, same read kernel, same CLI
 * conventions) rather than rewriting it. D=0 means "off" (no flushing,
 * behaves like stream_wb.c).
 *
 * CLFLUSHOPT is weakly ordered -- only ordered by SFENCE w.r.t. other
 * CLFLUSHOPT/stores (Intel SDM). We SFENCE once per batch of flushed lines,
 * not per line, to avoid serializing every flush.
 *
 * Usage:
 *   ./stream_wb_flushbehind --cpu 1 --node 2 --region-gb 1 --duration-sec 60 \
 *                           --flush-distance-kb 256
 *   --flush-distance-kb 0 means off (no flush-behind, full residency).
 */

#define _GNU_SOURCE
#include <sys/mman.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <unistd.h>
#include <time.h>
#include <getopt.h>
#include <sched.h>
#include <signal.h>
#include <immintrin.h>

#include "../lib/timing.h"
#include "../lib/hugepage.h"
#include "../lib/msr.h"

#define CACHELINE 64
#define DEFAULT_REGION_GB 1
#define DEFAULT_DURATION  60.0
#define REPORT_INTERVAL   1.0
#define FLUSH_BATCH_LINES 64  /* sfence once per this many clflushopt's */

static volatile sig_atomic_t g_stop = 0;
static void handle_sigterm(int sig) { (void)sig; g_stop = 1; }

static void pin_to_cpu(int cpu)
{
    cpu_set_t cs;
    CPU_ZERO(&cs); CPU_SET(cpu, &cs);
    if (sched_setaffinity(0, sizeof(cs), &cs) < 0) { perror("sched_setaffinity"); exit(1); }
}

/*
 * Sequential 64B read sweep with a trailing flush pointer bounded to
 * flush_distance bytes behind the read pointer. Returns bytes read.
 * flush_distance == 0 disables flushing entirely (fast path, same as
 * stream_wb.c's plain sweep).
 */
static uint64_t stream_read_flushbehind(const char *buf, size_t size, size_t flush_distance)
{
    const char *p = buf;
    const char *end = buf + size;
    volatile uint64_t sink = 0;

    if (flush_distance == 0) {
        while (p < end) {
            sink ^= *(volatile const uint64_t *)p;
            p += CACHELINE;
        }
        (void)sink;
        return size;
    }

    const char *flush_p = buf;
    unsigned batch = 0;
    while (p < end) {
        sink ^= *(volatile const uint64_t *)p;
        p += CACHELINE;

        /* Keep the resident window bounded to ~flush_distance bytes behind p */
        while ((size_t)(p - flush_p) > flush_distance) {
            _mm_clflushopt((void *)flush_p);
            flush_p += CACHELINE;
            if (++batch >= FLUSH_BATCH_LINES) {
                _mm_sfence();
                batch = 0;
            }
        }
    }
    if (batch > 0) _mm_sfence();
    (void)sink;
    return size;
}

int main(int argc, char **argv)
{
    int    cpu          = 1;
    int    node         = 0;
    size_t region_gb    = DEFAULT_REGION_GB;
    double duration_sec = DEFAULT_DURATION;
    size_t flush_kb     = 0;  /* 0 = off */

    static struct option opts[] = {
        {"cpu",              required_argument, 0, 'c'},
        {"node",             required_argument, 0, 'n'},
        {"region-gb",        required_argument, 0, 'r'},
        {"duration-sec",     required_argument, 0, 'd'},
        {"flush-distance-kb",required_argument, 0, 'f'},
        {0, 0, 0, 0}
    };
    int opt, idx;
    while ((opt = getopt_long(argc, argv, "c:n:r:d:f:", opts, &idx)) != -1) {
        switch (opt) {
            case 'c': cpu          = atoi(optarg); break;
            case 'n': node         = atoi(optarg); break;
            case 'r': region_gb    = (size_t)atol(optarg); break;
            case 'd': duration_sec = atof(optarg); break;
            case 'f': flush_kb     = (size_t)atol(optarg); break;
            default: exit(1);
        }
    }

    signal(SIGTERM, handle_sigterm);
    signal(SIGINT,  handle_sigterm);

    pin_to_cpu(cpu);

    size_t region_size = region_gb * 1024UL * 1024UL * 1024UL;
    size_t flush_distance = flush_kb * 1024UL;
    void *buf = hugepage_alloc(region_size, node);
    if (buf == MAP_FAILED) exit(1);
    memset(buf, 0xAB, region_size);

    fprintf(stderr, "stream_wb_flushbehind: cpu=%d node=%d region=%zu GB duration=%.0f s "
                    "flush_distance=%zu KB (0=off)\n",
            cpu, node, region_gb, duration_sec, flush_kb);

    struct timespec t0, t1;
    clock_gettime(CLOCK_MONOTONIC, &t0);
    double deadline = t0.tv_sec + t0.tv_nsec * 1e-9 + duration_sec;

    uint64_t total_bytes = 0;
    int iteration = 0;
    double last_report = t0.tv_sec + t0.tv_nsec * 1e-9;

    while (!g_stop) {
        uint64_t swept = stream_read_flushbehind((const char *)buf, region_size, flush_distance);
        total_bytes += swept;
        iteration++;

        clock_gettime(CLOCK_MONOTONIC, &t1);
        double now = t1.tv_sec + t1.tv_nsec * 1e-9;

        if (now - last_report >= REPORT_INTERVAL) {
            double bw_gbps = (double)(swept) / (now - last_report) / 1e9;
            fprintf(stderr, "stream_wb_flushbehind [cpu%d]: iter=%d bw=%.2f GB/s\n",
                    cpu, iteration, bw_gbps);
            last_report = now;
        }
        if (now >= deadline) break;
    }

    clock_gettime(CLOCK_MONOTONIC, &t1);
    double elapsed = (t1.tv_sec - t0.tv_sec) + (t1.tv_nsec - t0.tv_nsec) * 1e-9;
    double avg_bw = (double)total_bytes / elapsed / 1e9;

    printf("{\"cpu\": %d, \"condition\": \"flushbehind\", \"region_gb\": %zu, "
           "\"flush_distance_kb\": %zu, \"iterations\": %d, \"total_bytes\": %lu, "
           "\"elapsed_sec\": %.3f, \"avg_bw_gbps\": %.3f}\n",
           cpu, region_gb, flush_kb, iteration, total_bytes, elapsed, avg_bw);

    hugepage_free(buf, region_size);
    return 0;
}
