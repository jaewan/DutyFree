#include <algorithm>
#include <atomic>
#include <cerrno>
#include <chrono>
#include <climits>
#include <cmath>
#include <condition_variable>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <deque>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <mutex>
#include <new>
#include <numeric>
#include <sstream>
#include <string>
#include <thread>
#include <vector>

#include <fcntl.h>
#include <pthread.h>
#include <sched.h>
#include <sys/mman.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>
#include <x86intrin.h>

#ifndef MADV_HUGEPAGE
#define MADV_HUGEPAGE 14
#endif
#ifndef MAP_HUGE_SHIFT
#define MAP_HUGE_SHIFT 26
#endif
#ifndef MAP_HUGE_2MB
#define MAP_HUGE_2MB (21 << MAP_HUGE_SHIFT)
#endif
#ifndef MPOL_BIND
#define MPOL_BIND 2
#endif
#ifndef MPOL_MF_MOVE
#define MPOL_MF_MOVE (1 << 1)
#endif

namespace {

struct Fact {
  int64_t fk;
  int64_t measure;
};

struct Entry {
  int64_t key;
  int64_t payload;
};

struct Result {
  uint64_t matches = 0;
  int64_t sum = 0;
};

struct Config {
  std::string mode = "single";
  std::string policy = "wb";
  std::string self_test;
  uint64_t fact_bytes = 256ull << 20;
  uint64_t hot_bytes = 2ull << 20;
  int fact_node = 2;
  int hot_node = 0;
  int threads = 1;
  int reps = 5;
  int warmups = 1;
  int vector = 1024;
  int pf_distance = 0;
  int stream_count = 4;
  uint64_t seed = 0xC001C0FFEE123456ull;
  double hit_rate = 0.5;
  uint64_t morsel = 1ull << 20;
  std::string cpu_list = "0";
  bool json = false;
  bool check = false;
  bool huge2m = false;
  int scan_threads = 0;
  int probe_threads = 0;
  uint64_t queue_depth = 4;
  bool result_hash = false;
  bool scan_memcpy = false;
  bool no_stream = false;
  size_t flush_distance = 0;
  bool line_stride = false;   // bytes; 0 = off (default, join_range unchanged)
  double pre_measure_sleep_s = 0.0;
  // W7 Knob B (W7_PREREGISTRATION_2026-08-23.md section 2). 0 = off, and off is
  // bit-for-bit the pre-W7 code path: join_range is not touched and the batched
  // variant is not called. k > 1 software-pipelines the probe so k independent
  // hash-table loads are in flight at once.
  int probe_batch = 0;
  uint64_t iterations = 4ull << 20;  // fs-e2e-calibrate victim dereferences
  // fs-e2e-join victim chase footprint.  Distinct from --hot-bytes, which
  // that mode gives to the tenant's hash table exactly as --mode single does.
  uint64_t victim_bytes = 0;
  // Stats-section bracketing around run_stream()'s measured loop, specified in
  // AGGBW_WINDOW_PREREG_2026-09-03.md section 1.  Default OFF, and off is
  // bit-for-bit the unbracketed code path, so a binary built from this source
  // reproduces the runs that predate the option.
  bool window_brackets = false;
};

static inline uint64_t rdtsc() {
  unsigned aux = 0;
  return __rdtscp(&aux);
}

struct SplitMix64 {
  uint64_t x;
  explicit SplitMix64(uint64_t seed) : x(seed) {}
  uint64_t next() {
    uint64_t z = (x += 0x9e3779b97f4a7c15ull);
    z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ull;
    z = (z ^ (z >> 27)) * 0x94d049bb133111ebull;
    return z ^ (z >> 31);
  }
};

static inline uint64_t hash64(uint64_t x) {
  x ^= x >> 33;
  x *= 0xff51afd7ed558ccdULL;
  x ^= x >> 33;
  x *= 0xc4ceb9fe1a85ec53ULL;
  x ^= x >> 33;
  return x;
}

uint64_t feistel_permute(uint64_t x, int bits, uint64_t seed) {
  if (bits <= 1 || (bits & 1)) {
    uint64_t mask = bits == 64 ? ~0ull : ((1ull << bits) - 1);
    return (x * 0x9e3779b97f4a7c15ull + seed) & mask;
  }
  int half = bits / 2;
  uint64_t mask = (1ull << half) - 1;
  uint64_t l = x & mask;
  uint64_t r = (x >> half) & mask;
  for (int round = 0; round < 6; ++round) {
    uint64_t f = hash64(r + seed + 0x9e3779b97f4a7c15ull * static_cast<uint64_t>(round)) & mask;
    uint64_t nl = r;
    uint64_t nr = l ^ f;
    l = nl;
    r = nr;
  }
  return ((r & mask) << half) | (l & mask);
}

uint64_t parse_size(const std::string &s) {
  if (s.empty()) return 0;
  char *end = nullptr;
  double v = std::strtod(s.c_str(), &end);
  std::string u(end ? end : "");
  for (auto &c : u) c = static_cast<char>(std::tolower(c));
  double m = 1.0;
  if (u == "k" || u == "kb" || u == "kib") m = 1024.0;
  else if (u == "m" || u == "mb" || u == "mib") m = 1024.0 * 1024.0;
  else if (u == "g" || u == "gb" || u == "gib") m = 1024.0 * 1024.0 * 1024.0;
  return static_cast<uint64_t>(v * m);
}

std::vector<int> parse_cpus(const std::string &s) {
  std::vector<int> out;
  std::stringstream ss(s);
  std::string tok;
  while (std::getline(ss, tok, ',')) {
    auto dash = tok.find('-');
    if (dash == std::string::npos) {
      if (!tok.empty()) out.push_back(std::stoi(tok));
    } else {
      int a = std::stoi(tok.substr(0, dash));
      int b = std::stoi(tok.substr(dash + 1));
      for (int i = a; i <= b; ++i) out.push_back(i);
    }
  }
  if (out.empty()) out.push_back(0);
  return out;
}

void pin_cpu(int cpu) {
#if defined(GEM5) && !defined(GEM5_FS)
  (void)cpu;
#else
  cpu_set_t set;
  CPU_ZERO(&set);
  CPU_SET(cpu, &set);
  if (pthread_setaffinity_np(pthread_self(), sizeof(set), &set) != 0) {
    std::perror("pthread_setaffinity_np");
    std::exit(2);
  }
#endif
}

#ifdef GEM5
// H2: mark [addr,addr+size) STREAMING (M5OP_SET_STREAMING=0x55) so the CHI
// HNF bypasses the LLC data array for these clean read-only lines.
// The "memory" clobber is load-bearing, not decoration: both ops are ordered
// against the caller's accesses to [addr,addr+size) (set_streaming re-marks
// PTEs and flushes TLBs; bind_pool must land before first touch). Without it
// the compiler may sink a store below, or hoist one above, the op.
static inline void gem5_set_streaming(void *addr, long size) {
    uint64_t m5_rax;
    __asm__ volatile(".byte 0x0f, 0x04, 0x55, 0x00"
                     : "=a"(m5_rax) : "D"(addr), "S"(size) : "memory");
    (void)m5_rax;
}
static inline void gem5_reset_stats_now() {
    uint64_t m5_rax;
    __asm__ volatile(".byte 0x0f, 0x04, 0x40, 0x00"
                     : "=a"(m5_rax) : "D"(0L), "S"(0L) : "memory");
    (void)m5_rax;
}
// M5OP_DUMP_STATS=0x41.  Needed so the ROI has an exact closing boundary: the
// rcS `m5 dumpstats` fires only after the process has printed its JSON and
// exited, and gem5's own exit dump is cumulative on top of that.  Measuring
// either of those attributes post-ROI teardown to the ROI.
static inline void gem5_dump_stats_now() {
    uint64_t m5_rax;
    __asm__ volatile(".byte 0x0f, 0x04, 0x41, 0x00"
                     : "=a"(m5_rax) : "D"(0L), "S"(0L) : "memory");
    (void)m5_rax;
}
// M5OP_EXIT=0x21.  Ends the simulation at the tenant's JSON, so a complete
// join (--reps 1) owns the measured window instead of waiting for the victim's
// m5_exit.  Truncated campaigns (--reps 100) never reach this call.
static inline void gem5_exit_now() {
    uint64_t m5_rax;
    __asm__ volatile(".byte 0x0f, 0x04, 0x21, 0x00"
                     : "=a"(m5_rax) : "D"(0ULL) : "memory");
    (void)m5_rax;
}
// SE mode has no working NUMA syscalls -- mbind is registered ignoreFunc
// (src/arch/x86/linux/syscall_tbl64.cc), a silent no-op, which is why
// alloc_bytes's GEM5 branch used to skip placement entirely (task #22).
// bindpool (M5OP_BIND_POOL=0x56, pseudo_inst.cc) is SE mode's real
// placement primitive: it backs a not-yet-touched VA range from a named
// pool (0=DRAM, 1=CXL, process.hh:301). Must be called before first
// touch -- SE cannot migrate an already-backed page.
static inline void gem5_bind_pool(void *addr, uint64_t size, uint64_t pool) {
    uint64_t m5_rax;
    __asm__ volatile(".byte 0x0f, 0x04, 0x56, 0x00"
                     : "=a"(m5_rax) : "D"(addr), "S"(size), "d"(pool) : "memory");
    (void)m5_rax;
}
// FLUSH-BEHIND ORACLE (M5OP_FLUSH_RANGE=0x57).  Functionally invalidates
// [addr,addr+size) in the shared LLC slices at zero latency and zero fabric
// traffic.  Used only by --policy fbo, which prices flush-behind's BEST case
// against an admission policy: gem5's CHI has no handler for a real CLFLUSH,
// so clflushopt is a silent no-op here, and on silicon the converse holds.
// An UPPER BOUND on flush-behind, not a model of it.
static inline void gem5_flush_range(void *addr, uint64_t size) {
    uint64_t m5_rax;
    __asm__ volatile(".byte 0x0f, 0x04, 0x57, 0x00"
                     : "=a"(m5_rax) : "D"(addr), "S"(size) : "memory");
    (void)m5_rax;
}
#else
static inline void gem5_set_streaming(void *, long) {}
static inline void gem5_reset_stats_now() {}
static inline void gem5_dump_stats_now() {}
static inline void gem5_exit_now() {}
static inline void gem5_flush_range(void *, uint64_t) {}
#endif

// W8: how the Streaming declaration reaches the simulator.
//
// Every gem5 STREAMING number this project owns arrived through the m5op
// above -- a backdoor the OS knows nothing about. It validates H2/H3 and says
// nothing about I0/I1. `--declare mprotect` routes the same declaration
// through the guest kernel instead: mprotect(PROT_READ | PROT_STREAMING)
// rewrites the PTEs to PAT slot 6, and gem5's page-table walker reads the
// declaration off the ordinary translation. That path only exists under a
// kernel built with CONFIG_PAT_STREAMING=y, which is why it is a flag and not
// the default.
//
// PROT_STREAMING is 0x10, from the custom kernel's
// include/uapi/asm-generic/mman-common.h:14. A kernel without the feature
// returns EINVAL for the unknown bit, so a silent no-op is not possible --
// but only because the return value is checked below. It is checked below.
#ifndef PROT_STREAMING
#define PROT_STREAMING 0x10
#endif
enum class DeclareVia { M5OP, MPROTECT };
static DeclareVia g_declare = DeclareVia::M5OP;

// Sample counts from the last declare_streaming(), surfaced in JSON so the
// analyser can require a minimum, and so "verified" is never read as "uniform".
static unsigned g_pte_samples = 0;
static unsigned g_pte_passed = 0;

// W8 gate: read the installed PTE back out of the kernel.
//
// This is the artifact the whole full-system task exists to produce. mprotect
// returning 0 means the kernel accepted the request; it does not mean the PTE
// carries the Streaming encoding. mm/streaming.c exposes
// /sys/kernel/debug/streaming/pte_query for exactly this, and it resolves the
// address in `current->mm` -- so the querying process must be the one that
// owns the mapping. That is why this lives in the benchmark and not in the
// .rcS.
//
// Slot number is read off the same three bits the gem5 walker reads
// (pagetable_walker.cc:360-390): PAT<<2 | PCD<<1 | PWT, where PAT is bit 7 of a
// 4K PTE and bit 12 of a 2M leaf. Streaming is slot 6 -- PAT=1, PCD=1, PWT=0.
static bool streaming_pte_readback(uintptr_t vaddr) {
  const char *dir = "/sys/kernel/debug/streaming/pte_query";
  char buf[32];
  std::snprintf(buf, sizeof(buf), "%lx", (unsigned long)vaddr);
  FILE *w = std::fopen(dir, "r+");
  if (!w) {
    std::cerr << "DECLARE_PTE_READBACK unavailable: cannot open " << dir << ": "
              << std::strerror(errno) << " (debugfs not mounted, or a kernel without "
                 "CONFIG_PAT_STREAMING) -- the declaration is UNVERIFIED\n";
    return false;
  }
  if (std::fwrite(buf, 1, std::strlen(buf), w) != std::strlen(buf)) {
    std::cerr << "DECLARE_PTE_READBACK failed on write: " << std::strerror(errno)
              << " -- the declaration is UNVERIFIED\n";
    std::fclose(w);
    return false;
  }
  std::fflush(w);
  std::rewind(w);
  char line[128] = {0};
  if (!std::fgets(line, sizeof(line), w)) {
    std::cerr << "DECLARE_PTE_READBACK failed on read -- UNVERIFIED\n";
    std::fclose(w);
    return false;
  }
  std::fclose(w);
  unsigned long qv = 0, pteval = 0;
  unsigned lvl = 0;
  if (std::sscanf(line, "%lx %lx %u", &qv, &pteval, &lvl) != 3) {
    std::cerr << "DECLARE_PTE_READBACK unparsed: " << line << " -- UNVERIFIED\n";
    return false;
  }
  unsigned pwt = (pteval >> 3) & 1u;
  unsigned pcd = (pteval >> 4) & 1u;
  unsigned pat = (lvl >= 21) ? ((pteval >> 12) & 1u) : ((pteval >> 7) & 1u);
  unsigned slot = (pat << 2) | (pcd << 1) | pwt;
  const bool pass = slot == 6;
  std::cerr << "DECLARE_PTE_READBACK vaddr=0x" << std::hex << qv
            << " pte=0x" << pteval << std::dec
            << " level_shift=" << lvl
            << " PAT=" << pat << " PCD=" << pcd << " PWT=" << pwt
            << " pat_slot=" << slot
            << (pass ? "  GATE=PASS(slot6=Streaming)" : "  GATE=FAIL(expected slot 6)")
            << "\n";
  return pass;
}

static void declare_streaming(void *addr, uint64_t bytes) {
  if (g_declare == DeclareVia::M5OP) { gem5_set_streaming(addr, (long)bytes); return; }
  // Page-align outward: mprotect refuses an unaligned base, and declaring a
  // partial page would leave part of the object unlabelled -- an
  // object-scoped contract that covers most of the object is not the claim.
  const uintptr_t pg = 4096;
  uintptr_t base = reinterpret_cast<uintptr_t>(addr) & ~(pg - 1);
  uintptr_t end = (reinterpret_cast<uintptr_t>(addr) + bytes + pg - 1) & ~(pg - 1);
  if (mprotect(reinterpret_cast<void *>(base), (size_t)(end - base),
               PROT_READ | PROT_STREAMING) != 0) {
    std::cerr << "FATAL: mprotect(PROT_READ|PROT_STREAMING) failed: " << std::strerror(errno)
              << " -- base=0x" << std::hex << base << " len=0x" << (end - base) << std::dec
              << ". A kernel without CONFIG_PAT_STREAMING returns EINVAL here; "
                 "an ignored failure would produce a null that looks like a real result.\n";
    std::exit(12);
  }
  std::cerr << "DECLARE_STREAMING via=mprotect base=0x" << std::hex << base
            << " len=0x" << (end - base) << std::dec << " rc=0\n";
  // A successful syscall is not sufficient evidence: prove that representative
  // pages at both ends (and the middle for multi-page objects) carry the exact
  // slot gem5's walker consumes.  This is deliberately fail-closed; allowing
  // an unverified OS declaration would turn a null result into an H2 result.
  // Sample every 2 MiB boundary, not only the ends: a THP split leaving an
  // interior hole is the realistic failure mode for a prototype, and three
  // points out of thousands of PTEs cannot see it.  The count is reported so the
  // analyser gates on evidence rather than one PASS substring, and so nobody
  // reads "verified" as "uniform" (I0) when it means "N samples passed".
  const uintptr_t last = end - pg;
  unsigned samples = 0, passed = 0;
  const uintptr_t step = (2ull << 20) > pg ? (uintptr_t)(2ull << 20) : pg;
  for (uintptr_t a = base; a <= last; a += step) {
    ++samples;
    if (streaming_pte_readback(a)) ++passed;
  }
  if (((last - base) % step) != 0) {          // always include the final page
    ++samples;
    if (streaming_pte_readback(last)) ++passed;
  }
  g_pte_samples = samples;
  g_pte_passed = passed;
  std::cerr << "DECLARE_PTE_SAMPLES total=" << samples << " passed=" << passed << "\n";
  if (samples == 0 || passed != samples) {
    std::cerr << "FATAL: STREAMING declaration did not install verified slot-6 PTEs ("
              << passed << "/" << samples << " samples)\n";
    std::exit(13);
  }
}

void *alloc_bytes(uint64_t bytes, int node, bool huge2m, const char *name) {
  void *p = nullptr;
#if defined(GEM5) && !defined(GEM5_FS)
  (void)huge2m;
  int flags = MAP_PRIVATE | MAP_ANONYMOUS;
  p = mmap(nullptr, bytes, PROT_READ | PROT_WRITE, flags, -1, 0);
  if (p == MAP_FAILED) {
    p = nullptr;
  } else {
    // node 0 -> DRAM pool 0; any other requested node (this bench's own
    // default is fact_node=2 for "the CXL one") -> CXL pool 1. Call before
    // any write touches these pages (task #22 fix: this branch used to
    // silently skip placement entirely).
    uint64_t pool = (node == 0) ? 0 : 1;
    gem5_bind_pool(p, bytes, pool);
    // Emitted unconditionally, and deliberately not behind getenv: gem5 SE
    // gives the guest only what --env supplies and never inherits the host
    // environment (se.py:101), so an env-gated diagnostic can never fire in
    // the one build where it is compiled. check_pages_on_node() is still a
    // `return true` stub under GEM5, so this line plus the per-controller
    // bytesRead in stats.txt is the only in-band placement evidence a run
    // leaves behind.
    std::cerr << "BIND_POOL " << name << " addr=0x" << std::hex
              << reinterpret_cast<uintptr_t>(p) << std::dec
              << " bytes=" << bytes << " node=" << node
              << " pool=" << pool << "\n";
  }
#else
  int flags = MAP_PRIVATE | MAP_ANONYMOUS;
  if (huge2m) {
    p = mmap(nullptr, bytes, PROT_READ | PROT_WRITE, flags | MAP_HUGETLB | MAP_HUGE_2MB, -1, 0);
    if (p == MAP_FAILED) p = nullptr;
  }
  if (!p) {
    p = mmap(nullptr, bytes, PROT_READ | PROT_WRITE, flags, -1, 0);
    if (p == MAP_FAILED) p = nullptr;
    else if (huge2m) madvise(p, bytes, MADV_HUGEPAGE);
  }
  if (!p) {
    std::cerr << "allocation failed for " << name << " bytes=" << bytes
              << " node=" << node << "\n";
    std::exit(2);
  }
  unsigned long mask = 1ul << node;
  long rc = syscall(__NR_mbind, p, bytes, MPOL_BIND, &mask, sizeof(mask) * CHAR_BIT, 0);
  if (rc != 0) {
    std::cerr << "mbind failed for " << name << " node=" << node << ": "
              << std::strerror(errno) << "\n";
    munmap(p, bytes);
    std::exit(2);
  }
#endif
  return p;
}

void free_bytes(void *p, uint64_t bytes, bool huge2m) {
#if defined(GEM5) && !defined(GEM5_FS)
  munmap(p, bytes);
#else
  (void)huge2m;
  munmap(p, bytes);
#endif
}

bool check_pages_on_node(void *p, uint64_t bytes, int node, std::string *detail) {
#if defined(GEM5) && !defined(GEM5_FS)
  (void)p; (void)bytes; (void)node;
  if (detail) *detail = "gem5 SE no NUMA placement check";
  return true;
#else
  size_t pages = std::min<uint64_t>((bytes + 4095) / 4096, 4096);
  if (pages == 0) return true;
  std::vector<void *> addrs(pages);
  std::vector<int> status(pages, -1);
  uintptr_t base = reinterpret_cast<uintptr_t>(p);
  uint64_t stride = std::max<uint64_t>(4096, bytes / pages);
  for (size_t i = 0; i < pages; ++i) addrs[i] = reinterpret_cast<void *>(base + i * stride);
  long rc = syscall(__NR_move_pages, 0, static_cast<unsigned long>(pages), addrs.data(), nullptr,
                    status.data(), 0);
  if (rc != 0) {
    if (detail) *detail = std::string("move_pages failed: ") + std::strerror(errno);
    return false;
  }
  std::map<int, int> counts;
  for (int s : status) counts[s]++;
  std::ostringstream os;
  os << "sampled_pages=" << pages;
  for (auto &kv : counts) os << " node" << kv.first << "=" << kv.second;
  if (detail) *detail = os.str();
  return counts.size() == 1 && counts.begin()->first == node;
#endif
}

// FAULT-IN ONLY, and valid ONLY on a region nothing has written yet.
//
// This MUTATES, and it has to: a pure read of fresh anonymous memory resolves to
// the shared zero page and faults nothing in, so the touch must be a write.  That
// makes a call placed after the buffer is populated silently destructive -- it
// increments one byte per 4 KiB page, plus the last byte of the region.
//
// It has cost this project two campaigns.  In r6d it pushed next[0] off its line
// alignment and the victim chased two cache lines instead of 98,304.  On silicon
// it corrupted exactly one fact key per page -- 262,144 of 67,108,864 tuples at a
// 1 GiB fact -- and every cross-arm equality check still passed, because the
// damage is identical in every arm.  Both survived review as plausible numbers.
//
// So the precondition is now checked rather than documented.  Reading the first
// byte of a page maps the shared zero page and does not fault the page in, so the
// guard costs a cheap read pass and does not defeat the prefault it protects.
void prefault_region(void *p, uint64_t bytes, const char *what = "region") {
  const volatile char *chk = static_cast<const volatile char *>(p);
  uint64_t bad = UINT64_MAX;
  for (uint64_t off = 0; off < bytes; off += 4096) {
    if (chk[off] != 0) { bad = off; break; }
  }
  if (bad == UINT64_MAX && bytes && chk[bytes - 1] != 0) bad = bytes - 1;
  if (bad != UINT64_MAX) {
    std::cerr << "FATAL: prefault_region(" << what << ", " << bytes << ") called on"
              << " memory that has already been written (nonzero byte at +" << bad
              << ").  This function mutates: it must run BEFORE the region is"
              << " populated, never after.\n";
    std::exit(14);
  }
  volatile char *q = static_cast<volatile char *>(p);
  for (uint64_t off = 0; off < bytes; off += 4096) {
    q[off] = static_cast<char>(q[off] + 1);
  }
  if (bytes) q[bytes - 1] = static_cast<char>(q[bytes - 1] + 1);
}

struct SmapsInfo {
  uint64_t anon_huge_kb = 0;
  uint64_t kernel_page_kb = 0;
  uint64_t mmu_page_kb = 0;
};

SmapsInfo smaps_info(void *p) {
  SmapsInfo info;
#ifdef GEM5
  (void)p;
#else
  std::ifstream in("/proc/self/smaps");
  std::string line;
  uintptr_t target = reinterpret_cast<uintptr_t>(p);
  bool in_range = false;
  while (std::getline(in, line)) {
    uintptr_t lo = 0, hi = 0;
    if (std::sscanf(line.c_str(), "%lx-%lx", &lo, &hi) == 2) {
      if (in_range) return info;
      in_range = target >= lo && target < hi;
      continue;
    }
    if (!in_range) continue;
    std::sscanf(line.c_str(), "AnonHugePages: %lu kB", &info.anon_huge_kb);
    std::sscanf(line.c_str(), "KernelPageSize: %lu kB", &info.kernel_page_kb);
    std::sscanf(line.c_str(), "MMUPageSize: %lu kB", &info.mmu_page_kb);
  }
#endif
  return info;
}

std::string cpu_mapping_json(const std::vector<int> &cpus, int n,
                             const std::vector<std::string> &roles = {}) {
  std::ostringstream os;
  os << "[";
  for (int i = 0; i < n; ++i) {
    if (i) os << ",";
    int cpu = cpus[i % cpus.size()];
    os << "{\"thread\":" << i << ",\"cpu\":" << cpu;
#ifndef GEM5
    std::ifstream f("/sys/devices/system/cpu/cpu" + std::to_string(cpu) + "/topology/core_id");
    int core = -1;
    f >> core;
    os << ",\"physical_core\":" << core;
#endif
    if (static_cast<size_t>(i) < roles.size()) {
      os << ",\"role\":\"" << roles[i] << "\"";
    }
    os << "}";
  }
  os << "]";
  return os.str();
}

size_t table_capacity(uint64_t hot_bytes) {
  size_t cap = std::max<size_t>(1024, hot_bytes / sizeof(Entry));
  size_t pow2 = 1;
  while (pow2 < cap) pow2 <<= 1;
  // probe() masks rather than divides, so the table must be a power of two --
  // which means --hot-bytes is quantized, silently, by up to 2x. That is how
  // a run requesting 10 MiB was recorded as 10 MiB while instantiating 16 MiB
  // (task #22 follow-up). The requested size is a claim; this is the fact, so
  // say so on stderr whenever the two differ.
  uint64_t actual = static_cast<uint64_t>(pow2) * sizeof(Entry);
  if (actual != hot_bytes) {
    std::cerr << "HOT_TABLE_ROUNDED requested_bytes=" << hot_bytes
              << " instantiated_bytes=" << actual
              << " entries=" << pow2
              << " ratio=" << (static_cast<double>(actual) / hot_bytes)
              << "  (--hot-bytes must be a power of two times "
              << sizeof(Entry) << " to be honoured exactly)\n";
  }
  return pow2;
}

void build_table(std::vector<Entry> &table, std::vector<int64_t> &keys, uint64_t hot_bytes, uint64_t seed) {
  size_t cap = table_capacity(hot_bytes);
  table.assign(cap, Entry{0, 0});
  size_t nkeys = std::max<size_t>(1, cap / 2);
  keys.resize(nkeys);
  SplitMix64 rng(seed);
  for (size_t i = 0; i < nkeys; ++i) {
    int64_t key = static_cast<int64_t>((rng.next() | 1ull) & 0x7fffffffffffffffll);
    keys[i] = key;
    size_t pos = hash64(static_cast<uint64_t>(key)) & (cap - 1);
    while (table[pos].key != 0) pos = (pos + 1) & (cap - 1);
    table[pos].key = key;
    table[pos].payload = static_cast<int64_t>(i + 1);
  }
}

void fill_fact(Fact *fact, size_t n, const std::vector<int64_t> &keys, double hit_rate, uint64_t seed) {
  SplitMix64 rng(seed ^ 0xBAD5EED1234ull);
  // (double)UINT64_MAX rounds up to exactly 2^64, so at hit_rate 1.0 this product
  // is not representable as uint64_t and the conversion is undefined.  With
  // -march=native the AVX-512 vcvttsd2usi saturates to UINT64_MAX and the arm is
  // correct; the plain-SSE2 build used for every gem5 binary wraps to 0, which
  // turns a 100%-hit request into a 0%-hit arm with nothing in the JSON to say so.
  // Saturate explicitly so the two builds cannot disagree.
  const double hr = hit_rate < 0.0 ? 0.0 : (hit_rate > 1.0 ? 1.0 : hit_rate);
  const uint64_t threshold = (hr >= 1.0) ? UINT64_MAX
                                         : static_cast<uint64_t>(hr * 18446744073709549568.0);
  for (size_t i = 0; i < n; ++i) {
    uint64_t r = rng.next();
    if (r <= threshold) {
      fact[i].fk = keys[rng.next() % keys.size()];
    } else {
      fact[i].fk = -static_cast<int64_t>((rng.next() & 0x7fffffffffffffffll) | 2ull);
    }
    fact[i].measure = static_cast<int64_t>((rng.next() % 101) - 50);
  }
}

static inline bool probe(const std::vector<Entry> &table, int64_t key, int64_t *payload) {
  size_t mask = table.size() - 1;
  size_t pos = hash64(static_cast<uint64_t>(key)) & mask;
  while (true) {
    const Entry &e = table[pos];
    if (e.key == 0) return false;
    if (e.key == key) {
      *payload = e.payload;
      return true;
    }
    pos = (pos + 1) & mask;
  }
}

Result scalar_join(const std::vector<Entry> &table, const Fact *fact, size_t n) {
  Result r;
  for (size_t i = 0; i < n; ++i) {
    int64_t payload = 0;
    if (probe(table, fact[i].fk, &payload)) {
      (void)payload;
      r.matches++;
      r.sum += fact[i].measure;
    }
  }
  return r;
}

Result join_range(const std::vector<Entry> &table, const Fact *fact, size_t begin, size_t end,
                  const std::string &policy, int pf_distance) {
  Result r;
  int pfd = std::max(0, pf_distance);
  for (size_t i = begin; i < end; ++i) {
    if (policy == "nta" && i + static_cast<size_t>(pfd) < end) {
      _mm_prefetch(reinterpret_cast<const char *>(&fact[i + pfd]), _MM_HINT_NTA);
    }
    int64_t payload = 0;
    if (probe(table, fact[i].fk, &payload)) {
      (void)payload;
      r.matches++;
      r.sum += fact[i].measure;
    }
  }
  return r;
}

// H2 silicon proxy for the FUSED kernel. Identical to join_range except it issues
// clflushopt on fact lines more than flush_distance bytes behind the read pointer,
// bounding the stream's cache residency to ~flush_distance while still READING
// every byte. That is the distinction M2 could not make: --no-stream removes the
// bytes, this removes only the retention. Mirrors
// benchmarks/bench/aggressor/stream_wb_flushbehind.c (same distance convention,
// same sfence batching). flush_distance == 0 never reaches here; join_range is
// untouched and remains the default path.
Result join_range_flushbehind(const std::vector<Entry> &table, const Fact *fact,
                              size_t begin, size_t end, const std::string &policy,
                              int pf_distance, size_t flush_distance) {
  Result r;
  int pfd = std::max(0, pf_distance);
  const size_t ents_per_line = 64 / sizeof(Fact);          // 4
  const size_t flush_ents = std::max<size_t>(ents_per_line, flush_distance / sizeof(Fact));
  int batch = 0;
  for (size_t i = begin; i < end; ++i) {
    if (policy == "nta" && i + static_cast<size_t>(pfd) < end) {
      _mm_prefetch(reinterpret_cast<const char *>(&fact[i + pfd]), _MM_HINT_NTA);
    }
    int64_t payload = 0;
    if (probe(table, fact[i].fk, &payload)) {
      (void)payload;
      r.matches++;
      r.sum += fact[i].measure;
    }
    if (policy == "fbo") {
      // ORACLE arm: one m5op per 4 KiB of trailing data instead of one
      // clflushopt per 64 B line, so the guest pays ~1 instruction per 64
      // lines rather than one per line -- flush-behind with its software cost
      // removed, and the invalidation itself functional and free.
      const size_t blk = 4096 / sizeof(Fact);
      if (((i + 1) % blk) == 0 && i >= begin + flush_ents + blk) {
        gem5_flush_range(const_cast<void *>(static_cast<const void *>(
                             &fact[i - flush_ents - blk + 1])), 4096);
      }
    } else if (((i + 1) % ents_per_line) == 0 && i >= begin + flush_ents) {
      // one clflushopt per line -- a silent no-op under gem5 Ruby/CHI, which
      // is exactly why the oracle above exists
      _mm_clflushopt(const_cast<void *>(static_cast<const void *>(&fact[i - flush_ents])));
      if (++batch >= 64) { _mm_sfence(); batch = 0; }
    }
  }
  _mm_sfence();
  return r;
}

// Order-independent correctness diagnostic. Identical to join_range except it also
// XORs a per-match hash of (key,payload) into *xhash, so fused and split runs over the
// same seed can be compared without depending on morsel processing order. Never called
// unless --result-hash is set; join_range itself is untouched.
Result join_range_hashed(const std::vector<Entry> &table, const Fact *fact, size_t begin, size_t end,
                         const std::string &policy, int pf_distance, uint64_t *xhash) {
  Result r;
  int pfd = std::max(0, pf_distance);
  uint64_t h = 0;
  for (size_t i = begin; i < end; ++i) {
    if (policy == "nta" && i + static_cast<size_t>(pfd) < end) {
      _mm_prefetch(reinterpret_cast<const char *>(&fact[i + pfd]), _MM_HINT_NTA);
    }
    int64_t payload = 0;
    if (probe(table, fact[i].fk, &payload)) {
      r.matches++;
      r.sum += fact[i].measure;
      h ^= hash64(static_cast<uint64_t>(fact[i].fk) * 0x9E3779B97F4A7C15ull ^ static_cast<uint64_t>(payload));
    }
  }
  *xhash ^= h;
  return r;
}

// Same-code-path quiescent diagnostic. Identical to join_range except it indexes a
// small, cache-resident local buffer via wraparound (fact[i % local_n]) instead of
// striding through the real (CXL) fact array. Used only by --no-stream, to isolate how
// much of "quiescent vs loaded" reflects real interference versus a code-path
// difference against run_hot_probe's separate loop. join_range itself is untouched.
Result join_range_local(const std::vector<Entry> &table, const Fact *fact, size_t local_n,
                        size_t begin, size_t end, const std::string &policy, int pf_distance) {
  Result r;
  int pfd = std::max(0, pf_distance);
  // local_n is always a power of 2 by construction (run_morsel caps it at 65536), but
  // it is a runtime value, so a compiler cannot strength-reduce `% local_n` to a shift
  // the way it can for a literal. Mask explicitly to avoid paying a full integer
  // division per tuple, which would swamp the very effect this diagnostic measures.
  size_t mask = local_n - 1;
  for (size_t i = begin; i < end; ++i) {
    size_t li = i & mask;
    if (policy == "nta" && i + static_cast<size_t>(pfd) < end) {
      _mm_prefetch(reinterpret_cast<const char *>(&fact[(i + pfd) & mask]), _MM_HINT_NTA);
    }
    int64_t payload = 0;
    if (probe(table, fact[li].fk, &payload)) {
      r.matches++;
      r.sum += fact[li].measure;
    }
  }
  return r;
}

// W7 Knob B -- batched (software-pipelined) probe. Identical results to
// join_range by construction: the only change is WHEN the hash-table lines are
// requested, not which ones or what is done with them.
//
// join_range's dependent chain per tuple is load fact[i] -> hash64 (5 dependent
// ALU ops) -> load table[pos] -> compare. GATE1_FUSED_NULL_CORRECTION_2026-08-15
// section 4 measures ~1.3 lines in flight against a 16-entry L1d TBE budget --
// 8.1% occupancy -- so an efficiency gain at the HNF has nothing to convert
// into. Here k tuples are hashed first, then their k table lines are loaded as
// k INDEPENDENT loads, and only then are the k results consumed.
//
// Real loads, not _mm_prefetch: a prefetch is a hint that a model may drop, and
// the whole point of the cell is to put a known number of lines in flight.
// Loading the Entry itself also does double duty -- the common case (first slot
// hits or is empty) is resolved without a second access.
//
// The finish loop reproduces probe() exactly, including linear-probe fallback
// from pos+1 on collision, so `matches` and `sum` are equal to join_range's for
// every input. --check compares them; that equality is the correctness gate.
Result join_range_batched(const std::vector<Entry> &table, const Fact *fact, size_t begin,
                          size_t end, const std::string &policy, int pf_distance, int k) {
  Result r;
  int pfd = std::max(0, pf_distance);
  size_t mask = table.size() - 1;
  // Stack arrays, not std::vector: the lane state must not sit behind a heap
  // pointer the compiler has to reload. KMAX is the L1d TBE budget of the
  // modelled core (16) doubled, which is past any k worth testing -- the point
  // of the knob is to fill 16 entries, not to exceed them.
  static const size_t KMAX = 32;
  const size_t K = static_cast<size_t>(std::min<int>(std::max(1, k), (int)KMAX));
  size_t pos[KMAX];
  int64_t key[KMAX];
  Entry ent[KMAX];
  size_t i = begin;
  for (; i + K <= end; i += K) {
    // Stage 1: k independent hashes. No memory dependence between lanes.
    for (size_t j = 0; j < K; ++j) {
      if (policy == "nta" && i + j + static_cast<size_t>(pfd) < end) {
        _mm_prefetch(reinterpret_cast<const char *>(&fact[i + j + pfd]), _MM_HINT_NTA);
      }
      key[j] = fact[i + j].fk;
      pos[j] = hash64(static_cast<uint64_t>(key[j])) & mask;
    }
    // Stage 2: k independent hash-table loads. This is the stage that raises
    // memory-level parallelism, and the only reason this function exists.
    for (size_t j = 0; j < K; ++j) ent[j] = table[pos[j]];
    // Stage 3: consume. Slow path only on a collision that is not resolved by
    // the line already loaded.
    for (size_t j = 0; j < K; ++j) {
      if (ent[j].key == 0) continue;
      if (ent[j].key == key[j]) {
        r.matches++;
        r.sum += fact[i + j].measure;
        continue;
      }
      size_t p = (pos[j] + 1) & mask;
      while (true) {
        const Entry &e = table[p];
        if (e.key == 0) break;
        if (e.key == key[j]) {
          r.matches++;
          r.sum += fact[i + j].measure;
          break;
        }
        p = (p + 1) & mask;
      }
    }
  }
  // Tail: fewer than K tuples remain. Serial, same as join_range.
  for (; i < end; ++i) {
    int64_t payload = 0;
    if (probe(table, fact[i].fk, &payload)) {
      (void)payload;
      r.matches++;
      r.sum += fact[i].measure;
    }
  }
  return r;
}

uint64_t stream_tuple_loop(const Fact *fact, size_t n) {
  uint64_t s0 = 0, s1 = 0, s2 = 0, s3 = 0;
  for (size_t i = 0; i < n; i += 4) {
    if (i + 0 < n) s0 += static_cast<uint64_t>(fact[i + 0].fk) + static_cast<uint64_t>(fact[i + 0].measure);
    if (i + 1 < n) s1 += static_cast<uint64_t>(fact[i + 1].fk) + static_cast<uint64_t>(fact[i + 1].measure);
    if (i + 2 < n) s2 += static_cast<uint64_t>(fact[i + 2].fk) + static_cast<uint64_t>(fact[i + 2].measure);
    if (i + 3 < n) s3 += static_cast<uint64_t>(fact[i + 3].fk) + static_cast<uint64_t>(fact[i + 3].measure);
  }
  return s0 ^ s1 ^ s2 ^ s3;
}

uint64_t hash_only_loop(const Fact *fact, size_t n) {
  uint64_t s = 0;
  for (size_t i = 0; i < n; ++i) s ^= hash64(static_cast<uint64_t>(fact[i].fk));
  return s;
}

Result probe_only_loop(const std::vector<Entry> &table, const Fact *fact, size_t n) {
  Result r;
  for (size_t i = 0; i < n; ++i) {
    int64_t payload = 0;
    if (probe(table, fact[i].fk, &payload)) {
      r.matches++;
      r.sum += payload;
    }
  }
  return r;
}

Result aggregate_only_loop(const Fact *fact, size_t n) {
  Result r;
  for (size_t i = 0; i < n; ++i) {
    if (fact[i].fk > 0) {
      r.matches++;
      r.sum += fact[i].measure;
    }
  }
  return r;
}

void warm_table(const std::vector<Entry> &table) {
  volatile uint64_t acc = 0;
  for (const auto &e : table) acc += static_cast<uint64_t>(e.key);
  if (acc == 42) std::cerr << "";
}

double seconds_since(std::chrono::steady_clock::time_point t0) {
  auto t1 = std::chrono::steady_clock::now();
  return std::chrono::duration<double>(t1 - t0).count();
}

struct ProbeTiming {
  double cycles_per_access = 0;
  uint64_t accesses = 0;
};

double median(std::vector<double> v) {
  if (v.empty()) return 0.0;
  std::sort(v.begin(), v.end());
  size_t m = v.size() / 2;
  if (v.size() & 1) return v[m];
  return 0.5 * (v[m - 1] + v[m]);
}

double cov(const std::vector<double> &v) {
  if (v.size() < 2) return 0.0;
  double mean = std::accumulate(v.begin(), v.end(), 0.0) / v.size();
  if (mean == 0.0) return 0.0;
  double ss = 0.0;
  for (double x : v) ss += (x - mean) * (x - mean);
  return std::sqrt(ss / static_cast<double>(v.size() - 1)) / mean;
}

void emit_samples(const std::vector<double> &samples) {
  std::cout << "\"samples\":[";
  for (size_t i = 0; i < samples.size(); ++i) {
    if (i) std::cout << ",";
    std::cout << std::setprecision(9) << samples[i];
  }
  std::cout << "],";
  std::cout << "\"median\":" << std::setprecision(9) << median(samples) << ",";
  std::cout << "\"cov\":" << cov(samples) << ",";
}

ProbeTiming probe_timing(const std::vector<Entry> &table, const std::vector<int64_t> &keys, size_t accesses) {
  ProbeTiming pt;
  volatile int64_t sink = 0;
  uint64_t t0 = rdtsc();
  for (size_t i = 0; i < accesses; ++i) {
    int64_t payload = 0;
    probe(table, keys[i % keys.size()], &payload);
    sink += payload;
  }
  uint64_t t1 = rdtsc();
  if (sink == 7) std::cerr << "";
  pt.accesses = accesses;
  pt.cycles_per_access = accesses ? static_cast<double>(t1 - t0) / accesses : 0.0;
  return pt;
}

static inline void policy_prefetch(const char *p, const std::string &policy) {
  if (policy == "nta") _mm_prefetch(p, _MM_HINT_NTA);
  else if (policy == "t0") _mm_prefetch(p, _MM_HINT_T0);
}

uint64_t stream_read(Fact *fact, size_t n, const std::string &policy, int pf_distance, int stream_count) {
#ifdef __AVX2__
  const char *base = reinterpret_cast<const char *>(fact);
  size_t bytes = n * sizeof(Fact);
  size_t vecs = bytes / 32;
  __m256i a0 = _mm256_setzero_si256();
  __m256i a1 = _mm256_setzero_si256();
  __m256i a2 = _mm256_setzero_si256();
  __m256i a3 = _mm256_setzero_si256();
  __m256i a4 = _mm256_setzero_si256();
  __m256i a5 = _mm256_setzero_si256();
  __m256i a6 = _mm256_setzero_si256();
  __m256i a7 = _mm256_setzero_si256();
  size_t pf_lines = static_cast<size_t>(std::max(0, pf_distance));
  size_t streams = stream_count >= 8 ? 8 : 4;
  size_t chunk = (vecs / streams) & ~static_cast<size_t>(7);
  size_t i = 0;
  if (streams == 8) {
    for (; i < chunk; ++i) {
      const char *p0 = base + (0 * chunk + i) * 32;
      const char *p1 = base + (1 * chunk + i) * 32;
      const char *p2 = base + (2 * chunk + i) * 32;
      const char *p3 = base + (3 * chunk + i) * 32;
      const char *p4 = base + (4 * chunk + i) * 32;
      const char *p5 = base + (5 * chunk + i) * 32;
      const char *p6 = base + (6 * chunk + i) * 32;
      const char *p7 = base + (7 * chunk + i) * 32;
      if ((policy == "nta" || policy == "t0") && pf_lines && i + pf_lines * 2 < chunk) {
        size_t po = pf_lines * 2 * 32;
        policy_prefetch(p0 + po, policy);
        policy_prefetch(p1 + po, policy);
        policy_prefetch(p2 + po, policy);
        policy_prefetch(p3 + po, policy);
        policy_prefetch(p4 + po, policy);
        policy_prefetch(p5 + po, policy);
        policy_prefetch(p6 + po, policy);
        policy_prefetch(p7 + po, policy);
      }
      a0 = _mm256_add_epi64(a0, _mm256_loadu_si256(reinterpret_cast<const __m256i *>(p0)));
      a1 = _mm256_add_epi64(a1, _mm256_loadu_si256(reinterpret_cast<const __m256i *>(p1)));
      a2 = _mm256_add_epi64(a2, _mm256_loadu_si256(reinterpret_cast<const __m256i *>(p2)));
      a3 = _mm256_add_epi64(a3, _mm256_loadu_si256(reinterpret_cast<const __m256i *>(p3)));
      a4 = _mm256_add_epi64(a4, _mm256_loadu_si256(reinterpret_cast<const __m256i *>(p4)));
      a5 = _mm256_add_epi64(a5, _mm256_loadu_si256(reinterpret_cast<const __m256i *>(p5)));
      a6 = _mm256_add_epi64(a6, _mm256_loadu_si256(reinterpret_cast<const __m256i *>(p6)));
      a7 = _mm256_add_epi64(a7, _mm256_loadu_si256(reinterpret_cast<const __m256i *>(p7)));
    }
  } else {
    for (; i + 4 <= chunk; i += 4) {
    const char *p0 = base + (0 * chunk + i) * 32;
    const char *p1 = base + (1 * chunk + i) * 32;
    const char *p2 = base + (2 * chunk + i) * 32;
    const char *p3 = base + (3 * chunk + i) * 32;
    if ((policy == "nta" || policy == "t0") && pf_lines && i + pf_lines * 2 < chunk) {
      size_t po = pf_lines * 2 * 32;
      policy_prefetch(p0 + po, policy);
      policy_prefetch(p1 + po, policy);
      policy_prefetch(p2 + po, policy);
      policy_prefetch(p3 + po, policy);
    }
    a0 = _mm256_add_epi64(a0, _mm256_loadu_si256(reinterpret_cast<const __m256i *>(p0 + 0 * 32)));
    a1 = _mm256_add_epi64(a1, _mm256_loadu_si256(reinterpret_cast<const __m256i *>(p1 + 0 * 32)));
    a2 = _mm256_add_epi64(a2, _mm256_loadu_si256(reinterpret_cast<const __m256i *>(p2 + 0 * 32)));
    a3 = _mm256_add_epi64(a3, _mm256_loadu_si256(reinterpret_cast<const __m256i *>(p3 + 0 * 32)));
    a4 = _mm256_add_epi64(a4, _mm256_loadu_si256(reinterpret_cast<const __m256i *>(p0 + 1 * 32)));
    a5 = _mm256_add_epi64(a5, _mm256_loadu_si256(reinterpret_cast<const __m256i *>(p1 + 1 * 32)));
    a6 = _mm256_add_epi64(a6, _mm256_loadu_si256(reinterpret_cast<const __m256i *>(p2 + 1 * 32)));
    a7 = _mm256_add_epi64(a7, _mm256_loadu_si256(reinterpret_cast<const __m256i *>(p3 + 1 * 32)));
    a0 = _mm256_add_epi64(a0, _mm256_loadu_si256(reinterpret_cast<const __m256i *>(p0 + 2 * 32)));
    a1 = _mm256_add_epi64(a1, _mm256_loadu_si256(reinterpret_cast<const __m256i *>(p1 + 2 * 32)));
    a2 = _mm256_add_epi64(a2, _mm256_loadu_si256(reinterpret_cast<const __m256i *>(p2 + 2 * 32)));
    a3 = _mm256_add_epi64(a3, _mm256_loadu_si256(reinterpret_cast<const __m256i *>(p3 + 2 * 32)));
    a4 = _mm256_add_epi64(a4, _mm256_loadu_si256(reinterpret_cast<const __m256i *>(p0 + 3 * 32)));
    a5 = _mm256_add_epi64(a5, _mm256_loadu_si256(reinterpret_cast<const __m256i *>(p1 + 3 * 32)));
    a6 = _mm256_add_epi64(a6, _mm256_loadu_si256(reinterpret_cast<const __m256i *>(p2 + 3 * 32)));
    a7 = _mm256_add_epi64(a7, _mm256_loadu_si256(reinterpret_cast<const __m256i *>(p3 + 3 * 32)));
    }
  }
  a0 = _mm256_add_epi64(a0, a1);
  a2 = _mm256_add_epi64(a2, a3);
  a4 = _mm256_add_epi64(a4, a5);
  a6 = _mm256_add_epi64(a6, a7);
  a0 = _mm256_add_epi64(a0, a2);
  a4 = _mm256_add_epi64(a4, a6);
  a0 = _mm256_add_epi64(a0, a4);
  alignas(32) uint64_t tmp[4];
  _mm256_store_si256(reinterpret_cast<__m256i *>(tmp), a0);
  uint64_t sum = tmp[0] ^ tmp[1] ^ tmp[2] ^ tmp[3];
  const uint64_t *tail = reinterpret_cast<const uint64_t *>(base + streams * chunk * 32);
  size_t tail_words = (bytes - streams * chunk * 32) / sizeof(uint64_t);
  for (size_t j = 0; j < tail_words; ++j) sum ^= tail[j];
  return sum;
#else
  const uint64_t *p = reinterpret_cast<const uint64_t *>(fact);
  size_t words = n * (sizeof(Fact) / sizeof(uint64_t));
  uint64_t s0 = 0, s1 = 0, s2 = 0, s3 = 0, s4 = 0, s5 = 0, s6 = 0, s7 = 0;
  int pfd = std::max(0, pf_distance);
  size_t i = 0;
  size_t unroll = 32;
  for (; i + unroll <= words; i += unroll) {
    if ((policy == "nta" || policy == "t0") && pfd > 0 && i + static_cast<size_t>(pfd) * 2 < words) {
      policy_prefetch(reinterpret_cast<const char *>(&p[i + static_cast<size_t>(pfd) * 2]), policy);
    }
    s0 += p[i + 0] + p[i + 8] + p[i + 16] + p[i + 24];
    s1 += p[i + 1] + p[i + 9] + p[i + 17] + p[i + 25];
    s2 += p[i + 2] + p[i + 10] + p[i + 18] + p[i + 26];
    s3 += p[i + 3] + p[i + 11] + p[i + 19] + p[i + 27];
    s4 += p[i + 4] + p[i + 12] + p[i + 20] + p[i + 28];
    s5 += p[i + 5] + p[i + 13] + p[i + 21] + p[i + 29];
    s6 += p[i + 6] + p[i + 14] + p[i + 22] + p[i + 30];
    s7 += p[i + 7] + p[i + 15] + p[i + 23] + p[i + 31];
  }
  for (; i < words; ++i) s0 += p[i];
  return s0 ^ s1 ^ s2 ^ s3 ^ s4 ^ s5 ^ s6 ^ s7;
#endif
}

std::string json_escape(const std::string &s) {
  std::string o;
  for (char c : s) {
    if (c == '"' || c == '\\') { o.push_back('\\'); o.push_back(c); }
    else if (c == '\n') o += "\\n";
    else o.push_back(c);
  }
  return o;
}

void emit_json_prefix(const Config &c, void *fact, uint64_t fact_bytes, const std::vector<int> &cpus,
                      const std::vector<std::string> &roles = {}) {
  std::cout << "{";
  std::cout << "\"mode\":\"" << json_escape(c.mode) << "\",";
  // W7: the arm identity travels with the record (Sec5.1 rule). A batched run
  // and a serial run are different arms and must never be compared without it.
  std::cout << "\"probe_batch\":" << c.probe_batch << ",";
  std::cout << "\"policy\":\"" << json_escape(c.policy) << "\",";
  // W8: which channel carried the declaration. An m5op row and an mprotect row
  // are different arms -- the second one exercises I0/I1, the first does not.
  std::cout << "\"declare\":\"" << (g_declare == DeclareVia::MPROTECT ? "mprotect" : "m5op") << "\",";
  std::cout << "\"fact_bytes\":" << fact_bytes << ",";
  std::cout << "\"hot_bytes\":" << c.hot_bytes << ",";
  std::cout << "\"flush_distance\":" << c.flush_distance << ",";
  std::cout << "\"huge2m\":" << (c.huge2m ? "true" : "false") << ",";
  std::cout << "\"line_stride\":" << (c.line_stride ? "true" : "false") << ",";
  std::cout << "\"fact_node\":" << c.fact_node << ",";
  std::cout << "\"hot_node\":" << c.hot_node << ",";
  std::cout << "\"threads\":" << c.threads << ",";
  std::cout << "\"reps\":" << c.reps << ",";
  std::cout << "\"warmups\":" << c.warmups << ",";
  std::cout << "\"iterations\":" << c.iterations << ",";
  std::cout << "\"pf_distance\":" << c.pf_distance << ",";
  std::cout << "\"stream_count\":" << c.stream_count << ",";
  std::cout << "\"seed\":" << c.seed << ",";
  std::cout << "\"hit_rate\":" << c.hit_rate << ",";
  uintptr_t base = reinterpret_cast<uintptr_t>(fact);
  std::cout << "\"fact_base\":\"0x" << std::hex << base << "\",";
  std::cout << "\"fact_end\":\"0x" << (base + fact_bytes) << std::dec << "\",";
  std::cout << "\"thread_mapping\":" << cpu_mapping_json(cpus, c.threads, roles) << ",";
}

// --line-stride: one 8B load per 64B line instead of a dense scan. Ported
// verbatim from benchmarks/e2e/hash_join_gem5se (PR #2, branch
// gem5-hashjoin-forks) so that the fork can be retired rather than
// maintained as a third copy of this file. Opt-in; default off; the dense
// stream_read() path is untouched, and run_morsel never calls either.
// Line-granular stream read: ONE 8-byte load per 64B cache line, 8
// independent register accumulator chains. Low-uop-density BW probe for gem5
// builds (gem5 x86 cannot execute the AVX2 path; the scalar full-read loop
// spills accumulators and costs ~20 uops/line, capping the OoO window at
// ~10 in-flight lines). Memory-side traffic is identical (full 64B lines are
// transferred); only touched-word density differs. Disclose in frozen config.
uint64_t stream_read_lines(const Fact *fact, size_t n) {
  const unsigned char *base = reinterpret_cast<const unsigned char *>(fact);
  size_t bytes = n * sizeof(Fact);
  size_t lines = bytes / 64;
  uint64_t s0 = 0, s1 = 0, s2 = 0, s3 = 0, s4 = 0, s5 = 0, s6 = 0, s7 = 0;
  size_t i = 0;
  for (; i + 8 <= lines; i += 8) {
    s0 += *reinterpret_cast<const uint64_t *>(base + (i + 0) * 64);
    s1 += *reinterpret_cast<const uint64_t *>(base + (i + 1) * 64);
    s2 += *reinterpret_cast<const uint64_t *>(base + (i + 2) * 64);
    s3 += *reinterpret_cast<const uint64_t *>(base + (i + 3) * 64);
    s4 += *reinterpret_cast<const uint64_t *>(base + (i + 4) * 64);
    s5 += *reinterpret_cast<const uint64_t *>(base + (i + 5) * 64);
    s6 += *reinterpret_cast<const uint64_t *>(base + (i + 6) * 64);
    s7 += *reinterpret_cast<const uint64_t *>(base + (i + 7) * 64);
  }
  for (; i < lines; ++i)
    s0 += *reinterpret_cast<const uint64_t *>(base + i * 64);
  return s0 ^ s1 ^ s2 ^ s3 ^ s4 ^ s5 ^ s6 ^ s7;
}

void run_stream(Config c) {
  std::vector<int> cpus = parse_cpus(c.cpu_list);
  pin_cpu(cpus[0]);
  size_t n = c.fact_bytes / sizeof(Fact);
  c.fact_bytes = n * sizeof(Fact);
  Fact *fact = static_cast<Fact *>(alloc_bytes(c.fact_bytes, c.fact_node, c.huge2m, "fact"));
  std::vector<Entry> table;
  std::vector<int64_t> keys;
  // Report what was BUILT, not the config default: emit_json_prefix prints
  // c.hot_bytes, so a hardcoded size here would be published as 2 MiB while a
  // 1 MiB table was instantiated.  That is the F9 pattern -- a request reported
  // as a fact -- and it has cost this project five times.
  c.hot_bytes = 1ull << 20;
  build_table(table, keys, c.hot_bytes, c.seed);
  fill_fact(fact, n, keys, c.hit_rate, c.seed);
  // No prefault_region here.  fill_fact has written every tuple, so every page
  // is already faulted in, and prefault_region MUTATES -- see its definition.
  // The bracket below therefore times the declaration alone, which is what the
  // emitted field now says; it previously timed a prefault plus a declaration
  // under a name that claimed only the first.
  auto pf0 = std::chrono::steady_clock::now();
  if (c.policy == "stream") declare_streaming(fact, c.fact_bytes);
  double declare_sec = seconds_since(pf0);
  std::string placement;
  bool placed = check_pages_on_node(fact, c.fact_bytes, c.fact_node, &placement);
  if (!placed) {
    std::cerr << "FATAL: fact placement failed: " << placement << "\n";
    std::exit(10);
  }
  uint64_t checksum = 0;
  for (int i = 0; i < c.warmups; ++i) checksum ^= c.line_stride ? stream_read_lines(fact, n) : stream_read(fact, n, c.policy, c.pf_distance, c.stream_count);
  struct rusage ru_before {};
  struct rusage ru_after {};
  getrusage(RUSAGE_SELF, &ru_before);
  std::vector<double> samples;
  samples.reserve(c.reps);
  double total_sec = 0.0;
  // Window-scoped counters.  The k-th AGGBW_WINDOW_* marker in console.log is
  // the k-th stats section boundary in stats.txt: stderr and the stats dumps
  // are both ordered by simulated time, and the OPEN marker precedes its op
  // while the CLOSE marker follows its op.  simTicks is reset by the pair
  // (Root::RootStats::resetStats sets startTick = curTick()), so the section
  // between them is exactly the measured loop.
  if (c.window_brackets) {
    std::cerr << "AGGBW_WINDOW_OPEN cpu=" << cpus[0] << " reps=" << c.reps << "\n";
    std::cerr.flush();
    gem5_dump_stats_now();
    gem5_reset_stats_now();
  }
  for (int r = 0; r < c.reps; ++r) {
    auto t0 = std::chrono::steady_clock::now();
    checksum ^= c.line_stride ? stream_read_lines(fact, n) : stream_read(fact, n, c.policy, c.pf_distance, c.stream_count);
    double sec = seconds_since(t0);
    total_sec += sec;
    samples.push_back(static_cast<double>(c.fact_bytes) / sec / 1e9);
  }
  if (c.window_brackets) {
    gem5_dump_stats_now();
    gem5_reset_stats_now();
    std::cerr << "AGGBW_WINDOW_CLOSE cpu=" << cpus[0] << " seconds="
              << std::setprecision(9) << total_sec << "\n";
    std::cerr.flush();
  }
  getrusage(RUSAGE_SELF, &ru_after);
  double bytes = static_cast<double>(c.fact_bytes) * c.reps;
  SmapsInfo smi = smaps_info(fact);
  emit_json_prefix(c, fact, c.fact_bytes, cpus);
  std::cout << "\"placement\":\"" << json_escape(placement) << "\",";
  std::cout << "\"declare_seconds\":" << std::setprecision(9) << declare_sec << ",";
  std::cout << "\"window_brackets\":" << (c.window_brackets ? "true" : "false") << ",";
  std::cout << "\"anon_huge_kb\":" << smi.anon_huge_kb << ",";
  std::cout << "\"kernel_page_kb\":" << smi.kernel_page_kb << ",";
  std::cout << "\"mmu_page_kb\":" << smi.mmu_page_kb << ",";
  std::cout << "\"timed_minor_faults\":" << (ru_after.ru_minflt - ru_before.ru_minflt) << ",";
  std::cout << "\"timed_major_faults\":" << (ru_after.ru_majflt - ru_before.ru_majflt) << ",";
  emit_samples(samples);
  std::cout << "\"seconds\":" << std::setprecision(9) << total_sec << ",";
  std::cout << "\"bandwidth_gbps\":" << (bytes / total_sec / 1e9) << ",";
  std::cout << "\"checksum\":" << checksum << ",";
  std::cout << "\"status\":\"ok\"}\n";
  free_bytes(fact, c.fact_bytes, c.huge2m);
}

// S2 of E2E_BRIDGE_DESIGN: a two-process calibration, intentionally not an
// application result. The child is the CXL stream; the parent is a dependent,
// LLC-resident victim. Forking is essential: a fused thread cannot establish
// whether object-scoped admission protects a different execution context.
#ifdef GEM5_FS
struct FsE2EShared {
  std::atomic<int> ready;
  std::atomic<int> go;
  std::atomic<int> stream_started;
  std::atomic<int> victim_done;
  int stream_cpu;
  int stream_affinity_ok;
  int stream_placed;
  int child_exit;
  int victim_affinity_ok;
  uint64_t stream_fact_base;
  uint64_t stream_fact_bytes;
  char stream_placement[128];
  uint64_t stream_checksum;
  uint64_t victim_checksum;
  uint64_t stream_start_cycles;
  uint64_t stream_end_cycles;
  uint64_t victim_start_cycles;
  uint64_t victim_end_cycles;
  double stream_seconds;
  double victim_seconds;
  // fs-e2e-join adds a second completion edge: the victim stops when the
  // tenant's join finishes, so its window is exactly the contended one.
  std::atomic<int> tenant_done;
  // Set by the parent once the in-process stats dump has closed the ROI.  The
  // contended child must not write its JSON line through the simulated UART or
  // munmap its 32 MiB fact before that, or both land inside the measured
  // window -- and they land there only in wb/h2, never in qui, whose child
  // frees nothing.  That asymmetry contaminated every insertion count and miss
  // rate used to explain a result.
  std::atomic<int> stats_dumped;
  uint64_t victim_loads;
  uint64_t tenant_matches;
  int64_t tenant_sum;
  uint64_t tenant_hot_bytes;
};

// PAUSE, never sched_yield().  Every wait in this mode used to yield, and a
// yield is a syscall into the guest scheduler, which takes runqueue
// qspinlocks.  Two cores hammering those locks under gem5's CHI is W8.7's
// queued-spinlock livelock -- the defect the single-threaded FS arms were
// deliberately shaped to avoid.  It cost 5 arms across r6b and r6e: the hung
// arms ran 24 h at 99.7% KERNEL instructions with the sibling core quiesced
// for 4.56e9 cycles, while a healthy arm runs at 95% user instructions.
// Both roles are pinned to distinct guest CPUs, so nothing needs to yield for
// the other to make progress; a pause spin never enters the kernel at all.
void wait_for_go(FsE2EShared *s) {
  while (s->go.load(std::memory_order_acquire) == 0) __builtin_ia32_pause();
}

// A setup failure in the child must not leave the parent spinning forever
// before the measurement boundary.  This is deliberately a liveness guard,
// not a timeout: gem5 timing is not stable enough for a host-time limit to be
// a scientific gate.  Reaping an exited child makes the failed setup explicit.
bool child_reached_ready_or_exited(FsE2EShared *s, pid_t child, int *status) {
  while (s->ready.load(std::memory_order_acquire) < 1) {
    pid_t got = waitpid(child, status, WNOHANG);
    if (got == child) return false;
    if (got < 0) return false;
    __builtin_ia32_pause();
  }
  return true;
}

bool pinned_to_cpu(int expected) {
  cpu_set_t set;
  CPU_ZERO(&set);
  if (sched_getaffinity(0, sizeof(set), &set) != 0) return false;
  return CPU_COUNT(&set) == 1 && CPU_ISSET(expected, &set) && sched_getcpu() == expected;
}

void flush_cache_region(const void *p, uint64_t bytes) {
  const char *q = static_cast<const char *>(p);
  for (uint64_t off = 0; off < bytes; off += 64)
    _mm_clflush(q + off);
  _mm_mfence();
}

// A cache scrub that actually works under gem5 Ruby/CHI.
//
// CLFLUSH/CLFLUSHOPT are a SILENT NO-OP there: they retire as instructions and
// generate zero memory-system activity, so flush_cache_region() above leaves
// every level warm while appearing to succeed.  Measured: 512 flushed lines gave
// +511 dcache misses on gem5's classic hierarchy and +4 (noise) under CHI, at
// identical instruction counts.  See
// experiments/asplos/GEM5_RUBY_CLFLUSH_NOOP_2026-09-01.md.
//
// So displace rather than flush: read a disjoint ordinary-WB buffer several
// times larger than every cache combined.  A large contiguous region spans all
// HNF slices by address interleave, and because the buffer is never declared
// STREAMING it really allocates -- which makes the eviction terminal instead of
// dependent on the evicted line's own admission policy.  That is precisely what
// makes the scrub symmetric across the WB and STREAMING arms.
//
// Sized for the FS geometry: L1D 48 KiB + L2 2 MiB + HNF 2 x 5 MiB = ~12 MiB.
// 32 MiB is 2.7x that; two passes defeat residual LRU retention.
static const uint64_t SCRUB_BYTES = 32ull << 20;
static const int SCRUB_PASSES = 2;

static uint64_t scrub_caches(void *buf, uint64_t bytes, int passes) {
  // WRITE, do not read.  Two reasons, both learned the hard way:
  //
  // (a) alloc_bytes() mmaps without touching, and a READ of fresh anonymous
  //     memory faults onto Linux's SHARED ZERO PAGE -- 8192 pages collapse onto
  //     one 4 KiB frame, so a read sweep touches 64 lines, not 524288, and
  //     displaces nothing.  A write forces a distinct frame per page.
  // (b) This HNF is a non-inclusive victim cache: alloc_on_read{shared,unique,
  //     once}=false, alloc_on_writeback=true.  ONLY writebacks allocate.  A
  //     clean read sweep can evict the fact from L2 but can never displace it
  //     from the HNF -- which is the level this experiment is about.  Dirty
  //     lines evict as WriteBackFull and do allocate, which is what scrubs it.
  //
  // The first version of this routine read, and was therefore inert in exactly
  // the way the CLFLUSH scrub it replaced was inert.  See
  // experiments/asplos/GEM5_RUBY_CLFLUSH_NOOP_2026-09-01.md.
  volatile unsigned char *b = static_cast<volatile unsigned char *>(buf);
  for (int pass = 0; pass < passes; ++pass)
    for (uint64_t off = 0; off < bytes; off += 64)
      b[off] = static_cast<unsigned char>((off >> 6) + pass);  // volatile store
  _mm_mfence();
  uint64_t sink = 0;                       // read one line back per pass so the
  for (int pass = 0; pass < passes; ++pass)  // marker is non-zero when it worked
    sink += b[(bytes - 64) - static_cast<uint64_t>(pass) * 64];
  return sink;
}

// H2 admission proof: deliberately smaller than an application benchmark and
// deliberately stricter than stream-smoke.  It starts with a producer-like WB
// initialization, seals the consumer mapping, removes *all* local cache
// residue, and resets gem5 statistics immediately before the first consumer
// load.  Thus the final stats section is an admission experiment, not a blend
// of allocator, producer, TLB-shootdown, and consumer work.
void run_h2_admission(Config c) {
  if (c.policy != "wb" && c.policy != "stream") {
    std::cerr << "FATAL: h2-admission requires --policy wb or stream\n";
    std::exit(2);
  }
  if (c.warmups != 0 || c.reps != 1 || !c.line_stride) {
    std::cerr << "FATAL: h2-admission requires --warmups 0 --reps 1 --line-stride\n";
    std::exit(2);
  }
  if (c.policy == "stream" && g_declare != DeclareVia::MPROTECT) {
    std::cerr << "FATAL: h2-admission STREAMING arm requires --declare mprotect\n";
    std::exit(2);
  }
  std::vector<int> cpus = parse_cpus(c.cpu_list);
  pin_cpu(cpus[0]);
  const size_t n = c.fact_bytes / sizeof(Fact);
  c.fact_bytes = n * sizeof(Fact);
  if (n == 0 || c.fact_bytes % 64 != 0) {
    std::cerr << "FATAL: h2-admission requires a nonzero 64-byte-aligned fact size\n";
    std::exit(2);
  }
  Fact *fact = static_cast<Fact *>(alloc_bytes(c.fact_bytes, c.fact_node, false, "h2_admission_fact"));
  std::vector<Entry> table;
  std::vector<int64_t> keys;
  // Report what is BUILT, not the config default: emit_json_prefix prints
  // c.hot_bytes, so a hardcoded size here publishes 2 MiB while a 1 MiB table
  // was instantiated -- the F9 pattern, a request reported as a fact.
  c.hot_bytes = 1ull << 20;
  build_table(table, keys, c.hot_bytes, c.seed);
  fill_fact(fact, n, keys, c.hit_rate, c.seed);
  // No prefault_region here.  fill_fact has written every tuple, so every page
  // is already faulted in, and prefault_region MUTATES -- see its definition.
  // Placed here it corrupted exactly one fact key per 4 KiB page.
  if (c.policy == "stream") declare_streaming(fact, c.fact_bytes);
  // Experimental cache-state control, not a STREAMING API step.  Identical for
  // WB and STREAMING, and applied AFTER declaration so the state entering the
  // ROI is the declared state.  Coldness is NOT asserted here: the analyser
  // proves it from HNF demand hits inside the ROI (gate A3r).
  void *scrub = alloc_bytes(SCRUB_BYTES, c.hot_node, false, "h2_admission_scrub");
  const uint64_t scrub_sink = scrub_caches(scrub, SCRUB_BYTES, SCRUB_PASSES);
  std::string placement;
  const bool placed = check_pages_on_node(fact, c.fact_bytes, c.fact_node, &placement);
  if (!placed) {
    std::cerr << "FATAL: h2-admission fact placement failed: " << placement << "\n";
    std::exit(10);
  }
  std::cerr << "H2_ADMISSION_PHASE initialized_wb=1 sealed=" << (c.policy == "stream" ? 1 : 0)
            << " cold_scrub=evictbuf_" << (SCRUB_BYTES >> 20) << "MiBx" << SCRUB_PASSES
            << " scrub_sink=" << scrub_sink << " complete=1\n";
  std::cerr << "H2_ADMISSION_ROI_START policy=" << c.policy << "\n";
  struct rusage ru_before {}, ru_after {};
  getrusage(RUSAGE_SELF, &ru_before);
  // Reset last and dump first, so the console writes that frame the ROI fall
  // outside the counted window instead of inside it.
  gem5_reset_stats_now();
  auto t0 = std::chrono::steady_clock::now();
  const uint64_t checksum = stream_read_lines(fact, n);
  const double sec = seconds_since(t0);
  gem5_dump_stats_now();
  getrusage(RUSAGE_SELF, &ru_after);
  std::cerr << "H2_ADMISSION_ROI_END policy=" << c.policy << "\n";
  emit_json_prefix(c, fact, c.fact_bytes, cpus);
  std::cout << "\"h2_kind\":\"cold_admission\","
            << "\"cold_start_protocol\":\"wb_initialize;seal_if_stream;evict_buffer_scrub;mfence;resetstats;one_line_pass\","
            << "\"scrub_bytes\":" << SCRUB_BYTES << ","
            << "\"scrub_passes\":" << SCRUB_PASSES << ","
            << "\"pte_samples\":" << g_pte_samples << ","
            << "\"pte_samples_passed\":" << g_pte_passed << ","
            << "\"cold_scrub_complete\":true,"
            << "\"roi_stats_reset\":true,"
            << "\"pte_verified\":" << (c.policy == "stream" ? "true" : "null") << ","
            << "\"placement\":\"" << json_escape(placement) << "\","
            << "\"timed_minor_faults\":" << (ru_after.ru_minflt - ru_before.ru_minflt) << ","
            << "\"timed_major_faults\":" << (ru_after.ru_majflt - ru_before.ru_majflt) << ","
            << "\"seconds\":" << std::setprecision(9) << sec << ","
            << "\"bandwidth_gbps\":" << (static_cast<double>(c.fact_bytes) / sec / 1e9) << ","
            << "\"checksum\":" << checksum << ","
            << "\"status\":\"ok\"}\n";
  free_bytes(fact, c.fact_bytes, false);
}
#endif

void run_fs_e2e_calibrate(Config c) {
#ifndef GEM5_FS
  (void)c;
  std::cerr << "FATAL: fs-e2e-calibrate requires the GEM5_FS binary\n";
  std::exit(2);
#else
  if (c.threads != 1) {
    std::cerr << "FATAL: fs-e2e-calibrate owns its two process roles; use --threads 1\n";
    std::exit(2);
  }
  FsE2EShared *s = static_cast<FsE2EShared *>(mmap(nullptr, sizeof(*s),
      PROT_READ | PROT_WRITE, MAP_SHARED | MAP_ANONYMOUS, -1, 0));
  if (s == MAP_FAILED) { std::perror("mmap shared barrier"); std::exit(2); }
  new (&s->ready) std::atomic<int>(0);
  new (&s->go) std::atomic<int>(0);
  new (&s->stream_started) std::atomic<int>(0);
  new (&s->victim_done) std::atomic<int>(0);
  s->stream_cpu = -1; s->stream_affinity_ok = 0; s->stream_placed = 0; s->child_exit = -1;
  s->victim_affinity_ok = 0;
  s->stream_fact_base = s->stream_fact_bytes = 0;
  s->stream_placement[0] = '\0';
  s->stream_checksum = s->victim_checksum = 0;
  s->stream_start_cycles = s->stream_end_cycles = 0;
  s->victim_start_cycles = s->victim_end_cycles = 0;
  s->stream_seconds = s->victim_seconds = 0.0;

  pid_t child = fork();
  if (child < 0) { std::perror("fork streamer"); std::exit(2); }
  if (child == 0) {
    pin_cpu(0);
    s->stream_cpu = sched_getcpu();
    s->stream_affinity_ok = pinned_to_cpu(0) ? 1 : 0;
    if (c.policy == "quiet") {
      s->stream_placed = 1;
      std::snprintf(s->stream_placement, sizeof(s->stream_placement), "quiescent");
      std::cerr << "FS_E2E_STREAM_READY pid=" << getpid() << " cpu=" << s->stream_cpu
                << " placement=quiescent policy=quiet\n";
      s->ready.fetch_add(1, std::memory_order_release);
      wait_for_go(s);
      s->stream_start_cycles = rdtsc();
      s->stream_started.store(1, std::memory_order_release);
      while (s->victim_done.load(std::memory_order_acquire) == 0) __builtin_ia32_pause();
      s->stream_end_cycles = rdtsc();
      _exit(0);
    }
    size_t n = c.fact_bytes / sizeof(Fact);
    Fact *fact = static_cast<Fact *>(alloc_bytes(n * sizeof(Fact), c.fact_node,
                                                  false, "e2e_stream_fact"));
    // These are the *realized* streamed object properties.  The parent emits
    // the one combined record after reaping us, so never substitute its hot
    // victim buffer for this object in the provenance record.
    s->stream_fact_base = reinterpret_cast<uintptr_t>(fact);
    s->stream_fact_bytes = n * sizeof(Fact);
    // No prefault_region after this loop: the loop writes every tuple, so every
    // page is faulted in, and prefault_region MUTATES -- see its definition.
    for (size_t i = 0; i < n; ++i) fact[i] = Fact{static_cast<int64_t>(i), static_cast<int64_t>(i * 7)};
    if (c.policy == "stream") declare_streaming(fact, n * sizeof(Fact));
    // Setup writes allocate normally. Remove their residue before the victim
    // is warmed; otherwise WB and H2 begin from an uncontrolled, polluted LLC.
    //
    // This used flush_cache_region() -- i.e. CLFLUSH -- which is a SILENT NO-OP
    // under gem5 Ruby/CHI (512 flushed lines: +511 dcache misses on the classic
    // hierarchy, +4 under CHI, identical instruction counts).  Every S2 result
    // produced with it began from an uncontrolled LLC while reporting that it
    // had been scrubbed.  See GEM5_RUBY_CLFLUSH_NOOP_2026-09-01.md and the same
    // fix already applied to the h2-admission path.
    void *s2_scrub = alloc_bytes(SCRUB_BYTES, c.hot_node, false, "s2_scrub");
    const uint64_t s2_scrub_sink = scrub_caches(s2_scrub, SCRUB_BYTES, SCRUB_PASSES);
    std::string placement;
    s->stream_placed = check_pages_on_node(fact, n * sizeof(Fact), c.fact_node, &placement) ? 1 : 0;
    std::snprintf(s->stream_placement, sizeof(s->stream_placement), "%s", placement.c_str());
    std::cerr << "FS_E2E_STREAM_READY pid=" << getpid() << " cpu=" << s->stream_cpu
              << " placement=" << placement << " policy=" << c.policy
              << " scrub=evictbuf_" << (SCRUB_BYTES >> 20) << "MiBx" << SCRUB_PASSES
              << " scrub_sink=" << s2_scrub_sink << "\n";
    s->ready.fetch_add(1, std::memory_order_release);
    wait_for_go(s);
    auto t0 = std::chrono::steady_clock::now();
    s->stream_start_cycles = rdtsc();
    s->stream_started.store(1, std::memory_order_release);
    uint64_t sum = 0;
    for (int r = 0; r < c.reps; ++r) sum ^= stream_read_lines(fact, n);
    s->stream_end_cycles = rdtsc();
    s->stream_seconds = seconds_since(t0);
    s->stream_checksum = sum;
    free_bytes(fact, n * sizeof(Fact), false);
    _exit(0);
  }

  // The streamer's allocation, declaration, and cache cleanup must finish
  // before the victim is constructed/warmed. The previous concurrent setup
  // made the state at reset scheduler-dependent.
  int setup_status = 0;
  if (!child_reached_ready_or_exited(s, child, &setup_status)) {
    const int child_code = (setup_status >= 0 && WIFEXITED(setup_status))
        ? WEXITSTATUS(setup_status) : 255;
    std::cerr << "FATAL: fs-e2e-calibrate streamer failed before readiness"
              << " (exit=" << child_code << ")\n";
    munmap(s, sizeof(*s));
    std::exit(2);
  }
  pin_cpu(1);
  int victim_cpu = sched_getcpu();
  s->victim_affinity_ok = pinned_to_cpu(1) ? 1 : 0;
  // The victim is a pointer chase over 64-byte-aligned slots, built the same way
  // as the fs-e2e-join victim.  It used to be next[i] = (i + n/2 - 1) & (n - 1),
  // which is a Hamiltonian cycle and so satisfied every structural property one
  // would think to assert -- but two hops of it land on (i - 2), a dense backward
  // sweep at 8-byte granularity.  Measured on that construction, 83.6% of hops
  // stayed inside a line the previous hop had already touched, so the private L2
  // served most of the chase and the mode measured a bandwidth tax rather than a
  // latency one.  That is the same fault the fs-e2e-join victim was rebuilt to
  // remove; the comment there names this mode as the remaining offender.
  const size_t LINE_BYTES_V = 64;
  const size_t ELEMS_PER_LINE = LINE_BYTES_V / sizeof(uint64_t);
  const size_t vlines = c.hot_bytes / LINE_BYTES_V;
  if (vlines < 2 || (c.hot_bytes % LINE_BYTES_V) != 0) {
    std::cerr << "FATAL: fs-e2e-calibrate --hot-bytes must be a multiple of 64 and >= 128\n";
    std::exit(2);
  }
  const size_t n = vlines * ELEMS_PER_LINE;
  uint64_t *next = static_cast<uint64_t *>(alloc_bytes(n * sizeof(uint64_t), c.hot_node,
                                                        false, "e2e_victim_hot"));
  // PREFAULT FIRST, before the chain exists: prefault_region MUTATES, and run
  // after the build it walked next[] off its stride exactly as it did to the
  // r6d victim.  Same defect, same mode, found later.
  prefault_region(next, n * sizeof(uint64_t), "e2e_calibrate_victim");
  for (size_t i = 0; i < vlines; ++i) next[i * ELEMS_PER_LINE] = i * ELEMS_PER_LINE;
  // Sattolo: j < i on every step yields exactly one cycle over all vlines slots.
  // Seeded from --seed rather than a literal, so the permutation is reproducible
  // without being frozen; the arms of a calibration differ by policy, not seed,
  // so they still share a victim.
  SplitMix64 vrng(c.seed ^ 0x5A77010Full);
  for (size_t i = vlines - 1; i > 0; --i) {
    const size_t j = static_cast<size_t>(vrng.next() % i);
    const size_t ai = i * ELEMS_PER_LINE, bi = j * ELEMS_PER_LINE;
    const uint64_t t = next[ai]; next[ai] = next[bi]; next[bi] = t;
  }
  // Emit the cycle LENGTH, not a boolean.  "Follow the chain vlines times and
  // return to the start" is satisfied by any cycle whose length divides vlines,
  // 2 included -- which is precisely how the r6d two-line victim passed a gate
  // whose own comment warned about this.  Walk until the chain closes, and
  // require every hop to be in range and line-aligned.
  size_t cyc_len = 0, walk = 0;
  bool victim_structure_ok = true;
  do {
    const uint64_t nxt = next[walk];
    if (nxt >= n || (nxt % ELEMS_PER_LINE) != 0) { victim_structure_ok = false; break; }
    walk = static_cast<size_t>(nxt);
    ++cyc_len;
  } while (walk != 0 && cyc_len <= vlines);
  const bool victim_cycle_ok = victim_structure_ok && (cyc_len == vlines);
  volatile uint64_t warm_idx = 0;
  for (size_t i = 0; i < vlines; ++i) warm_idx = next[warm_idx];
  (void)warm_idx;
  std::string victim_placement;
  bool victim_placed = check_pages_on_node(next, n * sizeof(uint64_t), c.hot_node,
                                            &victim_placement);
  std::cerr << "FS_E2E_VICTIM_READY pid=" << getpid() << " cpu=" << victim_cpu
            << " placement=" << victim_placement
            << " victim_bytes=" << (n * sizeof(uint64_t))
            << " victim_lines=" << vlines
            << " cycle_len=" << cyc_len << "/" << vlines
            << " cycle_ok=" << (victim_cycle_ok ? 1 : 0) << "\n";
  s->ready.fetch_add(1, std::memory_order_release);
  while (s->ready.load(std::memory_order_acquire) != 2) __builtin_ia32_pause();
  // This is the measurement boundary: both mappings, page placement, H2 PTE
  // installation, and warm touches precede it. The parent alone resets global
  // gem5 stats and then releases both roles.
  gem5_reset_stats_now();
  std::cerr << "FS_E2E_MEASURE_START policy=" << c.policy << "\n";
  s->go.store(1, std::memory_order_release);
  while (s->stream_started.load(std::memory_order_acquire) == 0) __builtin_ia32_pause();
  auto t0 = std::chrono::steady_clock::now();
  s->victim_start_cycles = rdtsc();
  uint64_t idx = 0;
  for (uint64_t i = 0; i < c.iterations; ++i) idx = next[idx];
  s->victim_end_cycles = rdtsc();
  s->victim_seconds = seconds_since(t0);
  s->victim_checksum = idx;
  s->victim_done.store(1, std::memory_order_release);
  int status = 0;
  if (waitpid(child, &status, 0) < 0) { std::perror("waitpid streamer"); status = -1; }
  s->child_exit = (status >= 0 && WIFEXITED(status)) ? WEXITSTATUS(status) : 255;
  emit_json_prefix(c, reinterpret_cast<void *>(s->stream_fact_base),
                   s->stream_fact_bytes, {1}, {"victim"});
  std::cout << "\"e2e_kind\":\"calibration\","
            << "\"victim_cpu\":" << victim_cpu << ","
            << "\"stream_cpu\":" << s->stream_cpu << ","
            << "\"victim_affinity_ok\":" << (s->victim_affinity_ok ? "true" : "false") << ","
            << "\"stream_affinity_ok\":" << (s->stream_affinity_ok ? "true" : "false") << ","
            << "\"stream_placement\":\"" << json_escape(s->stream_placement) << "\","
            << "\"victim_placement\":\"" << json_escape(victim_placement) << "\","
            << "\"stream_placement_ok\":" << (s->stream_placed ? "true" : "false") << ","
            << "\"victim_placement_ok\":" << (victim_placed ? "true" : "false") << ","
            << "\"stream_checksum\":" << s->stream_checksum << ","
            << "\"victim_checksum\":" << s->victim_checksum << ","
            << "\"stream_seconds\":" << std::setprecision(9) << s->stream_seconds << ","
            << "\"victim_seconds\":" << s->victim_seconds << ","
            << "\"stream_start_cycles\":" << s->stream_start_cycles << ","
            << "\"stream_end_cycles\":" << s->stream_end_cycles << ","
            << "\"victim_start_cycles\":" << s->victim_start_cycles << ","
            << "\"victim_end_cycles\":" << s->victim_end_cycles << ","
            << "\"victim_cycles_per_access\":"
            << (c.iterations ? static_cast<double>(s->victim_end_cycles - s->victim_start_cycles) / c.iterations : 0.0) << ","
            << "\"stream_bytes\":" << (s->stream_fact_bytes * static_cast<uint64_t>(c.reps)) << ","
            << "\"victim_iterations\":" << c.iterations << ","
            << "\"victim_bytes\":" << (n * sizeof(uint64_t)) << ","
            << "\"victim_lines\":" << vlines << ","
            << "\"victim_cycle_len\":" << cyc_len << ","
            << "\"victim_cycle_ok\":" << (victim_cycle_ok ? "true" : "false") << ","
            << "\"victim_shuffle_seed\":" << c.seed << ","
            << "\"child_exit\":" << s->child_exit << ","
            << "\"status\":\"" << ((s->child_exit == 0 && victim_placed && s->stream_placed &&
                 s->victim_affinity_ok && s->stream_affinity_ok && victim_cycle_ok &&
                 s->stream_start_cycles <= s->victim_start_cycles &&
                 s->stream_end_cycles >= s->victim_end_cycles) ? "ok" : "failed") << "\"}\n";
  free_bytes(next, n * sizeof(uint64_t), false);
  munmap(s, sizeof(*s));
#endif
}

// The full-system analogue of the SE complete-join campaign.  It exists
// because every wedge number in the paper so far comes from --mode single
// under SE, where the declaration is an m5op backdoor: a simulator told to
// skip LLC fills will report skipped fills.  Here the tenant is a complete
// hash join whose stream is declared through the real kernel path
// (--declare mprotect), so the admission decision is made by the page tables
// the OS actually installed.
//
// Roles mirror fs-e2e-calibrate, which established that a fused thread cannot
// show whether object-scoped admission protects a *different* execution
// context.  Child on cpu0 is the tenant; parent on cpu1 is the LLC-resident
// victim.  Two differences from that mode:
//
//   1. The child joins instead of streaming.  It calls the same join_range()
//      that --mode single calls, so the SE and FS arms run the same kernel.
//   2. The victim stops when the tenant finishes rather than running a fixed
//      count, so its measured window is exactly the contended one.  Under
//      --policy quiet there is no tenant and the victim runs the full
//      --iterations cap: that is the uncontended baseline that protection is
//      normalised against.
void run_fs_e2e_join(Config c) {
#ifndef GEM5_FS
  (void)c;
  std::cerr << "FATAL: fs-e2e-join requires the GEM5_FS binary\n";
  std::exit(2);
#else
  if (c.threads != 1) {
    std::cerr << "FATAL: fs-e2e-join owns its two process roles; use --threads 1\n";
    std::exit(2);
  }
  if (c.victim_bytes < 4096 || c.victim_bytes % 64 != 0) {
    std::cerr << "FATAL: fs-e2e-join needs --victim-bytes (>=4096, multiple of 8);"
              << " --hot-bytes is the tenant's table, not the victim\n";
    std::exit(2);
  }
  FsE2EShared *s = static_cast<FsE2EShared *>(mmap(nullptr, sizeof(*s),
      PROT_READ | PROT_WRITE, MAP_SHARED | MAP_ANONYMOUS, -1, 0));
  if (s == MAP_FAILED) { std::perror("mmap shared barrier"); std::exit(2); }
  new (&s->ready) std::atomic<int>(0);
  new (&s->go) std::atomic<int>(0);
  new (&s->stream_started) std::atomic<int>(0);
  new (&s->victim_done) std::atomic<int>(0);
  new (&s->tenant_done) std::atomic<int>(0);
  new (&s->stats_dumped) std::atomic<int>(0);
  s->stream_cpu = -1;
  s->stream_affinity_ok = 0;
  s->stream_placed = 0;
  s->child_exit = 0;
  s->victim_affinity_ok = 0;
  s->stream_fact_base = s->stream_fact_bytes = 0;
  s->stream_placement[0] = '\0';
  s->stream_checksum = s->victim_checksum = 0;
  s->stream_start_cycles = s->stream_end_cycles = 0;
  s->victim_start_cycles = s->victim_end_cycles = 0;
  s->stream_seconds = s->victim_seconds = 0.0;
  s->victim_loads = 0;
  s->tenant_matches = 0;
  s->tenant_sum = 0;
  s->tenant_hot_bytes = 0;

  const size_t tuples = c.fact_bytes / sizeof(Fact);

  pid_t child = fork();
  if (child < 0) { std::perror("fork tenant"); std::exit(2); }
  if (child == 0) {
    pin_cpu(0);
    s->stream_cpu = sched_getcpu();
    s->stream_affinity_ok = pinned_to_cpu(0) ? 1 : 0;
    if (c.policy == "quiet") {
      // THE BASELINE MUST DIFFER FROM THE CONTENDED ARMS IN EXACTLY ONE WAY:
      // no stream.  r6b's quiet arm returned here before build_table, so its
      // records read instantiated_hot_bytes=0 and its victim owned the LLC with
      // 4 MiB of headroom the contended victims never had.  (wb - qui) then
      // conflated harm from the STREAMING-eligible fact stream with harm from
      // the tenant's non-streaming hash table -- and H2 can only ever remove
      // the former, so R had a structural ceiling unrelated to H2's quality and
      // the tax was not stream-attributable.  Build the table, scrub exactly as
      // the contended arms do, and keep probing it for the whole window.
      std::vector<Entry> table;
      std::vector<int64_t> keys;
      build_table(table, keys, c.hot_bytes, c.seed);
      s->tenant_hot_bytes = static_cast<uint64_t>(table.size()) * sizeof(Entry);
      void *scrub = alloc_bytes(SCRUB_BYTES, c.hot_node, false, "e2e_join_scrub");
      const uint64_t scrub_sink = scrub_caches(scrub, SCRUB_BYTES, SCRUB_PASSES);
      warm_table(table);
      s->stream_placed = 1;
      std::snprintf(s->stream_placement, sizeof(s->stream_placement),
                    "quiescent_table_resident");
      std::cerr << "FS_E2E_JOIN_TENANT_READY pid=" << getpid() << " cpu=" << s->stream_cpu
                << " placement=quiescent_table_resident policy=quiet declared=no"
                << " fact_bytes=0"
                << " instantiated_hot_bytes=" << s->tenant_hot_bytes
                << " scrub=evictbuf_" << (SCRUB_BYTES >> 20) << "MiBx" << SCRUB_PASSES
                << " scrub_sink=" << scrub_sink << "\n";
      s->ready.fetch_add(1, std::memory_order_release);
      wait_for_go(s);
      s->stream_start_cycles = rdtsc();
      s->stream_started.store(1, std::memory_order_release);
      // tenant_done is deliberately never set: the victim runs its full cap.
      //
      // Probing the table rather than __builtin_ia32_pause()-spinning.  r6b's quiet arm
      // spun on __builtin_ia32_pause() and generated MORE HNF data-array writes (3.71M)
      // than the stream under test (3.14M) -- essentially all of it cpu0's
      // syscall loop, so the "uncontended" baseline had a syscall-thrashing
      // neighbour that the contended arms did not.  Re-reading the table is
      // also what the contended tenant actually does to it, which keeps the
      // table's residency comparable across arms.
      while (s->victim_done.load(std::memory_order_acquire) == 0) warm_table(table);
      s->stream_end_cycles = rdtsc();
      _exit(0);
    }
    Fact *fact = static_cast<Fact *>(alloc_bytes(tuples * sizeof(Fact), c.fact_node,
                                                 c.huge2m, "e2e_join_fact"));
    std::vector<Entry> table;
    std::vector<int64_t> keys;
    build_table(table, keys, c.hot_bytes, c.seed);
    fill_fact(fact, tuples, keys, c.hit_rate, c.seed);
    // NO prefault_region(fact, ...) here.  fill_fact has already written every
    // byte, so every page is faulted in -- and prefault_region MUTATES:
    // q[off] = q[off] + 1 on the first byte of each page and on the last.
    // fact[i].fk is an int64_t at offset 0 of each page, so it corrupted the
    // low byte of the key on 8,192 of 2,097,152 tuples (0.39%), and those
    // probes then missed.  Symmetric across arms at a seed, so the matches
    // cross-check passed and the measurement was not materially moved -- but
    // the tenant was not computing the join it reported.  Same defect class as
    // the victim-chase corruption: found there, not checked here.
    if (c.policy == "stream") declare_streaming(fact, tuples * sizeof(Fact));
    s->stream_fact_base = reinterpret_cast<uintptr_t>(fact);
    s->stream_fact_bytes = tuples * sizeof(Fact);
    s->tenant_hot_bytes = static_cast<uint64_t>(table.size()) * sizeof(Entry);
    // Setup writes allocate normally; remove their residue before the victim
    // is warmed, or WB and H2 both begin from an uncontrolled LLC.  CLFLUSH is
    // a silent no-op under Ruby/CHI, so this displaces by writing.
    void *scrub = alloc_bytes(SCRUB_BYTES, c.hot_node, false, "e2e_join_scrub");
    const uint64_t scrub_sink = scrub_caches(scrub, SCRUB_BYTES, SCRUB_PASSES);
    // The table is a reused structure, unlike the stream, and --mode single
    // warms it before its timed window.  The victim's own warm follows this
    // one and will evict some of it; that transient is identical in every arm,
    // so it cannot bias the wb/h2 contrast this campaign exists to measure.
    warm_table(table);
    std::string placement;
    s->stream_placed = check_pages_on_node(fact, tuples * sizeof(Fact), c.fact_node,
                                           &placement) ? 1 : 0;
    std::snprintf(s->stream_placement, sizeof(s->stream_placement), "%s", placement.c_str());
    std::cerr << "FS_E2E_JOIN_TENANT_READY pid=" << getpid() << " cpu=" << s->stream_cpu
              << " placement=" << placement << " policy=" << c.policy
              << " declared=" << (c.policy == "stream" ? "yes" : "no")
              << " fact_bytes=" << (tuples * sizeof(Fact))
              << " instantiated_hot_bytes=" << s->tenant_hot_bytes
              << " scrub=evictbuf_" << (SCRUB_BYTES >> 20) << "MiBx" << SCRUB_PASSES
              << " scrub_sink=" << scrub_sink << "\n";
    s->ready.fetch_add(1, std::memory_order_release);
    wait_for_go(s);
    auto t0 = std::chrono::steady_clock::now();
    s->stream_start_cycles = rdtsc();
    s->stream_started.store(1, std::memory_order_release);
    Result out;
    for (int r = 0; r < c.reps; ++r) {
      Result rr = join_range(table, fact, 0, tuples, c.policy, c.pf_distance);
      out.matches += rr.matches;
      out.sum += rr.sum;
    }
    s->stream_end_cycles = rdtsc();
    s->stream_seconds = seconds_since(t0);
    s->tenant_matches = out.matches;
    s->tenant_sum = out.sum;
    s->tenant_done.store(1, std::memory_order_release);
    // Wait for the parent's dump before doing anything that touches memory or
    // the console: the UART write and the 32 MiB munmap (with its TLB
    // shootdowns) are teardown, not measured work.
    while (s->stats_dumped.load(std::memory_order_acquire) == 0)
      __builtin_ia32_pause();
    std::cerr << "FS_E2E_JOIN_TENANT_END seconds=" << std::setprecision(9)
              << s->stream_seconds << " matches=" << out.matches << std::endl;
    free_bytes(fact, tuples * sizeof(Fact), c.huge2m);
    _exit(0);
  }

  int setup_status = 0;
  if (!child_reached_ready_or_exited(s, child, &setup_status)) {
    const int child_code = (setup_status >= 0 && WIFEXITED(setup_status))
        ? WEXITSTATUS(setup_status) : 255;
    std::cerr << "FATAL: fs-e2e-join tenant failed before readiness"
              << " (exit=" << child_code << ")\n";
    munmap(s, sizeof(*s));
    std::exit(2);
  }
  pin_cpu(1);
  int victim_cpu = sched_getcpu();
  s->victim_affinity_ok = pinned_to_cpu(1) ? 1 : 0;
  // Element width and permutation deliberately match the SE campaign's victim
  // (gem5/testcase/dutyfree/victim.c): 32-bit elements shuffled by Sattolo's
  // algorithm, which gives a single random cycle for any N.  A constant-stride
  // cycle -- what fs-e2e-calibrate uses -- is a materially easier victim, and
  // the SE numbers this campaign will be read beside were produced against the
  // random one.  Nothing here needs a power of two, which is what lets the
  // footprint sit exactly on silicon's victim/LLC ratio rather than near it.
  // ONE LIVE ELEMENT PER 64-BYTE LINE.
  //
  // The first version of this mode packed 16 live ints into every line, which
  // is what r5's victim.c does.  At this L2 size that is a measurement fault,
  // not a detail: each line was then touched 16 times per traversal, so the
  // private L2 served 66% of the chase.  H2 governs the *shared* LLC, so that
  // traffic is structurally beyond its reach -- and of the 34% that did reach
  // the LLC, 97.6% still hit under full load.  The campaign therefore measured
  // a fabric/bandwidth tax, which H2 cannot remove, rather than the capacity
  // tax it exists to remove.  Striding to one element per line makes the
  // footprint the L2 sees equal to the footprint actually requested.
  const size_t LINE_BYTES_V = 64;
  const size_t ELEMS_PER_LINE = LINE_BYTES_V / sizeof(int);
  const size_t vlines = c.victim_bytes / LINE_BYTES_V;
  if (vlines < 2) {
    std::cerr << "FATAL: fs-e2e-join --victim-bytes too small\n";
    std::exit(2);
  }
  const size_t vn = vlines * ELEMS_PER_LINE;
  int *next = static_cast<int *>(alloc_bytes(vn * sizeof(int), c.hot_node,
                                             false, "e2e_victim_hot"));
  // PREFAULT FIRST.  prefault_region() does q[off] = q[off] + 1 on the first
  // byte of every page and on the last byte -- it MUTATES.  Running it after
  // the shuffle (r6d) incremented next[0] from 1191728 to 1191729, which is no
  // longer a multiple of ELEMS_PER_LINE, so the chase landed in a never-written
  // slot holding 0, bounced straight back to index 0, and the victim chased
  // TWO cache lines for the whole campaign.
  prefault_region(next, vn * sizeof(int), "e2e_join_victim");
  for (size_t i = 0; i < vlines; ++i)
    next[i * ELEMS_PER_LINE] = static_cast<int>(i * ELEMS_PER_LINE);
  std::srand(42);
  for (size_t i = vlines - 1; i > 0; --i) {
    const size_t j = static_cast<size_t>(std::rand()) % i;  // j < i => one cycle
    const size_t ai = i * ELEMS_PER_LINE, bi = j * ELEMS_PER_LINE;
    const int t = next[ai]; next[ai] = next[bi]; next[bi] = t;
  }
  // Measure the TRUE cycle length.  The previous check asked only whether
  // following the chain vlines times returns to the start -- which ANY cycle
  // whose length divides vlines satisfies, 2 included, since vlines is
  // 2^15 * 3.  That is exactly how the r6d corruption passed a gate whose own
  // comment warned about this failure.  Walk until we come back, and require
  // the length to be the whole object; also require every hop to be a live,
  // in-range, line-aligned slot.
  size_t cyc_len = 0, probe = 0;
  bool structure_ok = true;
  do {
    const int nxt = next[probe];
    if (nxt < 0 || static_cast<size_t>(nxt) >= vn ||
        (static_cast<size_t>(nxt) % ELEMS_PER_LINE) != 0) { structure_ok = false; break; }
    probe = static_cast<size_t>(nxt);
    ++cyc_len;
  } while (probe != 0 && cyc_len <= vlines);
  const bool victim_cycle_ok = structure_ok && (cyc_len == vlines);
  volatile int warm_idx = 0;
  for (size_t i = 0; i < vlines; ++i) warm_idx = next[warm_idx];
  (void)warm_idx;
  std::string victim_placement;
  bool victim_placed = check_pages_on_node(next, vn * sizeof(int), c.hot_node,
                                           &victim_placement);
  std::cerr << "FS_E2E_JOIN_VICTIM_READY pid=" << getpid() << " cpu=" << victim_cpu
            << " placement=" << victim_placement
            << " victim_bytes=" << (vn * sizeof(int))
            << " victim_lines=" << vlines
            << " cycle_len=" << cyc_len << "/" << vlines
            << " cycle_ok=" << (victim_cycle_ok ? 1 : 0) << "\n";
  s->ready.fetch_add(1, std::memory_order_release);
  while (s->ready.load(std::memory_order_acquire) != 2) __builtin_ia32_pause();
  // Measurement boundary: both mappings, placement, any H2 PTE installation,
  // and both warm passes precede it.
  gem5_reset_stats_now();
  std::cerr << "FS_E2E_JOIN_MEASURE_START policy=" << c.policy << "\n";
  s->go.store(1, std::memory_order_release);
  while (s->stream_started.load(std::memory_order_acquire) == 0) __builtin_ia32_pause();
  auto t0 = std::chrono::steady_clock::now();
  // Sample the victim's cost across the window.  An 8 MiB single-pass stream
  // cannot fill a 10 MiB LLC even once, so in r6b displacement rose
  // monotonically for the whole window and the reported cyc/load was the mean
  // of a ramp, not a rate.  These buckets make the difference measurable
  // instead of assumed: if the last bucket differs from the mean, the number
  // is still a transient and must be reported as one.
  // FIXED ABSOLUTE bucket size, not c.iterations/VBUCKETS.  --iterations is a
  // CAP, and a contended arm stops on tenant_done long before reaching it: at
  // --iterations 20000000 the divisor gave a 1,000,000-load bucket against
  // ~1.2M actual loads, i.e. ONE bucket equal to the whole-window mean -- so
  // the plateau instrument was blind in exactly the arms that need it, and
  // 20-buckets-wide only in the quiet arm that has no stream to ramp against.
  static const int VBUCKETS = 64;
  static const uint64_t VBUCKET_LOADS = 25000;
  uint64_t bucket_cyc[VBUCKETS] = {0};
  uint64_t bucket_ld[VBUCKETS] = {0};
  const uint64_t bucket_every = VBUCKET_LOADS;
  int bucket = 0;
  uint64_t bucket_l0 = 0;
  s->victim_start_cycles = rdtsc();
  uint64_t bucket_t0 = s->victim_start_cycles;
  int idx = 0;
  uint64_t loads = 0;
  for (uint64_t i = 0; i < c.iterations; ++i) {
    idx = next[idx];
    ++loads;
    // Polled rather than per-iteration: the chase is dependent, so a relaxed
    // load every 1024 dereferences costs almost nothing, and it bounds how far
    // past the tenant's finish the victim can run -- which is what makes the
    // victim's window a contended window.
    if ((i & 1023ull) == 1023ull && s->tenant_done.load(std::memory_order_relaxed)) break;
    if (loads - bucket_l0 >= bucket_every && bucket < VBUCKETS) {
      const uint64_t now = rdtsc();
      bucket_cyc[bucket] = now - bucket_t0;
      bucket_ld[bucket] = loads - bucket_l0;
      ++bucket;
      bucket_t0 = now;
      bucket_l0 = loads;
    }
  }
  s->victim_end_cycles = rdtsc();
  // CLOSE THE ROI HERE, in process.  Previously nothing called
  // gem5_dump_stats_now() in this mode, so the first stats section ran on to
  // the rcS's `m5 dumpstats` -- i.e. through the child's munmap and TLB
  // shootdowns, waitpid, the JSON write over the UART, the victim's own munmap,
  // process teardown, the shell, and a fork+exec of /sbin/m5.
  gem5_dump_stats_now();
  s->stats_dumped.store(1, std::memory_order_release);
  s->victim_seconds = seconds_since(t0);
  s->victim_checksum = static_cast<uint64_t>(idx);
  s->victim_loads = loads;
  s->victim_done.store(1, std::memory_order_release);
  int status = 0;
  if (waitpid(child, &status, 0) < 0) { std::perror("waitpid tenant"); status = -1; }
  s->child_exit = (status >= 0 && WIFEXITED(status)) ? WEXITSTATUS(status) : 255;

  const double victim_cpa = loads
      ? static_cast<double>(s->victim_end_cycles - s->victim_start_cycles) / loads : 0.0;
  const bool ran_join = (c.policy != "quiet");
  const double tenant_mtps = (ran_join && s->stream_seconds > 0.0)
      ? static_cast<double>(tuples) * c.reps / s->stream_seconds / 1e6 : 0.0;
  // The victim's window must be a *contended* window.  It cannot be strictly
  // contained in the tenant's, because the victim stops precisely because the
  // tenant finished and so always ends one poll interval later; requiring
  // containment (which is what fs-e2e-calibrate requires of its stream) would
  // fail every well-formed run of this mode.  What must hold is that the
  // tenant started first and that the uncontended tail is negligible.
  const uint64_t victim_span = (s->victim_end_cycles > s->victim_start_cycles)
      ? s->victim_end_cycles - s->victim_start_cycles : 0;
  const uint64_t overshoot = (ran_join && s->victim_end_cycles > s->stream_end_cycles)
      ? s->victim_end_cycles - s->stream_end_cycles : 0;
  const double overshoot_frac = victim_span ? static_cast<double>(overshoot) / victim_span : 0.0;
  const bool covered = !ran_join ||
      (s->stream_start_cycles <= s->victim_start_cycles && overshoot_frac <= 0.02);
  const bool capped = (loads >= c.iterations);

  emit_json_prefix(c, reinterpret_cast<void *>(s->stream_fact_base),
                   s->stream_fact_bytes, {1}, {"victim"});
  std::cout << "\"e2e_kind\":\"complete_join\","
            << "\"victim_cpu\":" << victim_cpu << ","
            << "\"tenant_cpu\":" << s->stream_cpu << ","
            << "\"victim_affinity_ok\":" << (s->victim_affinity_ok ? "true" : "false") << ","
            << "\"tenant_affinity_ok\":" << (s->stream_affinity_ok ? "true" : "false") << ","
            << "\"tenant_placement\":\"" << json_escape(s->stream_placement) << "\","
            << "\"victim_placement\":\"" << json_escape(victim_placement) << "\","
            << "\"tenant_placement_ok\":" << (s->stream_placed ? "true" : "false") << ","
            << "\"victim_placement_ok\":" << (victim_placed ? "true" : "false") << ","
            << "\"victim_bytes\":" << (vn * sizeof(int)) << ","
            << "\"victim_lines\":" << vlines << ","
            << "\"victim_cycle_ok\":" << (victim_cycle_ok ? "true" : "false") << ","
            << "\"victim_cycle_len\":" << cyc_len << ","
            << "\"victim_iterations_cap\":" << c.iterations << ","
            << "\"victim_loads\":" << loads << ","
            << "\"victim_capped\":" << (capped ? "true" : "false") << ","
            << "\"victim_overshoot_cycles\":" << overshoot << ","
            << "\"victim_overshoot_frac\":" << overshoot_frac << ","
            << "\"victim_checksum\":" << s->victim_checksum << ","
            << "\"victim_seconds\":" << std::setprecision(9) << s->victim_seconds << ","
            << "\"victim_cycles_per_access\":" << victim_cpa << ","
            << "\"victim_cpa_buckets\":[";
  for (int b = 0; b < bucket; ++b)
    std::cout << (b ? "," : "")
              << (bucket_ld[b] ? static_cast<double>(bucket_cyc[b]) / bucket_ld[b] : 0.0);
  std::cout << "],"
            << "\"victim_cpa_bucket_loads\":" << bucket_every << ","
            << "\"victim_start_cycles\":" << s->victim_start_cycles << ","
            << "\"victim_end_cycles\":" << s->victim_end_cycles << ","
            << "\"tenant_ran_join\":" << (ran_join ? "true" : "false") << ","
            << "\"tenant_seconds\":" << s->stream_seconds << ","
            << "\"tenant_start_cycles\":" << s->stream_start_cycles << ","
            << "\"tenant_end_cycles\":" << s->stream_end_cycles << ","
            << "\"instantiated_hot_bytes\":" << s->tenant_hot_bytes << ","
            << "\"join_mtuples_per_s\":" << tenant_mtps << ","
            << "\"matches\":" << s->tenant_matches << ","
            << "\"sum\":" << s->tenant_sum << ","
            << "\"tenant_covers_victim\":" << (covered ? "true" : "false") << ","
            << "\"child_exit\":" << s->child_exit << ","
            << "\"status\":\"" << ((s->child_exit == 0 && victim_placed && s->stream_placed &&
                 s->victim_affinity_ok && s->stream_affinity_ok && covered &&
                 victim_cycle_ok &&
                 (ran_join ? !capped : capped)) ? "ok" : "failed") << "\"}\n";
  std::cout.flush();
  std::cerr.flush();
  free_bytes(next, vn * sizeof(int), false);
  munmap(s, sizeof(*s));
#endif
}

void run_latency(Config c) {
  std::vector<int> cpus = parse_cpus(c.cpu_list);
  pin_cpu(cpus[0]);
  uint64_t bytes = c.fact_bytes;
  size_t n = bytes / sizeof(uint64_t);
  bytes = n * sizeof(uint64_t);
  uint64_t *next = static_cast<uint64_t *>(alloc_bytes(bytes, c.fact_node, c.huge2m, "latency"));
  prefault_region(next, bytes);
  bool power2 = n && ((n & (n - 1)) == 0);
  int bits = power2 ? static_cast<int>(__builtin_ctzll(static_cast<unsigned long long>(n))) : 0;
  if (power2 && !(bits & 1)) {
    for (size_t i = 0; i < n; ++i) {
      uint64_t cur = feistel_permute(i, bits, c.seed);
      uint64_t nxt = feistel_permute((i + 1) & (n - 1), bits, c.seed);
      next[cur] = nxt;
    }
  } else {
    size_t stride = (2ull * 1024 * 1024) / sizeof(uint64_t) + 1;
    while (std::gcd(stride, n) != 1) stride += 2;
    for (size_t i = 0; i < n; ++i) next[i] = (i + stride) % n;
  }
  std::string placement;
  bool placed = check_pages_on_node(next, bytes, c.fact_node, &placement);
  if (!placed) {
    std::cerr << "FATAL: latency placement failed: " << placement << "\n";
    std::exit(10);
  }
  volatile uint64_t idx = 0;
  size_t warm = std::min<size_t>(n, 1ull << 20);
  for (size_t i = 0; i < warm; ++i) idx = next[idx];
  uint64_t iters = static_cast<uint64_t>(c.reps) * 1000000ull;
  auto t0 = std::chrono::steady_clock::now();
  for (uint64_t i = 0; i < iters; ++i) idx = next[idx];
  double sec = seconds_since(t0);
  SmapsInfo smi = smaps_info(next);
  emit_json_prefix(c, next, bytes, cpus);
  std::cout << "\"placement\":\"" << json_escape(placement) << "\",";
  std::cout << "\"anon_huge_kb\":" << smi.anon_huge_kb << ",";
  std::cout << "\"kernel_page_kb\":" << smi.kernel_page_kb << ",";
  std::cout << "\"mmu_page_kb\":" << smi.mmu_page_kb << ",";
  std::cout << "\"iterations\":" << iters << ",";
  std::cout << "\"randomized_chain\":" << ((power2 && !(bits & 1)) ? "true" : "false") << ",";
  std::cout << "\"seconds\":" << std::setprecision(9) << sec << ",";
  std::cout << "\"latency_ns\":" << (sec * 1e9 / static_cast<double>(iters)) << ",";
  std::cout << "\"final_index\":" << idx << ",";
  std::cout << "\"status\":\"ok\"}\n";
  free_bytes(next, bytes, c.huge2m);
}

void run_single(Config c) {
  if (c.policy == "cat") {
    std::cerr << "deferred: --policy cat needs resctrl control-group privilege\n";
    std::exit(20);
  }
  if (c.policy == "stream") {
#ifndef GEM5
    // W8: the alias exists because natively the m5op tag is unavailable -- not
    // because a Streaming declaration is impossible off the simulator. With
    // --declare mprotect the declaration goes through the kernel, which is a
    // real syscall on a real host; aliasing it to wb would turn an explicitly
    // requested arm into a silently different one (F12).
    if (g_declare == DeclareVia::M5OP) {
      std::cerr << "warning: native --policy stream aliases wb; gem5-only tag is unavailable\n";
      c.policy = "wb";
    }
#else
    std::cerr << "warning: GEM5 --policy stream is a simulator-facing tag; C++ loads remain normal\n";
#endif
  }
  std::vector<int> cpus = parse_cpus(c.cpu_list);
  pin_cpu(cpus[0]);
  size_t n = c.fact_bytes / sizeof(Fact);
  c.fact_bytes = n * sizeof(Fact);
  Fact *fact = static_cast<Fact *>(alloc_bytes(c.fact_bytes, c.fact_node, c.huge2m, "fact"));
  std::vector<Entry> table;
  std::vector<int64_t> keys;
  build_table(table, keys, c.hot_bytes, c.seed);
  fill_fact(fact, n, keys, c.hit_rate, c.seed);
  // No prefault_region here.  fill_fact has written every tuple, so every page
  // is already faulted in, and prefault_region MUTATES -- see its definition.
  // Placed here it corrupted exactly one fact key per 4 KiB page.
  if (c.policy == "stream") declare_streaming(fact, c.fact_bytes);
  std::string placement;
  bool placed = check_pages_on_node(fact, c.fact_bytes, c.fact_node, &placement);
  if (!placed) {
    std::cerr << "FATAL: fact placement failed: " << placement << "\n";
    std::exit(10);
  }
  Result ref;
  if (c.check) ref = scalar_join(table, fact, n);
  Result out;
  // --flush-distance was a silent no-op in --mode single: the flag was parsed
  // and echoed into JSON while join_range (no clflushopt) still ran.  That is
  // the CLFLUSH-under-Ruby pattern on silicon.  Dispatch here so the fb arm's
  // identity can be read back from join_path, not from the launcher's intent.
  const size_t flush_distance = c.flush_distance;
  auto do_join = [&]() {
    if (flush_distance > 0 || c.policy == "fbo") {
      return join_range_flushbehind(table, fact, 0, n, c.policy, c.pf_distance,
                                    flush_distance);
    }
    return join_range(table, fact, 0, n, c.policy, c.pf_distance);
  };
  for (int i = 0; i < c.warmups; ++i) {
    warm_table(table);
    out = do_join();
  }
  warm_table(table);
  ProbeTiming pt = probe_timing(table, keys, std::min<size_t>(keys.size(), 1 << 20));
  std::vector<double> samples;
  samples.reserve(c.reps);
  double total_sec = 0.0;
  out = {};
  // Start the measured window after build_table/fill_fact/prefault/declaration.
  // Measured on the superseded campaign: setup costs ~113M cycles for an 8 MiB
  // fact at the observed tenant IPC of 0.204, which was 38-55% of the victim's
  // window -- and STREAMING is not declared for any of it.  A no-op off gem5.
  gem5_reset_stats_now();
  const uint64_t instantiated_hot = static_cast<uint64_t>(table.size()) * sizeof(Entry);
  std::cerr << "JOIN_MEASURE_BEGIN"
            << " fact_bytes=" << c.fact_bytes
            << " instantiated_hot_bytes=" << instantiated_hot
            << " flush_distance=" << flush_distance
            << " policy=" << c.policy
            << " pf_distance=" << c.pf_distance
            << " cpu=" << cpus[0]
            << std::endl;
  for (int r = 0; r < c.reps; ++r) {
    auto t0 = std::chrono::steady_clock::now();
    Result rr = do_join();
    double sec = seconds_since(t0);
    total_sec += sec;
    samples.push_back(static_cast<double>(n) / sec / 1e6);
    out.matches += rr.matches;
    out.sum += rr.sum;
  }
  std::cerr << "JOIN_MEASURE_END seconds=" << std::setprecision(9) << total_sec
            << std::endl;
  bool ok = !c.check || (out.matches == ref.matches * static_cast<uint64_t>(c.reps) &&
                         out.sum == ref.sum * static_cast<int64_t>(c.reps));
  emit_json_prefix(c, fact, c.fact_bytes, cpus);
  std::cout << "\"placement\":\"" << json_escape(placement) << "\",";
  std::cout << "\"instantiated_hot_bytes\":" << instantiated_hot << ",";
  std::cout << "\"join_path\":\""
            << (flush_distance > 0 ? "flushbehind" : "join_range") << "\",";
  emit_samples(samples);
  std::cout << "\"seconds\":" << std::setprecision(9) << total_sec << ",";
  std::cout << "\"join_mtuples_per_s\":" << (static_cast<double>(n) * c.reps / total_sec / 1e6) << ",";
  std::cout << "\"stream_bandwidth_gbps\":" << (static_cast<double>(c.fact_bytes) * c.reps / total_sec / 1e9) << ",";
  std::cout << "\"probe_cycles_per_access\":" << pt.cycles_per_access << ",";
  std::cout << "\"probe_accesses\":" << pt.accesses << ",";
  std::cout << "\"matches\":" << out.matches << ",";
  std::cout << "\"sum\":" << out.sum << ",";
  std::cout << "\"correct\":" << (ok ? "true" : "false") << ",";
  std::cout << "\"status\":\"" << (ok ? "ok" : "bad_result") << "\"}\n";
  std::cout.flush();
  std::cerr.flush();
#if defined(GEM5) && !defined(GEM5_FS)
  // Complete-join campaigns: tenant ends the sim so stats cover one finished
  // pass, not the victim's leftover chase.  Truncated campaigns never get here.
  std::cerr << "JOIN_M5_EXIT\n";
  std::cerr.flush();
  gem5_exit_now();
#endif
  free_bytes(fact, c.fact_bytes, c.huge2m);
  if (!ok) std::exit(11);
}

template <typename Fn>
double measure_cycles_per_tuple(Fn &&fn, size_t n, int reps, uint64_t *sink) {
  uint64_t total_cycles = 0;
  uint64_t local_sink = 0;
  for (int r = 0; r < reps; ++r) {
    uint64_t t0 = rdtsc();
    local_sink ^= static_cast<uint64_t>(fn());
    uint64_t t1 = rdtsc();
    total_cycles += (t1 - t0);
  }
  *sink ^= local_sink;
  return static_cast<double>(total_cycles) / static_cast<double>(std::max<size_t>(1, n) * std::max(1, reps));
}

void run_breakdown(Config c) {
  std::vector<int> cpus = parse_cpus(c.cpu_list);
  pin_cpu(cpus[0]);
  size_t n = c.fact_bytes / sizeof(Fact);
  c.fact_bytes = n * sizeof(Fact);
  Fact *fact = static_cast<Fact *>(alloc_bytes(c.fact_bytes, c.fact_node, c.huge2m, "fact"));
  std::vector<Entry> table;
  std::vector<int64_t> keys;
  build_table(table, keys, c.hot_bytes, c.seed);
  fill_fact(fact, n, keys, c.hit_rate, c.seed);
  // No prefault_region here.  fill_fact has written every tuple, so every page
  // is already faulted in, and prefault_region MUTATES -- see its definition.
  // Placed here it corrupted exactly one fact key per 4 KiB page.
  if (c.policy == "stream") declare_streaming(fact, c.fact_bytes);
  std::string placement;
  bool placed = check_pages_on_node(fact, c.fact_bytes, c.fact_node, &placement);
  if (!placed) {
    std::cerr << "FATAL: fact placement failed: " << placement << "\n";
    std::exit(10);
  }
  for (int i = 0; i < c.warmups; ++i) {
    warm_table(table);
    (void)stream_tuple_loop(fact, n);
    (void)hash_only_loop(fact, n);
    (void)probe_only_loop(table, fact, n);
    (void)aggregate_only_loop(fact, n);
    (void)join_range(table, fact, 0, n, c.policy, c.pf_distance);
  }
  uint64_t sink = 0;
  double stream_cpt = measure_cycles_per_tuple([&]() { return stream_tuple_loop(fact, n); }, n, c.reps, &sink);
  double hash_cpt = measure_cycles_per_tuple([&]() { return hash_only_loop(fact, n); }, n, c.reps, &sink);
  double probe_cpt = measure_cycles_per_tuple([&]() {
    Result r = probe_only_loop(table, fact, n);
    return r.matches ^ static_cast<uint64_t>(r.sum);
  }, n, c.reps, &sink);
  double aggregate_cpt = measure_cycles_per_tuple([&]() {
    Result r = aggregate_only_loop(fact, n);
    return r.matches ^ static_cast<uint64_t>(r.sum);
  }, n, c.reps, &sink);
  double full_cpt = measure_cycles_per_tuple([&]() {
    Result r = join_range(table, fact, 0, n, c.policy, c.pf_distance);
    return r.matches ^ static_cast<uint64_t>(r.sum);
  }, n, c.reps, &sink);
  emit_json_prefix(c, fact, c.fact_bytes, cpus);
  std::cout << "\"placement\":\"" << json_escape(placement) << "\",";
  std::cout << "\"stream_load_cycles_per_tuple\":" << stream_cpt << ",";
  std::cout << "\"hash_cycles_per_tuple\":" << hash_cpt << ",";
  std::cout << "\"probe_cycles_per_tuple\":" << probe_cpt << ",";
  std::cout << "\"aggregate_cycles_per_tuple\":" << aggregate_cpt << ",";
  std::cout << "\"full_join_cycles_per_tuple\":" << full_cpt << ",";
  std::cout << "\"residual_cycles_per_tuple\":" << (full_cpt - probe_cpt) << ",";
  std::cout << "\"sink\":" << sink << ",";
  std::cout << "\"status\":\"ok\"}\n";
  free_bytes(fact, c.fact_bytes, c.huge2m);
}

void run_probe_workload(Config c) {
  std::vector<int> cpus = parse_cpus(c.cpu_list);
  pin_cpu(cpus[0]);
  size_t n = c.fact_bytes / sizeof(Fact);
  c.fact_bytes = n * sizeof(Fact);
  Fact *fact = static_cast<Fact *>(alloc_bytes(c.fact_bytes, c.fact_node, c.huge2m, "fact"));
  std::vector<Entry> table;
  std::vector<int64_t> keys;
  build_table(table, keys, c.hot_bytes, c.seed);
  fill_fact(fact, n, keys, c.hit_rate, c.seed);
  // No prefault_region here.  fill_fact has written every tuple, so every page
  // is already faulted in, and prefault_region MUTATES -- see its definition.
  // Placed here it corrupted exactly one fact key per 4 KiB page.
  if (c.policy == "stream") declare_streaming(fact, c.fact_bytes);
  std::string placement;
  bool placed = check_pages_on_node(fact, c.fact_bytes, c.fact_node, &placement);
  if (!placed) {
    std::cerr << "FATAL: fact placement failed: " << placement << "\n";
    std::exit(10);
  }
  for (int i = 0; i < c.warmups; ++i) {
    warm_table(table);
    (void)probe_only_loop(table, fact, n);
  }
  std::vector<double> samples;
  samples.reserve(c.reps);
  uint64_t total_cycles = 0;
  double total_sec = 0.0;
  Result total;
  for (int r = 0; r < c.reps; ++r) {
    uint64_t c0 = rdtsc();
    auto t0 = std::chrono::steady_clock::now();
    Result rr = probe_only_loop(table, fact, n);
    double sec = seconds_since(t0);
    uint64_t c1 = rdtsc();
    total_cycles += c1 - c0;
    total_sec += sec;
    samples.push_back(static_cast<double>(n) / sec / 1e6);
    total.matches += rr.matches;
    total.sum += rr.sum;
  }
  emit_json_prefix(c, fact, c.fact_bytes, cpus);
  std::cout << "\"placement\":\"" << json_escape(placement) << "\",";
  emit_samples(samples);
  std::cout << "\"seconds\":" << std::setprecision(9) << total_sec << ",";
  std::cout << "\"probe_mtuples_per_s\":" << (static_cast<double>(n) * c.reps / total_sec / 1e6) << ",";
  std::cout << "\"cycles_per_access\":" << (static_cast<double>(total_cycles) /
              static_cast<double>(std::max<size_t>(1, n) * std::max(1, c.reps))) << ",";
  std::cout << "\"matches\":" << total.matches << ",";
  std::cout << "\"sum\":" << total.sum << ",";
  std::cout << "\"status\":\"ok\"}\n";
  free_bytes(fact, c.fact_bytes, c.huge2m);
}

// Bounded MPMC morsel queue for --mode split. N_s scan threads copy fact-array morsels
// (the CXL read) into pre-allocated slots; N_p probe threads pop filled slots and run
// the hash-table probe against a private, already-copied batch, so probe threads never
// touch the CXL fact region directly. Locking is per-morsel (batch of --morsel tuples),
// not per-tuple, so mutex overhead is negligible relative to the copy/probe work.
class MorselQueue {
 public:
  MorselQueue(size_t depth, size_t morsel_elems) : slots_(depth) {
    for (auto &s : slots_) s.data.resize(morsel_elems);
    reset();
  }

