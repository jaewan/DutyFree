// HNSW victim for the CAT capacity-sensitivity gate and the co-run campaign.
//
// Emits "Trial Time: <seconds>" per trial so the existing gate runner
// (benchmarks/e2e/gapbs/scripts/run_cat_sensitivity_gate.py) consumes it
// unchanged. Vectors and queries come from a fixed seed, and the index is
// built once and copied between hosts, so every host measures the same graph.
//
//   hnsw_bench build <index_path> <n> <dim> <M> <efC>
//   hnsw_bench query <index_path> <n> <dim> <queries> <ef> <k> <trials>
//
// Single-threaded by construction: the gate pins one core, and a
// multi-threaded build would make the graph depend on thread interleaving.
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <random>
#include <string>
#include <vector>

#include "hnswlib/hnswlib.h"

namespace {

// Distinct streams for base vectors and queries so that changing the query
// count cannot shift the base data.
constexpr unsigned kSeedBase = 20260821u;
constexpr unsigned kSeedQuery = 981127u;

std::vector<float> gen_vectors(size_t n, size_t dim, unsigned seed) {
    std::vector<float> v(n * dim);
    std::mt19937 rng(seed);
    std::uniform_real_distribution<float> dist(0.0f, 1.0f);
    for (size_t i = 0; i < v.size(); ++i) v[i] = dist(rng);
    return v;
}

int do_build(int argc, char** argv) {
    if (argc != 7) { fprintf(stderr, "usage: build <index> <n> <dim> <M> <efC>\n"); return 2; }
    const std::string path = argv[2];
    const size_t n = strtoull(argv[3], nullptr, 10);
    const size_t dim = strtoull(argv[4], nullptr, 10);
    const size_t M = strtoull(argv[5], nullptr, 10);
    const size_t efC = strtoull(argv[6], nullptr, 10);

    printf("build n=%zu dim=%zu M=%zu efC=%zu seed=%u\n", n, dim, M, efC, kSeedBase);
    fflush(stdout);
    std::vector<float> base = gen_vectors(n, dim, kSeedBase);
    hnswlib::L2Space space(dim);
    auto* index = new hnswlib::HierarchicalNSW<float>(&space, n, M, efC);
    const auto t0 = std::chrono::steady_clock::now();
    for (size_t i = 0; i < n; ++i) {
        index->addPoint(base.data() + i * dim, i);
        if ((i + 1) % 100000 == 0) {
            const double el = std::chrono::duration<double>(
                std::chrono::steady_clock::now() - t0).count();
            printf("  added %zu / %zu (%.1f s)\n", i + 1, n, el);
            fflush(stdout);
        }
    }
    index->saveIndex(path);
    printf("Build Time: %.6f\n", std::chrono::duration<double>(
        std::chrono::steady_clock::now() - t0).count());
    printf("saved %s\n", path.c_str());
    delete index;
    return 0;
}

int do_query(int argc, char** argv) {
    if (argc != 9) {
        fprintf(stderr, "usage: query <index> <n> <dim> <queries> <ef> <k> <trials>\n");
        return 2;
    }
    const std::string path = argv[2];
    const size_t n = strtoull(argv[3], nullptr, 10);
    const size_t dim = strtoull(argv[4], nullptr, 10);
    const size_t nq = strtoull(argv[5], nullptr, 10);
    const size_t ef = strtoull(argv[6], nullptr, 10);
    const size_t k = strtoull(argv[7], nullptr, 10);
    const size_t trials = strtoull(argv[8], nullptr, 10);

    std::vector<float> queries = gen_vectors(nq, dim, kSeedQuery);
    hnswlib::L2Space space(dim);
    auto* index = new hnswlib::HierarchicalNSW<float>(&space, path, false, n);
    index->setEf(ef);
    // Ready marker, mirroring GAPBS's "Graph has ..." line: the co-run runner
    // starts the streamer only after the victim is loaded and past trial 1.
    printf("Index loaded: %s n=%zu dim=%zu ef=%zu k=%zu queries=%zu\n",
           path.c_str(), n, dim, ef, k, nq);
    fflush(stdout);

    for (size_t t = 0; t < trials; ++t) {
        // Checksum keeps the searches from being optimised away and detects a
        // silently different index across hosts.
        double checksum = 0.0;
        const auto t0 = std::chrono::steady_clock::now();
        for (size_t q = 0; q < nq; ++q) {
            auto res = index->searchKnn(queries.data() + q * dim, k);
            while (!res.empty()) { checksum += res.top().first; res.pop(); }
        }
        const double el = std::chrono::duration<double>(
            std::chrono::steady_clock::now() - t0).count();
        printf("Trial Time: %.6f\n", el);
        printf("  checksum: %.6f\n", checksum);
        fflush(stdout);
    }
    delete index;
    return 0;
}

}  // namespace

int main(int argc, char** argv) {
    if (argc < 2) {
        fprintf(stderr, "usage: %s build|query ...\n", argv[0]);
        return 2;
    }
    if (!strcmp(argv[1], "build")) return do_build(argc, argv);
    if (!strcmp(argv[1], "query")) return do_query(argc, argv);
    fprintf(stderr, "unknown mode %s\n", argv[1]);
    return 2;
}
