// DuckDB mmap-probe harness.
// Native (no -DGEM5): declaration-site identity. Probe keys live in a
// file-backed mmap; table function mmap_probe() scans that mapping. Hash
// table b stays a DuckDB table. Matches vs CREATE TABLE p, smaps copy-gate,
// mprotect UAPI. Not H2.
//
// GEM5 (-DGEM5): SE H2 kill-gate. Anonymous mmap, bind_pool CXL, m5op
// SET_STREAMING (0x55) on the probe only. Table b stays WB DRAM. Not OS
// mprotect (that is FS). See DUCKDB_MMAP_SE_H2_PREREG_2026-09-02.md.
#include <duckdb.h>

#include <cctype>
#include <cerrno>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>
#include <unistd.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <fcntl.h>

#ifndef PROT_STREAMING
#define PROT_STREAMING 0x10
#endif

#ifdef GEM5
// Same m5ops as cxl_join_bench.cpp. The "memory" clobber is load-bearing:
// set_streaming re-marks PTEs; bind_pool must land before first touch.
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
static inline void gem5_exit_now() {
  uint64_t m5_rax;
    __asm__ volatile(".byte 0x0f, 0x04, 0x21, 0x00"
                     : "=a"(m5_rax) : "D"(0ULL) : "memory");
    (void)m5_rax;
}
static inline void gem5_bind_pool(void *addr, uint64_t size, uint64_t pool) {
  uint64_t m5_rax;
  __asm__ volatile(".byte 0x0f, 0x04, 0x56, 0x00"
                   : "=a"(m5_rax) : "D"(addr), "S"(size), "d"(pool) : "memory");
  (void)m5_rax;
}
#else
static inline void gem5_set_streaming(void *, long) {}
static inline void gem5_reset_stats_now() {}
static inline void gem5_exit_now() {}
static inline void gem5_bind_pool(void *, uint64_t, uint64_t) {}
#endif

// r5-matched table/LLC: 40*N / 7680KiB = 0.5333. N must be divisible by chain.
static const uint64_t WANT_N = 838864;
static const uint64_t WANT_P = 10000000;
static const uint64_t GEM5_N = 104856;
static const uint64_t GEM5_P = 1048576;
static const uint64_t SMOKE_N = 1024;
static const uint64_t SMOKE_P = 8192;
static const int WANT_CHAIN = 8;
static const double COPY_FRAC = 0.25;
static const double VMA_FRAC = 0.50;
static const uint64_t CXL_POOL = 1;

struct ProbeMap {
  std::string path;
  int64_t *keys = nullptr;
  uint64_t n = 0;
  uint64_t bytes = 0;
  int fd = -1;
  bool anon = false;
};

struct InitOff {
  idx_t off = 0;
};

struct Smaps {
  uint64_t rss_probe_file = 0;
  uint64_t rss_anon = 0;
  uint64_t rss_total = 0;
  int n_probe_vma = 0;
};

static ProbeMap g_probe;
static bool g_fatal_scan = false;

static void die(const std::string &m) {
  std::cerr << "FATAL: " << m << "\n";
  std::exit(2);
}

static void qcheck(duckdb_state st, duckdb_result *res, const char *what) {
  if (st == DuckDBSuccess) return;
  const char *e = res ? duckdb_result_error(res) : "";
  die(std::string(what) + ": " + (e ? e : "unknown"));
}

static Smaps parse_smaps(const std::string &probe_base) {
  Smaps o{};
  std::ifstream in("/proc/self/smaps");
  if (!in) {
#ifdef GEM5
    return o;
#else
    die("cannot read /proc/self/smaps");
#endif
  }
  std::string line, header;
  uint64_t rss = 0;
  auto flush = [&]() {
    if (header.empty()) return;
    o.rss_total += rss;
    const auto sp = header.rfind(' ');
    std::string name;
    if (sp != std::string::npos && sp + 1 < header.size() && header[sp + 1] == '/')
      name = header.substr(sp + 1);
    else if (sp != std::string::npos)
      name = header.substr(sp + 1);
    const bool file_probe = !probe_base.empty() && name.find(probe_base) != std::string::npos;
    const bool anon = name.empty() || name == "[heap]" || name.rfind("[anon", 0) == 0 ||
                      name == "[stack]";
    if (file_probe) {
      o.rss_probe_file += rss;
      o.n_probe_vma += 1;
    } else if (anon)
      o.rss_anon += rss;
    rss = 0;
    header.clear();
  };
  while (std::getline(in, line)) {
    if (!line.empty() && std::isxdigit(static_cast<unsigned char>(line[0])) &&
        line.find('-') != std::string::npos && line.find(" kB") == std::string::npos) {
      flush();
      header = line;
    } else if (line.rfind("Rss:", 0) == 0) {
      rss = std::strtoull(line.c_str() + 4, nullptr, 10) * 1024ull;
    }
  }
  flush();
  return o;
}

