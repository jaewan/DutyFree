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
#include <unistd.h>
#include <x86intrin.h>

#ifndef MADV_HUGEPAGE
#define MADV_HUGEPAGE 14
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
#ifdef GEM5
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
static inline void gem5_set_streaming(void *addr, long size) {
    __asm__ volatile(".byte 0x0f, 0x04, 0x55, 0x00" : : "D"(addr), "S"(size));
}
#else
static inline void gem5_set_streaming(void *, long) {}
#endif

void *alloc_bytes(uint64_t bytes, int node, bool huge2m, const char *name) {
  void *p = nullptr;
#ifdef GEM5
  (void)node;
  (void)name;
  int flags = MAP_PRIVATE | MAP_ANONYMOUS;
  p = mmap(nullptr, bytes, PROT_READ | PROT_WRITE, flags, -1, 0);
  if (p == MAP_FAILED) p = nullptr;
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
#ifdef GEM5
  munmap(p, bytes);
#else
  (void)huge2m;
  munmap(p, bytes);
#endif
}

bool check_pages_on_node(void *p, uint64_t bytes, int node, std::string *detail) {
#ifdef GEM5
  (void)p; (void)bytes; (void)node;
  if (detail) *detail = "GEM5 no NUMA placement check";
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

void prefault_region(void *p, uint64_t bytes) {
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
  uint64_t threshold = static_cast<uint64_t>(hit_rate * static_cast<double>(UINT64_MAX));
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
  std::cout << "\"policy\":\"" << json_escape(c.policy) << "\",";
  std::cout << "\"fact_bytes\":" << fact_bytes << ",";
  std::cout << "\"hot_bytes\":" << c.hot_bytes << ",";
  std::cout << "\"fact_node\":" << c.fact_node << ",";
  std::cout << "\"hot_node\":" << c.hot_node << ",";
  std::cout << "\"threads\":" << c.threads << ",";
  std::cout << "\"pf_distance\":" << c.pf_distance << ",";
  std::cout << "\"stream_count\":" << c.stream_count << ",";
  std::cout << "\"seed\":" << c.seed << ",";
  std::cout << "\"hit_rate\":" << c.hit_rate << ",";
  uintptr_t base = reinterpret_cast<uintptr_t>(fact);
  std::cout << "\"fact_base\":\"0x" << std::hex << base << "\",";
  std::cout << "\"fact_end\":\"0x" << (base + fact_bytes) << std::dec << "\",";
  std::cout << "\"thread_mapping\":" << cpu_mapping_json(cpus, c.threads, roles) << ",";
}

void run_stream(Config c) {
  std::vector<int> cpus = parse_cpus(c.cpu_list);
  pin_cpu(cpus[0]);
  size_t n = c.fact_bytes / sizeof(Fact);
  c.fact_bytes = n * sizeof(Fact);
  Fact *fact = static_cast<Fact *>(alloc_bytes(c.fact_bytes, c.fact_node, c.huge2m, "fact"));
  std::vector<Entry> table;
  std::vector<int64_t> keys;
  build_table(table, keys, 1ull << 20, c.seed);
  fill_fact(fact, n, keys, c.hit_rate, c.seed);
  auto pf0 = std::chrono::steady_clock::now();
  prefault_region(fact, c.fact_bytes);
  if (c.policy == "stream") gem5_set_streaming(fact, (long)c.fact_bytes);
  double prefault_sec = seconds_since(pf0);
  std::string placement;
  bool placed = check_pages_on_node(fact, c.fact_bytes, c.fact_node, &placement);
  if (!placed) {
    std::cerr << "FATAL: fact placement failed: " << placement << "\n";
    std::exit(10);
  }
  uint64_t checksum = 0;
  for (int i = 0; i < c.warmups; ++i) checksum ^= stream_read(fact, n, c.policy, c.pf_distance, c.stream_count);
  struct rusage ru_before {};
  struct rusage ru_after {};
  getrusage(RUSAGE_SELF, &ru_before);
  std::vector<double> samples;
  samples.reserve(c.reps);
  double total_sec = 0.0;
  for (int r = 0; r < c.reps; ++r) {
    auto t0 = std::chrono::steady_clock::now();
    checksum ^= stream_read(fact, n, c.policy, c.pf_distance, c.stream_count);
    double sec = seconds_since(t0);
    total_sec += sec;
    samples.push_back(static_cast<double>(c.fact_bytes) / sec / 1e9);
  }
  getrusage(RUSAGE_SELF, &ru_after);
  double bytes = static_cast<double>(c.fact_bytes) * c.reps;
  SmapsInfo smi = smaps_info(fact);
  emit_json_prefix(c, fact, c.fact_bytes, cpus);
  std::cout << "\"placement\":\"" << json_escape(placement) << "\",";
  std::cout << "\"prefault_seconds\":" << std::setprecision(9) << prefault_sec << ",";
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
    std::cerr << "warning: native --policy stream aliases wb; gem5-only tag is unavailable\n";
    c.policy = "wb";
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
  prefault_region(fact, c.fact_bytes);
  if (c.policy == "stream") gem5_set_streaming(fact, (long)c.fact_bytes);
  std::string placement;
  bool placed = check_pages_on_node(fact, c.fact_bytes, c.fact_node, &placement);
  if (!placed) {
    std::cerr << "FATAL: fact placement failed: " << placement << "\n";
    std::exit(10);
  }
  Result ref;
  if (c.check) ref = scalar_join(table, fact, n);
  Result out;
  for (int i = 0; i < c.warmups; ++i) {
    warm_table(table);
    out = join_range(table, fact, 0, n, c.policy, c.pf_distance);
  }
  warm_table(table);
  ProbeTiming pt = probe_timing(table, keys, std::min<size_t>(keys.size(), 1 << 20));
  std::vector<double> samples;
  samples.reserve(c.reps);
  double total_sec = 0.0;
  out = {};
  for (int r = 0; r < c.reps; ++r) {
    auto t0 = std::chrono::steady_clock::now();
    Result rr = join_range(table, fact, 0, n, c.policy, c.pf_distance);
    double sec = seconds_since(t0);
    total_sec += sec;
    samples.push_back(static_cast<double>(n) / sec / 1e6);
    out.matches += rr.matches;
    out.sum += rr.sum;
  }
  bool ok = !c.check || (out.matches == ref.matches * static_cast<uint64_t>(c.reps) &&
                         out.sum == ref.sum * static_cast<int64_t>(c.reps));
  emit_json_prefix(c, fact, c.fact_bytes, cpus);
  std::cout << "\"placement\":\"" << json_escape(placement) << "\",";
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
  prefault_region(fact, c.fact_bytes);
  if (c.policy == "stream") gem5_set_streaming(fact, (long)c.fact_bytes);
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
  prefault_region(fact, c.fact_bytes);
  if (c.policy == "stream") gem5_set_streaming(fact, (long)c.fact_bytes);
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
  prefault_region(fact, c.fact_bytes);
  if (c.policy == "stream") gem5_set_streaming(fact, (long)c.fact_bytes);
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
  fill_fact(fact, local_n, keys, c.hit_rate, c.seed);
  prefault_region(fact, phys_bytes);
  if (c.policy == "stream") gem5_set_streaming(fact, (long)phys_bytes);
  std::string placement;
  bool placed = check_pages_on_node(fact, phys_bytes, alloc_node, &placement);
  if (!placed) {
    std::cerr << "FATAL: fact placement failed: " << placement << "\n";
    std::exit(10);
  }
  for (int i = 0; i < c.warmups; ++i) warm_table(table);
  std::atomic<size_t> next{0};
  std::vector<Result> partial(c.threads);
  std::vector<uint64_t> thread_cycles(c.threads, 0);
  std::vector<uint64_t> thread_tuples(c.threads, 0);
  std::vector<uint64_t> thread_xhash(c.threads, 0);
  bool want_hash = c.result_hash;
  bool no_stream = c.no_stream;
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
      } else if (want_hash) {
        rr = join_range_hashed(table, fact, begin, end, c.policy, c.pf_distance, &thread_xhash[tid]);
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
    else if (a == "--policy") c.policy = need("--policy");
    else if (a == "--self-test") c.self_test = need("--self-test");
    else if (a == "--fact-bytes") c.fact_bytes = parse_size(need("--fact-bytes"));
    else if (a == "--hot-bytes") c.hot_bytes = parse_size(need("--hot-bytes"));
    else if (a == "--fact-node") c.fact_node = std::stoi(need("--fact-node"));
    else if (a == "--hot-node") c.hot_node = std::stoi(need("--hot-node"));
    else if (a == "--threads") c.threads = std::stoi(need("--threads"));
    else if (a == "--reps") c.reps = std::stoi(need("--reps"));
    else if (a == "--warmups") c.warmups = std::stoi(need("--warmups"));
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
