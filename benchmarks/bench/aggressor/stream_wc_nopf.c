/*
 * stream_wc_nopf.c - MOVNTDQA loads on WB pages, hardware prefetchers DISABLED.
 *
 * ADDED 2026-08-24 for T2 (see experiments/asplos/T2_WBWC_PREREG_2026-08-24.md).
 *
 * Why this arm exists. stream_wc.c is named "WC" but is MOVNTDQA-on-WB with the
 * hardware prefetchers left ON, and stream_nt.c is the same program plus an MSR
 * warning. Neither is a proxy for the write-combining memory type, whose two
 * defining properties are (i) no allocation in the cache hierarchy and (ii) no
 * hardware prefetch. This file supplies (ii) as well, by disabling all four
 * prefetchers on the measuring core via MSR 0x1A4 with a read-back verify.
 *
 * It is STILL A PROXY, not WC. True WC needs PAT manipulation from the kernel.
 * Label it as a proxy wherever it is reported.
 *
 * The inner loop is byte-identical to stream_wc.c's so that the ONLY difference
 * between the two arms is prefetcher state. Do not "improve" it here.
 *
 * MSR 0x1A4 is Intel-specific. On AMD this is expected to fail loudly
 * (msr_pf_disable verifies and the caller exits 1). A silent success on AMD
 * would be an F12 hazard, not a result -- see the pre-registration's
 * cross-check.
 *
 * Usage:
 *   ./stream_wc_nopf --cpu 1 --node 0 --region-gb 2 --duration-sec 10
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
        fprintf(stderr, "stream_wc_nopf: MSR 0x1A4 restored on cpu%d (0x%lx)\n",
                g_cpu, g_saved_msr);
    }
}

static void pin_to_cpu(int cpu)
{
    cpu_set_t cs;
    CPU_ZERO(&cs); CPU_SET(cpu, &cs);
    if (sched_setaffinity(0, sizeof(cs), &cs) < 0) { perror("sched_setaffinity"); exit(1); }
}

/* Sequential MOVNTDQA sweep; returns bytes read.
 * The __m128i MOVNTDQA instruction issues a 16-byte NT load.
 * We issue 4 back-to-back per cache line (4 × 16 = 64 bytes). */
static uint64_t stream_nt_read_once(const char *buf, size_t size)
{
    const __m128i *p   = (const __m128i *)buf;
    const __m128i *end = (const __m128i *)(buf + size);
    volatile __m128i sink;
    while (p < end) {
        sink = _mm_stream_load_si128((__m128i *)p + 0);
        sink = _mm_stream_load_si128((__m128i *)p + 1);
        sink = _mm_stream_load_si128((__m128i *)p + 2);
        sink = _mm_stream_load_si128((__m128i *)p + 3);
        p += 4;  /* 4 × 16B = 64B = one cache line */
    }
    _mm_sfence();
    (void)sink;
    return size;
}

int main(int argc, char **argv)
{
    int    cpu         = 1;
    int    node        = 0;
    size_t region_gb   = DEFAULT_REGION_GB;
    double duration_sec = DEFAULT_DURATION;

    static struct option opts[] = {
        {"cpu",         required_argument, 0, 'c'},
        {"node",        required_argument, 0, 'n'},
        {"region-gb",   required_argument, 0, 'r'},
        {"duration-sec",required_argument, 0, 'd'},
        {0, 0, 0, 0}
    };
    int opt, idx;
    while ((opt = getopt_long(argc, argv, "c:n:r:d:", opts, &idx)) != -1) {
        switch (opt) {
            case 'c': cpu        = atoi(optarg); break;
            case 'n': node       = atoi(optarg); break;
            case 'r': region_gb  = (size_t)atol(optarg); break;
            case 'd': duration_sec = atof(optarg); break;
            default: exit(1);
        }
    }

    signal(SIGTERM, handle_sigterm);
    signal(SIGINT,  handle_sigterm);

    g_cpu = cpu;
    atexit(restore_on_exit);
    pin_to_cpu(cpu);

    /* Disable all four hardware prefetchers on this core, and verify. */
    g_saved_msr = msr_pf_disable(cpu, 0xF);
    if (g_saved_msr == (uint64_t)-1) {
        fprintf(stderr, "stream_wc_nopf: FATAL: cannot write MSR 0x1A4 on cpu%d\n"
                "  (Intel-only register; on AMD this arm is UNAVAILABLE)\n", cpu);
        exit(1);
    }
    uint64_t verify = 0;
    if (msr_read(cpu, 0x1A4, &verify) < 0 || (verify & 0xF) != 0xF) {
        fprintf(stderr, "stream_wc_nopf: ERROR: MSR verify failed: got 0x%lx "
                "(expected bits[3:0]=0xF)\n", verify);
        exit(1);
    }
    fprintf(stderr, "stream_wc_nopf: MSR 0x1A4 cpu%d = 0x%lx (prefetchers OFF)\n",
            cpu, verify);

    size_t region_size = region_gb * 1024UL * 1024UL * 1024UL;

    /* Ensure 16-byte alignment for MOVNTDQA */
    void *buf = hugepage_alloc(region_size, node);
    if (buf == MAP_FAILED) exit(1);
    if (((uintptr_t)buf & 15) != 0) {
        fprintf(stderr, "stream_wc_nopf: ERROR: hugepage not 16-byte aligned\n");
        exit(1);
    }
    memset(buf, 0xAB, region_size);

    fprintf(stderr, "stream_wc_nopf (MOVNTDQA-on-WB, pf=OFF): cpu=%d node=%d "
            "region=%zu GB duration=%.0f s\n",
            cpu, node, region_gb, duration_sec);

    struct timespec t0, t1;
    clock_gettime(CLOCK_MONOTONIC, &t0);
    double deadline = t0.tv_sec + t0.tv_nsec * 1e-9 + duration_sec;

    uint64_t total_bytes = 0;
    int iteration = 0;
    double last_report = t0.tv_sec + t0.tv_nsec * 1e-9;

    while (!g_stop) {
        uint64_t swept = stream_nt_read_once((const char *)buf, region_size);
        total_bytes += swept;
        iteration++;

        clock_gettime(CLOCK_MONOTONIC, &t1);
        double now = t1.tv_sec + t1.tv_nsec * 1e-9;

        if (now - last_report >= REPORT_INTERVAL) {
            double bw_gbps = (double)(swept) / (now - last_report) / 1e9;
            fprintf(stderr, "stream_wc_nopf [cpu%d]: iter=%d bw=%.2f GB/s\n",
                    cpu, iteration, bw_gbps);
            last_report = now;
        }

        if (now >= deadline) break;
    }

    clock_gettime(CLOCK_MONOTONIC, &t1);
    double elapsed = (t1.tv_sec - t0.tv_sec) + (t1.tv_nsec - t0.tv_nsec) * 1e-9;
    double avg_bw = (double)total_bytes / elapsed / 1e9;

    printf("{\"cpu\": %d, \"condition\": \"Cp_wc_nopf\", \"region_gb\": %zu, "
           "\"iterations\": %d, \"total_bytes\": %lu, "
           "\"elapsed_sec\": %.3f, \"avg_bw_gbps\": %.3f}\n",
           cpu, region_gb, iteration, total_bytes, elapsed, avg_bw);

    hugepage_free(buf, region_size);
    return 0;
}