  void reset() {
    std::lock_guard<std::mutex> lk(mu_);
    free_slots_.clear();
    filled_slots_.clear();
    for (size_t i = 0; i < slots_.size(); ++i) free_slots_.push_back(static_cast<int>(i));
    scanners_remaining_ = 0;
  }

  void set_scanner_count(int n) {
    std::lock_guard<std::mutex> lk(mu_);
    scanners_remaining_ = n;
  }

  template <typename FillFn>
  void produce(FillFn &&fill) {
    std::unique_lock<std::mutex> lk(mu_);
    free_cv_.wait(lk, [&] { return !free_slots_.empty(); });
    int slot = free_slots_.back();
    free_slots_.pop_back();
    lk.unlock();
    size_t count = fill(slots_[slot].data);
    slots_[slot].count = count;
    lk.lock();
    filled_slots_.push_back(slot);
    lk.unlock();
    filled_cv_.notify_one();
  }

  void producer_done() {
    std::lock_guard<std::mutex> lk(mu_);
    if (--scanners_remaining_ == 0) filled_cv_.notify_all();
  }

  // Returns false once all scanners are done and no filled morsels remain.
  template <typename ConsumeFn>
  bool consume(ConsumeFn &&consume_fn) {
    std::unique_lock<std::mutex> lk(mu_);
    filled_cv_.wait(lk, [&] { return !filled_slots_.empty() || scanners_remaining_ == 0; });
    if (filled_slots_.empty()) return false;
    int slot = filled_slots_.front();
    filled_slots_.pop_front();
    lk.unlock();
    consume_fn(slots_[slot].data, slots_[slot].count);
    lk.lock();
    free_slots_.push_back(slot);
    lk.unlock();
    free_cv_.notify_one();
    return true;
  }