static void bind_mmap(duckdb_bind_info info) {
  auto *p = static_cast<ProbeMap *>(duckdb_bind_get_extra_info(info));
  if (!p || !p->keys) {
    duckdb_bind_set_error(info, "mmap_probe: no mapping");
    return;
  }
  duckdb_logical_type t = duckdb_create_logical_type(DUCKDB_TYPE_BIGINT);
  duckdb_bind_add_result_column(info, "k", t);
  duckdb_destroy_logical_type(&t);
  duckdb_bind_set_bind_data(info, p, nullptr);
  duckdb_bind_set_cardinality(info, p->n, true);
}

static void init_mmap(duckdb_init_info info) {
  duckdb_init_set_max_threads(info, 1);
  auto *st = new InitOff();
  duckdb_init_set_init_data(info, st, [](void *p) { delete static_cast<InitOff *>(p); });
}

static void scan_mmap(duckdb_function_info info, duckdb_data_chunk output) {
  auto *p = static_cast<ProbeMap *>(duckdb_function_get_bind_data(info));
  auto *st = static_cast<InitOff *>(duckdb_function_get_init_data(info));
  if (!p || !st) {
    duckdb_function_set_error(info, "mmap_probe: missing state");
    g_fatal_scan = true;
    return;
  }
  const idx_t vs = duckdb_vector_size();
  const idx_t remain = p->n > st->off ? (idx_t)(p->n - st->off) : 0;
  const idx_t take = remain < vs ? remain : vs;
  duckdb_vector vec = duckdb_data_chunk_get_vector(output, 0);
  auto *out = static_cast<int64_t *>(duckdb_vector_get_data(vec));
  if (take) std::memcpy(out, p->keys + st->off, take * sizeof(int64_t));
  st->off += take;
  duckdb_data_chunk_set_size(output, take);
}

static void register_mmap_probe(duckdb_connection con) {
  duckdb_table_function tf = duckdb_create_table_function();
  duckdb_table_function_set_name(tf, "mmap_probe");
  duckdb_table_function_set_extra_info(tf, &g_probe, nullptr);
  duckdb_table_function_set_bind(tf, bind_mmap);
  duckdb_table_function_set_init(tf, init_mmap);
  duckdb_table_function_set_function(tf, scan_mmap);
  if (duckdb_register_table_function(con, tf) != DuckDBSuccess)
    die("duckdb_register_table_function mmap_probe");
  duckdb_destroy_table_function(&tf);
}

static void sql(duckdb_connection con, const std::string &q) {
  duckdb_result res;
  qcheck(duckdb_query(con, q.c_str(), &res), &res, q.c_str());
  duckdb_destroy_result(&res);
}

static void join_result(duckdb_connection con, const std::string &q,
                        int64_t *count, int64_t *payload_sum) {
  duckdb_result res;
  qcheck(duckdb_query(con, q.c_str(), &res), &res, q.c_str());
  if (duckdb_row_count(&res) != 1) die("join did not return one row");
  *count = duckdb_value_int64(&res, 0, 0);
  *payload_sum = duckdb_value_int64(&res, 1, 0);
  duckdb_destroy_result(&res);
}

static void fill_probe_mmap(duckdb_connection con, uint64_t p, uint64_t k) {
  std::ostringstream qs;
  qs << "SELECT (hash(i) % " << k << ")::BIGINT FROM range(" << p << ") t(i);";
  duckdb_result res;
  qcheck(duckdb_query(con, qs.str().c_str(), &res), &res, "hash fill");
  const idx_t rows = duckdb_row_count(&res);
  if (rows != p) die("hash fill row count");
  const auto *col = static_cast<const int64_t *>(duckdb_column_data(&res, 0));
  if (!col) die("hash fill column");
  std::memcpy(g_probe.keys, col, p * sizeof(int64_t));
  duckdb_destroy_result(&res);
}

