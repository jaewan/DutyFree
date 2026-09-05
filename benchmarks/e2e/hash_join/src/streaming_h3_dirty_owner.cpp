// SPDX-License-Identifier: MIT
/*
 * Coherent-ReadOnce correctness gate for H3.
 *
 * CPU 0 leaves the youngest object line dirty in its WB cache.  Without any
 * clean or flush, the FS build marks the object STREAMING with mprotect and
 * CPU 1 reads it.  Correct H3 must resolve the existing owner
 * coherently while declining to enroll or retain the new reader.  Any store
 * or atomic carrying the STREAMING tag is a simulator error independently of
 * this program's checksum.
 */

#include <pthread.h>
#include <sched.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <string.h>
#include <sys/mman.h>

#define BYTES (64UL * 1024)
#define LINE 64UL
#ifndef PROT_STREAMING
#define PROT_STREAMING 0x10
#endif

struct ProducerArgs {
    volatile uint64_t *object;
    uint64_t generation;
    int actual_cpu;
};

static void pin_cpu(int cpu)
{
    cpu_set_t set;
    CPU_ZERO(&set);
    CPU_SET(cpu, &set);
    if (pthread_setaffinity_np(pthread_self(), sizeof(set), &set) != 0) {
        perror("pthread_setaffinity_np");
        exit(2);
    }
}

static uint64_t expected(uint64_t generation, size_t line)
{
    return 0x6a09e667f3bcc909ULL * generation ^
           (0x9e3779b97f4a7c15ULL * (line + 1));
}

static void *produce(void *opaque)
{
    auto *args = static_cast<ProducerArgs *>(opaque);
    pin_cpu(0);
    args->actual_cpu = sched_getcpu();
    for (size_t line = 1; line < BYTES / LINE; ++line)
        args->object[line * LINE / sizeof(uint64_t)] =
            expected(args->generation, line);
    /* This is deliberately the last WB store and the first reader load. */
    args->object[0] = expected(args->generation, 0);
    return nullptr;
}

static inline void set_streaming(void *addr, uint64_t size)
{
#ifdef GEM5_FS
    if (mprotect(addr, size, PROT_READ | PROT_STREAMING) != 0) {
        fprintf(stderr, "mprotect(PROT_STREAMING): %s\n", strerror(errno));
        exit(2);
    }
#else
    uint64_t m5_rax;
    __asm__ volatile(".byte 0x0f, 0x04, 0x55, 0x00"
                     : "=a"(m5_rax) : "D"(addr), "S"(size) : "memory");
    (void)m5_rax;
#endif
}

static inline void retire_streaming(void *addr, uint64_t size)
{
#ifdef GEM5_FS
    if (mprotect(addr, size, PROT_READ | PROT_WRITE) != 0) {
        fprintf(stderr, "mprotect(WB): %s\n", strerror(errno));
        exit(2);
    }
#else
    (void)addr;
    (void)size;
#endif
}

static inline void reset_stats(void)
{
    uint64_t m5_rax;
    __asm__ volatile(".byte 0x0f, 0x04, 0x40, 0x00"
                     : "=a"(m5_rax) : "D"(0L), "S"(0L) : "memory");
    (void)m5_rax;
}

int main()
{
    auto *object = static_cast<volatile uint64_t *>(
        mmap(nullptr, BYTES, PROT_READ | PROT_WRITE,
             MAP_PRIVATE | MAP_ANONYMOUS, -1, 0));
    if (object == MAP_FAILED) {
        perror("mmap");
        return 2;
    }

    int producer_cpu = -1;
    int reader_cpu = -1;
    uint64_t checksum = 0;
#ifdef GEM5_FS
    constexpr int generations = 2;
#else
    constexpr int generations = 1;
#endif

    for (int generation = 1; generation <= generations; ++generation) {
        ProducerArgs args{object, static_cast<uint64_t>(generation), -1};
        pthread_t thread;
        if (pthread_create(&thread, nullptr, produce, &args) != 0 ||
            pthread_join(thread, nullptr) != 0) {
            fprintf(stderr, "producer thread failed\n");
            return 2;
        }

        producer_cpu = args.actual_cpu;
        /* No CLWB, CLFLUSH, SFENCE, WBINVD, or cache-thrashing step here. */
        set_streaming(const_cast<uint64_t *>(object), BYTES);
        pin_cpu(1);
        reader_cpu = sched_getcpu();
        if (generation == 1)
            reset_stats();

        for (size_t line = 0; line < BYTES / LINE; ++line) {
            uint64_t value = object[line * LINE / sizeof(uint64_t)];
            if (value != expected(generation, line)) {
                fprintf(stderr,
                        "H3_DIRTY_OWNER_FAIL generation=%d line=%zu "
                        "got=%#llx expected=%#llx\n",
                        generation, line,
                        static_cast<unsigned long long>(value),
                        static_cast<unsigned long long>(
                            expected(generation, line)));
                return 1;
            }
            checksum ^= value;
        }

        if (generation != generations)
            retire_streaming(const_cast<uint64_t *>(object), BYTES);
    }

    printf("H3_DIRTY_OWNER_%s bytes=%lu lines=%lu generations=%d "
           "checksum=%#llx producer_cpu=%d reader_cpu=%d explicit_clean=0\n",
#ifdef GEM5_FS
           producer_cpu != reader_cpu ? "PASS" : "FAIL_SAME_CPU",
#else
           "SINGLE_CORE_SMOKE",
#endif
           BYTES, BYTES / LINE, generations,
           static_cast<unsigned long long>(checksum),
           producer_cpu, reader_cpu);
#ifdef GEM5_FS
    if (producer_cpu == reader_cpu)
        return 1;
#endif
    return 0;
}
