/*
 * stream_sw_prefetch.c — WB streaming aggressor, HW prefetchers DISABLED,
 * software prefetch at a configurable distance/hint (E3 calibration:
 * BW vs SW-prefetch distance, T0 vs NTA).
 *
 * Extends stream_wb_nopf.c's MSR-disable/restore pattern (reused verbatim,
 * not reimplemented) with a configurable _mm_prefetch ahead of the read
 * pointer, using either _MM_HINT_T0 (pull into all cache levels) or
 * _MM_HINT_NTA (non-temporal hint, minimize cache pollution).
 *
 * Usage:
 *   ./stream_sw_prefetch --cpu 1 --node 2 --region-gb 1 --duration-sec 30 \
 *                        --pf-distance 16 --pf-hint t0
 *   --pf-distance 0 disables software prefetch entirely (pure demand-only,
 *   HW prefetch still off -- the "all-off" floor from E2a's MSR sweep).
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

static volatile sig_atomic_t g_stop = 0;
static void handle_sigterm(int sig) { (void)sig; g_stop = 1; }

static uint64_t g_saved_msr = (uint64_t)-1;
static int g_cpu = -1;

static void restore_on_exit(void)
{
    if (g_saved_msr != (uint64_t)-1 && g_cpu >= 0) {
        msr_pf_restore(g_cpu, g_saved_msr);
        fprintf(stderr, "stream_sw_prefetch: MSR 0x1A4 restored on cpu%d (0x%lx)\n",
                g_cpu, g_saved_msr);
    }
}

static void pin_to_cpu(int cpu)
{
    cpu_set_t cs;
    CPU_ZERO(&cs); CPU_SET(cpu, &cs);
    if (sched_setaffinity(0, sizeof(cs), &cs) < 0) { perror("sched_setaffinity"); exit(1); }
}

static uint64_t stream_read_swpf(const char *buf, size_t size, int distance_lines, int hint_nta)
{
    const char *p = buf;
    const char *end = buf + size;
    volatile uint64_t sink = 0;
    ptrdiff_t ahead = (ptrdiff_t)distance_lines * CACHELINE;

    while (p < end) {
        if (distance_lines > 0) {
            const char *pf = p + ahead;
            if (pf < end) {
                if (hint_nta) _mm_prefetch(pf, _MM_HINT_NTA);
                else          _mm_prefetch(pf, _MM_HINT_T0);
            }
        }
        sink ^= *(volatile const uint64_t *)p;
        p += CACHELINE;
    }
    (void)sink;
    return size;
}

int main(int argc, char **argv)
{
    int    cpu           = 1;
    int    node          = 0;
    size_t region_gb     = DEFAULT_REGION_GB;
    double duration_sec  = DEFAULT_DURATION;
    int    pf_distance   = 0;
    int    hint_nta      = 0;  /* 0 = T0, 1 = NTA */

    static struct option opts[] = {
        {"cpu",          required_argument, 0, 'c'},
        {"node",         required_argument, 0, 'n'},
        {"region-gb",    required_argument, 0, 'r'},
        {"duration-sec", required_argument, 0, 'd'},
        {"pf-distance",  required_argument, 0, 'p'},
        {"pf-hint",      required_argument, 0, 'h'},
        {0, 0, 0, 0}
    };
    int opt, idx;
    while ((opt = getopt_long(argc, argv, "c:n:r:d:p:h:", opts, &idx)) != -1) {
        switch (opt) {
            case 'c': cpu          = atoi(optarg); break;
            case 'n': node         = atoi(optarg); break;
            case 'r': region_gb    = (size_t)atol(optarg); break;
            case 'd': duration_sec = atof(optarg); break;
            case 'p': pf_distance  = atoi(optarg); break;
            case 'h': hint_nta     = (strcmp(optarg, "nta") == 0); break;
            default: exit(1);
        }
    }

    signal(SIGTERM, handle_sigterm);
    signal(SIGINT,  handle_sigterm);

    pin_to_cpu(cpu);
    g_cpu = cpu;
    atexit(restore_on_exit);

    g_saved_msr = msr_pf_disable(cpu, 0xF);
    if (g_saved_msr == (uint64_t)-1) {
        fprintf(stderr, "stream_sw_prefetch: MSR disable failed on cpu%d — aborting\n", cpu);
        exit(1);
    }
    fprintf(stderr, "stream_sw_prefetch: MSR 0x1A4 disabled on cpu%d (saved=0x%lx)\n",
            cpu, g_saved_msr);

    size_t region_size = region_gb * 1024UL * 1024UL * 1024UL;
    void *buf = hugepage_alloc(region_size, node);
    if (buf == MAP_FAILED) exit(1);
    memset(buf, 0xAB, region_size);

    fprintf(stderr, "stream_sw_prefetch: cpu=%d node=%d region=%zu GB duration=%.0f s "
                    "pf_distance=%d lines hint=%s\n",
            cpu, node, region_gb, duration_sec, pf_distance, hint_nta ? "NTA" : "T0");

    struct timespec t0, t1;
    clock_gettime(CLOCK_MONOTONIC, &t0);
    double deadline = t0.tv_sec + t0.tv_nsec * 1e-9 + duration_sec;

    uint64_t total_bytes = 0;
    int iteration = 0;
    double last_report = t0.tv_sec + t0.tv_nsec * 1e-9;

    while (!g_stop) {
        uint64_t swept = stream_read_swpf((const char *)buf, region_size, pf_distance, hint_nta);
        total_bytes += swept;
        iteration++;

        clock_gettime(CLOCK_MONOTONIC, &t1);
        double now = t1.tv_sec + t1.tv_nsec * 1e-9;
        if (now - last_report >= REPORT_INTERVAL) {
            double bw_gbps = (double)(swept) / (now - last_report) / 1e9;
            fprintf(stderr, "stream_sw_prefetch [cpu%d]: iter=%d bw=%.2f GB/s\n",
                    cpu, iteration, bw_gbps);
            last_report = now;
        }
        if (now >= deadline) break;
    }

    clock_gettime(CLOCK_MONOTONIC, &t1);
    double elapsed = (t1.tv_sec - t0.tv_sec) + (t1.tv_nsec - t0.tv_nsec) * 1e-9;
    double avg_bw = (double)total_bytes / elapsed / 1e9;

    printf("{\"cpu\": %d, \"region_gb\": %zu, \"pf_distance_lines\": %d, "
           "\"pf_hint\": \"%s\", \"iterations\": %d, \"total_bytes\": %lu, "
           "\"elapsed_sec\": %.3f, \"avg_bw_gbps\": %.3f}\n",
           cpu, region_gb, pf_distance, hint_nta ? "NTA" : "T0",
           iteration, total_bytes, elapsed, avg_bw);

    hugepage_free(buf, region_size);
    return 0;
}
