/* Quick diagnostic: does an unrolled/vectorized (higher-MLP) read kernel
 * reach closer to the paper's ~15.8 GB/s single-core WB CXL figure than
 * stream_wb.c's single scalar 8B-load-per-line loop? Not a new experiment
 * arm -- diagnostic evidence for REPRO_FAILURE.md. */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <unistd.h>
#include <time.h>
#include <sched.h>
#include <sys/mman.h>
#include <numa.h>
#include <numaif.h>
#include <immintrin.h>

int main(int argc, char **argv) {
    int cpu = argc > 1 ? atoi(argv[1]) : 1;
    int node = argc > 2 ? atoi(argv[2]) : 2;
    size_t gb = argc > 3 ? atol(argv[3]) : 16;
    double dur = argc > 4 ? atof(argv[4]) : 8.0;

    cpu_set_t cs; CPU_ZERO(&cs); CPU_SET(cpu, &cs);
    sched_setaffinity(0, sizeof(cs), &cs);

    size_t sz = gb * 1024UL * 1024 * 1024;
    void *p = mmap(NULL, sz, PROT_READ | PROT_WRITE,
                   MAP_ANONYMOUS | MAP_PRIVATE | MAP_HUGETLB | MAP_POPULATE, -1, 0);
    if (p == MAP_FAILED) { perror("mmap"); return 1; }
    unsigned long mask = 1UL << node;
    if (mbind(p, sz, MPOL_BIND, &mask, sizeof(mask) * 8, MPOL_MF_MOVE | MPOL_MF_STRICT) < 0) {
        perror("mbind"); return 1;
    }
    memset(p, 0xAB, sz);

    struct timespec t0, t1;
    clock_gettime(CLOCK_MONOTONIC, &t0);
    double deadline = t0.tv_sec + t0.tv_nsec * 1e-9 + dur;
    uint64_t total = 0;
    char *buf = (char *)p;
    for (;;) {
        register __m256i s0 asm("ymm0") = _mm256_setzero_si256();
        register __m256i s1 asm("ymm1") = _mm256_setzero_si256();
        register __m256i s2 asm("ymm2") = _mm256_setzero_si256();
        register __m256i s3 asm("ymm3") = _mm256_setzero_si256();
        const char *end = buf + sz;
        for (const char *q = buf; q < end; q += 128) {
            s0 = _mm256_xor_si256(s0, _mm256_load_si256((const __m256i *)(q)));
            s1 = _mm256_xor_si256(s1, _mm256_load_si256((const __m256i *)(q + 32)));
            s2 = _mm256_xor_si256(s2, _mm256_load_si256((const __m256i *)(q + 64)));
            s3 = _mm256_xor_si256(s3, _mm256_load_si256((const __m256i *)(q + 96)));
        }
        asm volatile("" :: "x"(s0), "x"(s1), "x"(s2), "x"(s3));
        total += sz;
        clock_gettime(CLOCK_MONOTONIC, &t1);
        double now = t1.tv_sec + t1.tv_nsec * 1e-9;
        if (now >= deadline) break;
    }
    double elapsed = (t1.tv_sec - t0.tv_sec) + (t1.tv_nsec - t0.tv_nsec) * 1e-9;
    printf("{\"cpu\": %d, \"node\": %d, \"region_gb\": %zu, \"kernel\": \"avx2_4reg_unrolled\", "
           "\"total_bytes\": %lu, \"elapsed_sec\": %.3f, \"avg_bw_gbps\": %.3f}\n",
           cpu, node, gb, total, elapsed, (double)total / elapsed / 1e9);
    return 0;
}