 private:
  struct Slot {
    std::vector<Fact> data;
    size_t count = 0;
  };
  std::vector<Slot> slots_;
  std::vector<int> free_slots_;
  std::deque<int> filled_slots_;
  std::mutex mu_;
  std::condition_variable free_cv_;
  std::condition_variable filled_cv_;
  int scanners_remaining_ = 0;
};

void run_split(Config c) {
  if (c.policy == "cat") {
    std::cerr << "deferred: --policy cat needs resctrl control-group privilege\n";
    std::exit(20);
  }
  int n_scan = c.scan_threads > 0 ? c.scan_threads : std::max(1, c.threads / 2);
  int n_probe = c.probe_threads > 0 ? c.probe_threads : (c.threads - n_scan);
  if (n_scan <= 0 || n_probe <= 0) {
    std::cerr << "split mode requires --scan-threads>=1 and --probe-threads>=1\n";
    std::exit(2);
  }
  c.threads = n_scan + n_probe;
  std::vector<int> cpus = parse_cpus(c.cpu_list);
  if (static_cast<int>(cpus.size()) < c.threads) {
    std::cerr << "not enough CPUs in --cpu-list\n";
    std::exit(2);
  }
  size_t n = c.fact_bytes / sizeof(Fact);
  c.fact_bytes = n * sizeof(Fact);
  Fact *fact = static_cast<Fact *>(alloc_bytes(c.fact_bytes, c.fact_node, c.huge2m, "fact"));
  std::vector<Entry> table;
  std::vector<int64_t> keys;
  build_table(table, keys, c.hot_bytes, c.seed);
  fill_fact(fact, n, keys, c.hit_rate, c.seed);
  // No prefault_region here.  fill_fact has written every tuple, so every page
  // is already faulted in, and prefault_region MUTATES -- see its definition.
  // Placed here it corrupted exactly one fact key per 4 KiB page.
  if (c.policy == "stream") declare_streaming(fact, c.fact_bytes);
  std::string placement;
  bool placed = check_pages_on_node(fact, c.fact_bytes, c.fact_node, &placement);
  if (!placed) {
    std::cerr << "FATAL: fact placement failed: " << placement << "\n";
    std::exit(10);
  }
  for (int i = 0; i < c.warmups; ++i) warm_table(table);

  size_t morsel_elems = static_cast<size_t>(c.morsel);
  size_t qdepth = std::max<uint64_t>(2, c.queue_depth);
  MorselQueue queue(qdepth, morsel_elems);
  bool want_hash = c.result_hash;

  std::atomic<size_t> next{0};
  std::vector<Result> partial(n_probe);
  std::vector<uint64_t> scan_cycles(n_scan, 0), scan_tuples(n_scan, 0);
  // probe_compute_cycles times only the probe loop itself (matches the original
  // metric). probe_wall_cycles wraps the entire consume() call, including any time
  // spent blocked waiting for a filled queue slot -- this is the metric comparable to
  // fused mode's active_cycles_per_access, since join_range never waits on anything
  // internal and so is implicitly "wall" already. Reporting both avoids silently
  // picking one and lets a reader see the wait-time component directly.
  std::vector<uint64_t> probe_compute_cycles(n_probe, 0), probe_wall_cycles(n_probe, 0);
  std::vector<uint64_t> probe_tuples(n_probe, 0);
  std::vector<uint64_t> probe_xhash(n_probe, 0);

  bool use_memcpy = c.scan_memcpy;
  auto scan_worker = [&](int tid) {
    pin_cpu(cpus[tid]);
    while (true) {
      size_t begin = next.fetch_add(morsel_elems);
      if (begin >= n) break;
      size_t end = std::min(n, begin + morsel_elems);
      uint64_t c0 = rdtsc();
      queue.produce([&](std::vector<Fact> &buf) -> size_t {
        if (use_memcpy) {
          std::memcpy(buf.data(), &fact[begin], (end - begin) * sizeof(Fact));
        } else {
          for (size_t i = begin; i < end; ++i) buf[i - begin] = fact[i];
        }
        return end - begin;
      });
      uint64_t c1 = rdtsc();
      scan_cycles[tid] += c1 - c0;
      scan_tuples[tid] += end - begin;
    }
    queue.producer_done();
  };

  auto probe_worker = [&](int pid) {
    pin_cpu(cpus[n_scan + pid]);
    while (true) {
      uint64_t w0 = rdtsc();
      bool got = queue.consume([&](std::vector<Fact> &buf, size_t count) {
        uint64_t c0 = rdtsc();
        Result rr;
        uint64_t h = 0;
        for (size_t i = 0; i < count; ++i) {
          int64_t payload = 0;
          if (probe(table, buf[i].fk, &payload)) {
            rr.matches++;
            rr.sum += buf[i].measure;
            if (want_hash) {
              h ^= hash64(static_cast<uint64_t>(buf[i].fk) * 0x9E3779B97F4A7C15ull ^ static_cast<uint64_t>(payload));
            }
          }
        }
        uint64_t c1 = rdtsc();
        probe_compute_cycles[pid] += c1 - c0;
        probe_tuples[pid] += count;
        partial[pid].matches += rr.matches;
        partial[pid].sum += rr.sum;
        probe_xhash[pid] ^= h;
      });
      uint64_t w1 = rdtsc();
      if (!got) break;
      probe_wall_cycles[pid] += w1 - w0;
    }
  };

  std::vector<double> samples;
  samples.reserve(c.reps);
  double total_sec = 0.0;
  Result last_out;
  uint64_t last_xhash = 0;
  uint64_t all_scan_cycles = 0, all_scan_tuples = 0;
  uint64_t all_probe_compute_cycles = 0, all_probe_wall_cycles = 0, all_probe_tuples = 0;
  for (int rep = 0; rep < c.reps; ++rep) {
    next.store(0);
    queue.reset();
    queue.set_scanner_count(n_scan);
    std::fill(partial.begin(), partial.end(), Result{});
    std::fill(scan_cycles.begin(), scan_cycles.end(), 0);
    std::fill(scan_tuples.begin(), scan_tuples.end(), 0);
    std::fill(probe_compute_cycles.begin(), probe_compute_cycles.end(), 0);
    std::fill(probe_wall_cycles.begin(), probe_wall_cycles.end(), 0);
    std::fill(probe_tuples.begin(), probe_tuples.end(), 0);
    std::fill(probe_xhash.begin(), probe_xhash.end(), 0);
    std::vector<std::thread> th;
    auto t0 = std::chrono::steady_clock::now();
    for (int t = 0; t < n_scan; ++t) th.emplace_back(scan_worker, t);
    for (int t = 0; t < n_probe; ++t) th.emplace_back(probe_worker, t);
    for (auto &x : th) x.join();
    double sec = seconds_since(t0);
    total_sec += sec;
    samples.push_back(static_cast<double>(n) / sec / 1e6);
    all_scan_cycles += std::accumulate(scan_cycles.begin(), scan_cycles.end(), uint64_t{0});
    all_scan_tuples += std::accumulate(scan_tuples.begin(), scan_tuples.end(), uint64_t{0});
    all_probe_compute_cycles += std::accumulate(probe_compute_cycles.begin(), probe_compute_cycles.end(), uint64_t{0});
    all_probe_wall_cycles += std::accumulate(probe_wall_cycles.begin(), probe_wall_cycles.end(), uint64_t{0});
    all_probe_tuples += std::accumulate(probe_tuples.begin(), probe_tuples.end(), uint64_t{0});
    last_out = {};
    last_xhash = 0;
    for (auto &p : partial) { last_out.matches += p.matches; last_out.sum += p.sum; }
    for (auto x : probe_xhash) last_xhash ^= x;
  }

  std::vector<std::string> roles(c.threads);
  for (int i = 0; i < n_scan; ++i) roles[i] = "scan";
  for (int i = 0; i < n_probe; ++i) roles[n_scan + i] = "probe";

  emit_json_prefix(c, fact, c.fact_bytes, cpus, roles);
  std::cout << "\"placement\":\"" << json_escape(placement) << "\",";
  std::cout << "\"scan_threads\":" << n_scan << ",";
  std::cout << "\"probe_threads\":" << n_probe << ",";
  std::cout << "\"queue_depth\":" << qdepth << ",";
  std::cout << "\"morsel_elems\":" << morsel_elems << ",";
  std::cout << "\"scan_memcpy\":" << (use_memcpy ? "true" : "false") << ",";
  emit_samples(samples);
  std::cout << "\"seconds\":" << std::setprecision(9) << total_sec << ",";
  std::cout << "\"join_mtuples_per_s\":" << (static_cast<double>(n) * c.reps / total_sec / 1e6) << ",";
  std::cout << "\"stream_bandwidth_gbps\":" << (static_cast<double>(c.fact_bytes) * c.reps / total_sec / 1e9) << ",";
  std::cout << "\"scan_cycles_per_access\":" << (all_scan_tuples ? static_cast<double>(all_scan_cycles) / all_scan_tuples : 0.0) << ",";
  std::cout << "\"active_cycles_per_access\":" << (all_probe_tuples ? static_cast<double>(all_probe_wall_cycles) / all_probe_tuples : 0.0) << ",";
  std::cout << "\"probe_compute_cycles_per_access\":" << (all_probe_tuples ? static_cast<double>(all_probe_compute_cycles) / all_probe_tuples : 0.0) << ",";
  std::cout << "\"matches_last_rep\":" << last_out.matches << ",";
  std::cout << "\"sum_last_rep\":" << last_out.sum << ",";
  std::cout << "\"result_hash\":" << last_xhash << ",";
  std::cout << "\"status\":\"ok\"}\n";
  free_bytes(fact, c.fact_bytes, c.huge2m);
}

void run_morsel(Config c) {
  if (c.policy == "cat") {
    std::cerr << "deferred: --policy cat needs resctrl control-group privilege\n";
    std::exit(20);
  }
  std::vector<int> cpus = parse_cpus(c.cpu_list);
  if (static_cast<int>(cpus.size()) < c.threads) {
    std::cerr << "not enough CPUs in --cpu-list\n";
    std::exit(2);
  }
  size_t n = c.fact_bytes / sizeof(Fact);
  c.fact_bytes = n * sizeof(Fact);
  // --no-stream: same threading/counting structure and same code path (join_range_local
  // is a copy of join_range) as the real fused path, but the "fact" data is a small
  // buffer that stays resident in cache, so there is no real stream. Used only to check
  // how much of the fused-vs-quiescent gap is a code-path difference against
  // run_hot_probe's separate loop, versus real interference. join_range/run_morsel's
  // normal path is otherwise untouched.
  size_t local_n = n;
  if (c.no_stream) {
    // Must stay a power of 2 (join_range_local masks rather than divides); round
    // down to the largest power of 2 not exceeding min(n, 65536).
    size_t cap = std::min<size_t>(n, 65536);
    size_t pow2 = 1;
    while (pow2 * 2 <= cap) pow2 *= 2;
    local_n = std::max<size_t>(1, pow2);
  }
  uint64_t phys_bytes = local_n * sizeof(Fact);
  int alloc_node = c.no_stream ? c.hot_node : c.fact_node;
  Fact *fact = static_cast<Fact *>(alloc_bytes(phys_bytes, alloc_node, c.huge2m, "fact"));
  std::vector<Entry> table;
  std::vector<int64_t> keys;
  build_table(table, keys, c.hot_bytes, c.seed);
  SmapsInfo table_smi = smaps_info(table.data());
  std::cerr << "HOT_TABLE"
            << " pid=" << getpid()
            << " base=0x" << std::hex << reinterpret_cast<uintptr_t>(table.data()) << std::dec
            << " bytes=" << (table.size() * sizeof(Entry))
            << " entries=" << table.size()
            << " anon_huge_kb=" << table_smi.anon_huge_kb
            << " kernel_page_kb=" << table_smi.kernel_page_kb
            << " mmu_page_kb=" << table_smi.mmu_page_kb
            << "\n";
  // No prefault_region here.  fill_fact has written every tuple, so every page
  // is already faulted in, and prefault_region MUTATES -- see its definition.
  // This is the site that corrupted one key per page in every morsel campaign.
  fill_fact(fact, local_n, keys, c.hit_rate, c.seed);
  if (c.policy == "stream") declare_streaming(fact, phys_bytes);
  std::string placement;
  bool placed = check_pages_on_node(fact, phys_bytes, alloc_node, &placement);
  if (!placed) {
    std::cerr << "FATAL: fact placement failed: " << placement << "\n";
    std::exit(10);
  }
  for (int i = 0; i < c.warmups; ++i) warm_table(table);
  std::cerr << "HOT_TABLE_WARMED"
            << " pid=" << getpid()
            << " warmups=" << c.warmups
            << " pre_measure_sleep_s=" << std::setprecision(9) << c.pre_measure_sleep_s
            << "\n";
  if (c.pre_measure_sleep_s > 0.0) {
    std::this_thread::sleep_for(std::chrono::duration<double>(c.pre_measure_sleep_s));
  }
  std::atomic<size_t> next{0};
  std::vector<Result> partial(c.threads);
  std::vector<uint64_t> thread_cycles(c.threads, 0);
  std::vector<uint64_t> thread_tuples(c.threads, 0);
  std::vector<uint64_t> thread_xhash(c.threads, 0);
  bool want_hash = c.result_hash;
  bool no_stream = c.no_stream;
  size_t flush_distance = c.flush_distance;
  int probe_batch = c.probe_batch;
  // Silently ignoring one of two mutually exclusive flags is how an arm gets
  // mislabelled. join_range_hashed has no batched twin, so refuse the pair.
  if (want_hash && probe_batch > 1) {
    std::cerr << "FATAL: --result-hash and --probe-batch>1 are mutually exclusive "
                 "(join_range_hashed has no batched variant)\n";
    std::exit(11);
  }
  if (no_stream && probe_batch > 1) {
    std::cerr << "FATAL: --no-stream and --probe-batch>1 are mutually exclusive\n";
    std::exit(11);
  }
  auto worker = [&](int tid) {
    pin_cpu(cpus[tid]);
    while (true) {
      size_t begin = next.fetch_add(c.morsel);
      if (begin >= n) break;
      size_t end = std::min(n, begin + static_cast<size_t>(c.morsel));
      uint64_t c0 = rdtsc();
      Result rr;
      if (no_stream) {
        rr = join_range_local(table, fact, local_n, begin, end, c.policy, c.pf_distance);
      } else if (flush_distance > 0) {
        rr = join_range_flushbehind(table, fact, begin, end, c.policy, c.pf_distance, flush_distance);
      } else if (want_hash) {
        rr = join_range_hashed(table, fact, begin, end, c.policy, c.pf_distance, &thread_xhash[tid]);
      } else if (probe_batch > 1) {
        rr = join_range_batched(table, fact, begin, end, c.policy, c.pf_distance, probe_batch);
      } else {
        rr = join_range(table, fact, begin, end, c.policy, c.pf_distance);
      }
      uint64_t c1 = rdtsc();
      thread_cycles[tid] += c1 - c0;
      thread_tuples[tid] += end - begin;
      partial[tid].matches += rr.matches;
      partial[tid].sum += rr.sum;
    }
  };
  std::vector<double> samples;
  samples.reserve(c.reps);
  double total_sec = 0.0;
  Result last_out;
  uint64_t last_xhash = 0;
  uint64_t all_active_cycles = 0;
  uint64_t all_active_tuples = 0;
  for (int rep = 0; rep < c.reps; ++rep) {
    next.store(0);
    std::fill(partial.begin(), partial.end(), Result{});
    std::fill(thread_cycles.begin(), thread_cycles.end(), 0);
    std::fill(thread_tuples.begin(), thread_tuples.end(), 0);
    std::fill(thread_xhash.begin(), thread_xhash.end(), 0);
    std::vector<std::thread> th;
    auto t0 = std::chrono::steady_clock::now();
    for (int t = 0; t < c.threads; ++t) th.emplace_back(worker, t);
    for (auto &x : th) x.join();
    double sec = seconds_since(t0);
    total_sec += sec;
    samples.push_back(static_cast<double>(n) / sec / 1e6);
    all_active_cycles += std::accumulate(thread_cycles.begin(), thread_cycles.end(), uint64_t{0});
    all_active_tuples += std::accumulate(thread_tuples.begin(), thread_tuples.end(), uint64_t{0});
    last_out = {};
    last_xhash = 0;
    for (auto &p : partial) { last_out.matches += p.matches; last_out.sum += p.sum; }
    for (auto x : thread_xhash) last_xhash ^= x;
  }
  emit_json_prefix(c, fact, phys_bytes, cpus);
  std::cout << "\"placement\":\"" << json_escape(placement) << "\",";
  std::cout << "\"no_stream\":" << (no_stream ? "true" : "false") << ",";
  std::cout << "\"local_n\":" << local_n << ",";
  std::cout << "\"pre_measure_sleep_s\":" << std::setprecision(9) << c.pre_measure_sleep_s << ",";
  std::cout << "\"table_anon_huge_kb\":" << table_smi.anon_huge_kb << ",";
  std::cout << "\"table_kernel_page_kb\":" << table_smi.kernel_page_kb << ",";
  std::cout << "\"table_mmu_page_kb\":" << table_smi.mmu_page_kb << ",";
  emit_samples(samples);
  std::cout << "\"seconds\":" << std::setprecision(9) << total_sec << ",";
  std::cout << "\"join_mtuples_per_s\":" << (static_cast<double>(n) * c.reps / total_sec / 1e6) << ",";
  std::cout << "\"stream_bandwidth_gbps\":" << (no_stream ? 0.0 : (static_cast<double>(c.fact_bytes) * c.reps / total_sec / 1e9)) << ",";
  std::cout << "\"active_cycles_per_access\":" << (all_active_tuples ? static_cast<double>(all_active_cycles) / all_active_tuples : 0.0) << ",";
  std::cout << "\"matches_last_rep\":" << last_out.matches << ",";
  std::cout << "\"sum_last_rep\":" << last_out.sum << ",";
  std::cout << "\"result_hash\":" << last_xhash << ",";
  std::cout << "\"status\":\"ok\"}\n";
  free_bytes(fact, phys_bytes, c.huge2m);
}

void run_hot_probe(Config c) {
  std::vector<int> cpus = parse_cpus(c.cpu_list);
  if (static_cast<int>(cpus.size()) < c.threads) {
    std::cerr << "not enough CPUs in --cpu-list\n";
    std::exit(2);
  }
  std::vector<Entry> table;
  std::vector<int64_t> keys;
  build_table(table, keys, c.hot_bytes, c.seed);
  warm_table(table);
  size_t total = std::max<uint64_t>(1, c.fact_bytes / sizeof(Fact));
  std::vector<double> samples;
  samples.reserve(c.reps);
  double total_sec = 0.0;
  std::atomic<uint64_t> sink{0};
  std::vector<uint64_t> thread_cycles(c.threads, 0);
  std::vector<uint64_t> thread_tuples(c.threads, 0);
  uint64_t all_active_cycles = 0;
  uint64_t all_active_tuples = 0;
  for (int rep = 0; rep < c.reps; ++rep) {
    std::atomic<size_t> next{0};
    std::fill(thread_cycles.begin(), thread_cycles.end(), 0);
    std::fill(thread_tuples.begin(), thread_tuples.end(), 0);
    auto worker = [&](int tid) {
      pin_cpu(cpus[tid]);
      uint64_t local = 0;
      while (true) {
        size_t begin = next.fetch_add(c.morsel);
        if (begin >= total) break;
        size_t end = std::min(total, begin + static_cast<size_t>(c.morsel));
        uint64_t c0 = rdtsc();
        for (size_t i = begin; i < end; ++i) {
          int64_t payload = 0;
          probe(table, keys[i % keys.size()], &payload);
          local += static_cast<uint64_t>(payload);
        }
        uint64_t c1 = rdtsc();
        thread_cycles[tid] += c1 - c0;
        thread_tuples[tid] += end - begin;
      }
      sink.fetch_add(local, std::memory_order_relaxed);
    };
    std::vector<std::thread> th;
    auto t0 = std::chrono::steady_clock::now();
    for (int t = 0; t < c.threads; ++t) th.emplace_back(worker, t);
    for (auto &x : th) x.join();
    double sec = seconds_since(t0);
    total_sec += sec;
    samples.push_back(static_cast<double>(total) / sec / 1e6);
    all_active_cycles += std::accumulate(thread_cycles.begin(), thread_cycles.end(), uint64_t{0});
    all_active_tuples += std::accumulate(thread_tuples.begin(), thread_tuples.end(), uint64_t{0});
  }
  emit_json_prefix(c, nullptr, 0, cpus);
  emit_samples(samples);
  std::cout << "\"seconds\":" << std::setprecision(9) << total_sec << ",";
  std::cout << "\"probe_mops_per_s\":" << (static_cast<double>(total) * c.reps / total_sec / 1e6) << ",";
  std::cout << "\"active_cycles_per_access\":" << (all_active_tuples ? static_cast<double>(all_active_cycles) / all_active_tuples : 0.0) << ",";
  std::cout << "\"sink\":" << sink.load(std::memory_order_relaxed) << ",";
  std::cout << "\"status\":\"ok\"}\n";
}

void self_test_reference() {
  uint64_t fact_bytes = 8ull << 20;
  size_t n = fact_bytes / sizeof(Fact);
  std::vector<Fact> fact(n);
  std::vector<Entry> table;
  std::vector<int64_t> keys;
  build_table(table, keys, 2ull << 20, 1234);
  fill_fact(fact.data(), n, keys, 0.5, 5678);
  Result a = scalar_join(table, fact.data(), n);
  Result b = join_range(table, fact.data(), 0, n, "wb", 0);
  Result c = join_range(table, fact.data(), 0, n, "nta", 32);
  if (a.matches != b.matches || a.sum != b.sum || a.matches != c.matches || a.sum != c.sum) {
    std::cerr << "reference test failed\n";
    std::exit(11);
  }
  std::cout << "{\"self_test\":\"reference\",\"status\":\"ok\",\"matches\":" << a.matches
            << ",\"sum\":" << a.sum << "}\n";
}

void self_test_numa(Config c) {
  std::vector<int> cpus = parse_cpus(c.cpu_list);
  pin_cpu(cpus[0]);
  Fact *fact = static_cast<Fact *>(alloc_bytes(c.fact_bytes, c.fact_node, c.huge2m, "fact"));
  size_t n = c.fact_bytes / sizeof(Fact);
  for (size_t i = 0; i < n; ++i) fact[i] = Fact{static_cast<int64_t>(i), static_cast<int64_t>(i)};
  std::string detail;
  bool ok = check_pages_on_node(fact, c.fact_bytes, c.fact_node, &detail);
  std::cout << "{\"self_test\":\"numa\",\"status\":\"" << (ok ? "ok" : "failed")
            << "\",\"detail\":\"" << json_escape(detail) << "\"}\n";
  free_bytes(fact, c.fact_bytes, c.huge2m);
  if (!ok) std::exit(10);
}

Config parse(int argc, char **argv) {
  Config c;
  for (int i = 1; i < argc; ++i) {
    std::string a = argv[i];
    auto need = [&](const char *name) -> std::string {
      if (i + 1 >= argc) { std::cerr << "missing value for " << name << "\n"; std::exit(2); }
      return argv[++i];
    };
    if (a == "--mode") c.mode = need("--mode");
    else if (a == "--probe-batch") c.probe_batch = std::stoi(need("--probe-batch"));
    else if (a == "--policy") c.policy = need("--policy");
    else if (a == "--self-test") c.self_test = need("--self-test");
    else if (a == "--fact-bytes") c.fact_bytes = parse_size(need("--fact-bytes"));
    else if (a == "--hot-bytes") c.hot_bytes = parse_size(need("--hot-bytes"));
    else if (a == "--fact-node") c.fact_node = std::stoi(need("--fact-node"));
    else if (a == "--hot-node") c.hot_node = std::stoi(need("--hot-node"));
    else if (a == "--threads") c.threads = std::stoi(need("--threads"));
    else if (a == "--reps") c.reps = std::stoi(need("--reps"));
    else if (a == "--warmups") c.warmups = std::stoi(need("--warmups"));
    else if (a == "--iterations") c.iterations = std::stoull(need("--iterations"));
    else if (a == "--victim-bytes") c.victim_bytes = parse_size(need("--victim-bytes"));
    else if (a == "--vector") c.vector = std::stoi(need("--vector"));
    else if (a == "--pf-distance") c.pf_distance = std::stoi(need("--pf-distance"));
    else if (a == "--stream-count") c.stream_count = std::stoi(need("--stream-count"));
    else if (a == "--seed") c.seed = std::stoull(need("--seed"));
    else if (a == "--hit-rate") c.hit_rate = std::stod(need("--hit-rate"));
    else if (a == "--morsel") c.morsel = parse_size(need("--morsel"));
    else if (a == "--cpu-list") c.cpu_list = need("--cpu-list");
    else if (a == "--json") c.json = true;
    else if (a == "--check") c.check = true;
    else if (a == "--huge2m") c.huge2m = true;
    else if (a == "--scan-threads") c.scan_threads = std::stoi(need("--scan-threads"));
    else if (a == "--probe-threads") c.probe_threads = std::stoi(need("--probe-threads"));
    else if (a == "--queue-depth") c.queue_depth = std::stoull(need("--queue-depth"));
    else if (a == "--result-hash") c.result_hash = true;
    else if (a == "--scan-memcpy") c.scan_memcpy = true;
    else if (a == "--no-stream") c.no_stream = true;
    else if (a == "--window-brackets") c.window_brackets = true;
    else if (a == "--flush-distance") c.flush_distance = static_cast<size_t>(std::stoull(need("--flush-distance")));
    else if (a == "--line-stride") c.line_stride = true;
    else if (a == "--declare") {
      std::string v = need("--declare");
      if (v == "m5op") g_declare = DeclareVia::M5OP;
      else if (v == "mprotect") g_declare = DeclareVia::MPROTECT;
      else { std::cerr << "FATAL: --declare takes m5op or mprotect, got " << v << "\n"; std::exit(2); }
    }
    else if (a == "--pre-measure-sleep-s") c.pre_measure_sleep_s = std::stod(need("--pre-measure-sleep-s"));
    else {
      std::cerr << "unknown argument: " << a << "\n";
      std::exit(2);
    }
  }
  return c;
}

}  // namespace

int main(int argc, char **argv) {
  Config c = parse(argc, argv);
  if (c.self_test == "reference") {
    self_test_reference();
    return 0;
  }
  if (c.self_test == "numa") {
    self_test_numa(c);
    return 0;
  }
  if (c.mode == "stream-smoke" || c.mode == "stream-nta") run_stream(c);
  else if (c.mode == "fs-e2e-calibrate") run_fs_e2e_calibrate(c);
  else if (c.mode == "fs-e2e-join") run_fs_e2e_join(c);
  else if (c.mode == "h2-admission") {
#ifdef GEM5_FS
    run_h2_admission(c);
#else
    std::cerr << "FATAL: h2-admission requires the GEM5_FS binary\n";
    return 2;
#endif
  }
  else if (c.mode == "latency") run_latency(c);
  else if (c.mode == "single") run_single(c);
  else if (c.mode == "breakdown") run_breakdown(c);
  else if (c.mode == "probe-workload") run_probe_workload(c);
  else if (c.mode == "morsel") run_morsel(c);
  else if (c.mode == "split") run_split(c);
  else if (c.mode == "hot-probe") run_hot_probe(c);
  else {
    std::cerr << "unknown mode: " << c.mode << "\n";
    return 2;
  }
  return 0;
}
