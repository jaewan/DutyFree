/* A5.2: give the DuckDB victim a hugepage-backed build arena, without
 * touching the frozen host's THP setting.
 *
 * moscxl runs transparent_hugepage=madvise with defrag=madvise, so a region
 * marked MADV_HUGEPAGE is backed by 2 MiB pages and the kernel will compact
 * synchronously to find them. That is exactly the manipulation A5.2 declares
 * and it is scoped to one process: LD_PRELOAD is set on the victim's
 * subprocess only, never on the aggressor, so the streamer's page placement is
 * held fixed across the comparison.
 *
 * MADV_POPULATE_WRITE pre-faults, which is the "pre-faulted" half of A5.2's
 * wording, and it is capped: DuckDB reserves address space far larger than it
 * touches, and populating a multi-gigabyte reservation would change the
 * workload rather than its page backing. Above the cap the region still gets
 * MADV_HUGEPAGE and is simply faulted in on demand, as huge pages, when used.
 *
 * The exit hook reports what was actually obtained. A diagnostic that silently
 * failed to get hugepages would look identical to a null result, which is the
 * one failure mode that would make A5.2 lie.
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>

#ifndef MADV_POPULATE_WRITE
#define MADV_POPULATE_WRITE 23
#endif

#define MIN_BYTES  (2UL << 20)     /* below one huge page, nothing to gain */
#define POP_CAP    (512UL << 20)   /* pre-fault only up to here */

static void *(*real_mmap)(void *, size_t, int, int, int, off_t);
static unsigned long n_marked, n_populated, bytes_marked;

void *mmap(void *addr, size_t len, int prot, int flags, int fd, off_t off) {
    if (!real_mmap) real_mmap = dlsym(RTLD_NEXT, "mmap");
    void *p = real_mmap(addr, len, prot, flags, fd, off);
    if (p != MAP_FAILED && (flags & MAP_ANONYMOUS) && len >= MIN_BYTES
        && (prot & PROT_WRITE)) {
        if (madvise(p, len, MADV_HUGEPAGE) == 0) { n_marked++; bytes_marked += len; }
        if (len <= POP_CAP && madvise(p, len, MADV_POPULATE_WRITE) == 0) n_populated++;
    }
    return p;
}

__attribute__((destructor)) static void report(void) {
    const char *path = getenv("STREAMING_THP_LOG");
    if (!path) return;
    unsigned long anon_huge_kb = 0;
    FILE *f = fopen("/proc/self/smaps_rollup", "r");
    if (f) {
        char line[256];
        while (fgets(line, sizeof line, f))
            if (!strncmp(line, "AnonHugePages:", 14)) {
                sscanf(line + 14, "%lu", &anon_huge_kb);
                break;
            }
        fclose(f);
    }
    FILE *o = fopen(path, "a");
    if (!o) return;
    fprintf(o, "pid=%d marked=%lu populated=%lu marked_mib=%lu anonhuge_kb=%lu\n",
            getpid(), n_marked, n_populated, bytes_marked >> 20, anon_huge_kb);
    fclose(o);
}