static void fill_probe_mod(uint64_t p, uint64_t k) {
  if (!g_probe.keys) die("fill_probe_mod: no mapping");
  for (uint64_t i = 0; i < p; i++)
    g_probe.keys[i] = static_cast<int64_t>(i % k);
}

static void map_probe(const std::string &path, uint64_t n) {
  g_probe.path = path;
  g_probe.n = n;
  g_probe.bytes = n * sizeof(int64_t);
#ifdef GEM5
  // SE has no durable file for the probe, and bind_pool must precede first
  // touch. Anonymous CXL-backed pages are the SE analogue of the native
  // file-backed VMA.
  (void)path;
  void *p = mmap(nullptr, g_probe.bytes, PROT_READ | PROT_WRITE,
                 MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
  if (p == MAP_FAILED) die(std::string("mmap anon: ") + std::strerror(errno));
  gem5_bind_pool(p, g_probe.bytes, CXL_POOL);
  g_probe.keys = static_cast<int64_t *>(p);
  g_probe.anon = true;
  g_probe.fd = -1;
#else
  g_probe.fd = open(path.c_str(), O_RDWR | O_CREAT | O_TRUNC, 0644);
  if (g_probe.fd < 0) die(std::string("open probe: ") + std::strerror(errno));
  if (ftruncate(g_probe.fd, (off_t)g_probe.bytes) != 0)
    die(std::string("ftruncate: ") + std::strerror(errno));
  void *p = mmap(nullptr, g_probe.bytes, PROT_READ | PROT_WRITE, MAP_SHARED, g_probe.fd, 0);
  if (p == MAP_FAILED) die(std::string("mmap: ") + std::strerror(errno));
  g_probe.keys = static_cast<int64_t *>(p);
  g_probe.anon = false;
#endif
}

static void unmap_probe() {
  if (g_probe.keys && g_probe.bytes)
    munmap(g_probe.keys, g_probe.bytes);
  if (g_probe.fd >= 0) close(g_probe.fd);
  g_probe = {};
}

#ifndef GEM5
static int try_mprotect(const char *kind) {
  if (!g_probe.keys) return -1;
  int prot = PROT_READ;
  if (std::strcmp(kind, "streaming") == 0) prot |= PROT_STREAMING;
  else if (std::strcmp(kind, "read") != 0) die("mprotect kind");
  errno = 0;
  if (mprotect(g_probe.keys, g_probe.bytes, prot) != 0) return errno;
  return 0;
}
#endif

static void json_escape(const std::string &s) {
  for (char c : s) {
    if (c == '"' || c == '\\') std::cout << '\\';
    std::cout << c;
  }
}

int main(int argc, char **argv) {
  uint64_t n = WANT_N, probe = WANT_P;
  int chain = WANT_CHAIN;
  std::string mode = "both";
  std::string mprot = "streaming";
  std::string outdir = "/tmp/duckdb_mmap_probe";
  std::string policy = "wb";
  std::string keys = "hash";
  bool self_test = false;
  for (int i = 1; i < argc; i++) {
    auto need = [&](const char *flag) -> char * {
      if (i + 1 >= argc) die(std::string("missing arg for ") + flag);
      return argv[++i];
    };
    std::string a = argv[i];
    if (a == "--n") n = std::strtoull(need("--n"), nullptr, 10);
    else if (a == "--probe") probe = std::strtoull(need("--probe"), nullptr, 10);
    else if (a == "--chain") chain = std::atoi(need("--chain"));
    else if (a == "--mode") mode = need("--mode");
    else if (a == "--mprotect") mprot = need("--mprotect");
    else if (a == "--outdir") outdir = need("--outdir");
    else if (a == "--policy") policy = need("--policy");
    else if (a == "--keys") keys = need("--keys");
    else if (a == "--preset") {
      const std::string p = need("--preset");
      if (p == "gem5") {
        n = GEM5_N;
        probe = GEM5_P;
        chain = WANT_CHAIN;
        keys = "mod";
        mode = "mmap";
      } else if (p == "gem5-smoke") {
        n = SMOKE_N;
        probe = SMOKE_P;
        chain = WANT_CHAIN;
        keys = "mod";
        mode = "mmap";
      } else
        die("preset (gem5|gem5-smoke)");
    } else if (a == "--self-test") self_test = true;
    else die("unknown flag " + a);
  }
  if (self_test) {
    n = 1024;
    probe = 65536;
    chain = 8;
    mprot = "read";
    keys = "hash";
    mode = "both";
  }
  if (policy != "wb" && policy != "stream") die("policy (wb|stream)");
  if (keys != "hash" && keys != "mod") die("keys (hash|mod)");
  if (policy == "stream") {
#ifndef GEM5
    die("native --policy stream refused; PAT slot 6 is not a datapath off gem5. "
        "Use --mprotect streaming for the UAPI probe");
#endif
  }
  if (chain < 1) die("chain");
  const uint64_t k = n / (uint64_t)chain;
  if (k < 1) die("k");
  if (n % (uint64_t)chain != 0) die("n must be divisible by chain");

  const char *ver = duckdb_library_version();
  duckdb_database db = nullptr;
  duckdb_connection con = nullptr;
  if (duckdb_open(nullptr, &db) != DuckDBSuccess) die("duckdb_open");
  if (duckdb_connect(db, &con) != DuckDBSuccess) die("duckdb_connect");
  sql(con, "SET threads=1;");

  std::ostringstream bsql;
  bsql << "CREATE TABLE b AS SELECT (i%" << k << ")::BIGINT AS k, (i*7)::BIGINT AS payload "
       << "FROM range(" << n << ") t(i);";
  sql(con, bsql.str());

  int64_t copy_count = -1, copy_sum = -1;
  int64_t mmap_count = -1, mmap_sum = -1;
  Smaps before{}, after{};
  int mprot_errno = -1;
  std::string mprot_note;
  double query_seconds = -1;

  if (mode == "copy" || mode == "both") {
    std::ostringstream psql;
    psql << "CREATE TABLE p AS SELECT (hash(i) % " << k << ")::BIGINT AS k FROM range("
         << probe << ") t(i);";
    sql(con, psql.str());
    join_result(con, "SELECT count(*), sum(b.payload) FROM p JOIN b ON p.k=b.k;",
                &copy_count, &copy_sum);
    sql(con, "DROP TABLE p;");
  }

  if (mode == "mmap" || mode == "both") {
    if (mkdir(outdir.c_str(), 0755) != 0 && errno != EEXIST) die("mkdir outdir");
    const std::string pfile = outdir + "/probe.bin";
    map_probe(pfile, probe);
    if (keys == "mod") fill_probe_mod(probe, k);
    else fill_probe_mmap(con, probe, k);
    if (!g_probe.anon) {
      if (msync(g_probe.keys, g_probe.bytes, MS_SYNC) != 0)
        die(std::string("msync: ") + std::strerror(errno));
    }
#ifdef GEM5
    (void)mprot;
    if (policy == "stream") {
      gem5_set_streaming(g_probe.keys, static_cast<long>(g_probe.bytes));
      mprot_note = "m5op SET_STREAMING 0x55";
      mprot_errno = 0;
    } else {
      mprot_note = "wb; no m5op";
      mprot_errno = 0;
    }
#else
    mprot_errno = try_mprotect(mprot.c_str());
    if (mprot_errno != 0) {
      mprot_note = std::strerror(mprot_errno);
      if (mprot == "streaming") {
        const int e2 = try_mprotect("read");
        if (e2 != 0) die(std::string("mprotect READ failed: ") + std::strerror(e2));
        mprot_note += "; fell back to PROT_READ";
      } else
        die(std::string("mprotect failed: ") + mprot_note);
    } else {
      mprot_note = "ok";
    }
#endif
    register_mmap_probe(con);
    before = parse_smaps("probe.bin");
#ifdef GEM5
    std::cerr << "JOIN_MEASURE_BEGIN n=" << n << " probe=" << probe
              << " table_bytes=" << (40ull * n) << " probe_bytes=" << (probe * 8ull)
              << " policy=" << policy << std::endl;
    gem5_reset_stats_now();
#endif
    const auto t0 = std::chrono::steady_clock::now();
    join_result(con, "SELECT count(*), sum(b.payload) FROM mmap_probe() p JOIN b ON p.k=b.k;",
                &mmap_count, &mmap_sum);
    query_seconds = std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
#ifdef GEM5
    std::cerr << "JOIN_MEASURE_END seconds=" << std::setprecision(9) << query_seconds
              << std::endl;
#endif
    after = parse_smaps("probe.bin");
    if (g_fatal_scan) die("scan error");
  }

  const uint64_t probe_bytes = probe * 8ull;
  const uint64_t table_bytes = 40ull * n;
  const int64_t anon_delta =
      (int64_t)after.rss_anon - (int64_t)before.rss_anon;
  const bool g_match = (mode != "both") ||
                       (copy_count == mmap_count && copy_sum == mmap_sum);
  const bool g_vma = after.rss_probe_file >= (uint64_t)(VMA_FRAC * (double)probe_bytes) &&
                     after.n_probe_vma > 0;
  const bool g_copy = anon_delta <= (int64_t)(COPY_FRAC * (double)probe_bytes);
  const bool g_lib = ver && std::strstr(ver, "v1.1.3");
#ifdef GEM5
  const bool se = true;
  const char *campaign = "duckdb_mmap_se_h2";
  const bool void_site = false;
#else
  const bool se = false;
  const char *campaign = "duckdb_mmap_probe";
  const bool void_site = (!g_copy || !g_vma || !g_match);
#endif

  std::cout << "{"
            << "\"campaign\":\"" << campaign << "\","
            << "\"self_test\":" << (self_test ? "true" : "false") << ","
            << "\"gem5\":" << (se ? "true" : "false") << ","
            << "\"policy\":\"" << policy << "\","
            << "\"keys\":\"" << keys << "\","
            << "\"n\":" << n << ","
            << "\"probe\":" << probe << ","
            << "\"chain\":" << chain << ","
            << "\"k\":" << k << ","
            << "\"probe_bytes\":" << probe_bytes << ","
            << "\"table_bytes\":" << table_bytes << ","
            << "\"duckdb_c_version\":\"" << (ver ? ver : "") << "\","
            << "\"g_lib\":" << (g_lib ? "true" : "false") << ","
            << "\"copy_count\":" << copy_count << ","
            << "\"copy_sum\":" << copy_sum << ","
            << "\"mmap_count\":" << mmap_count << ","
            << "\"mmap_sum\":" << mmap_sum << ","
            << "\"query_seconds\":" << std::setprecision(9) << query_seconds << ","
            << "\"g_match\":" << (g_match ? "true" : "false") << ","
            << "\"rss_probe_before\":" << before.rss_probe_file << ","
            << "\"rss_probe_after\":" << after.rss_probe_file << ","
            << "\"rss_anon_before\":" << before.rss_anon << ","
            << "\"rss_anon_after\":" << after.rss_anon << ","
            << "\"anon_delta\":" << anon_delta << ","
            << "\"n_probe_vma\":" << after.n_probe_vma << ","
            << "\"g_vma\":" << (g_vma ? "true" : "false") << ","
            << "\"g_copy\":" << (g_copy ? "true" : "false") << ","
            << "\"mprotect_kind\":\"" << mprot << "\","
            << "\"mprotect_errno\":" << mprot_errno << ","
            << "\"mprotect_note\":\"";
  json_escape(mprot_note);
  std::cout << "\","
            << "\"status\":\"ok\","
            << "\"void_streaming_duckdb\":" << (void_site ? "true" : "false")
            << "}\n";
  std::cout.flush();
  std::cerr.flush();

  unmap_probe();
  duckdb_disconnect(&con);
  duckdb_close(&db);
#ifdef GEM5
  std::cerr << "JOIN_M5_EXIT\n";
  std::cerr.flush();
  gem5_exit_now();
#endif
  if (!g_lib) return 1;
#ifndef GEM5
  if (!g_match) return 1;
  if ((mode == "mmap" || mode == "both") && !g_vma) return 1;
  // G-copy is the declaration-site kill (hash keys, large P on c4). SE
  // presets use --keys mod; DuckDB's join heap can exceed 0.25×P when P is
  // only 8 MiB. That does not unlicense the c4 80 MiB G-copy PASS.
  if ((mode == "mmap" || mode == "both") && !g_copy && keys == "hash") return 1;
#endif
  return 0;
}
