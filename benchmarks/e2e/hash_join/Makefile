CXX ?= g++
CXXFLAGS ?= -O3 -std=c++17 -Wall -Wextra -Wpedantic -march=native -pthread
LDFLAGS ?= -pthread

BUILD := build
SRC := src/cxl_join_bench.cpp

.PHONY: all native gem5 w7 test clean

# W7 (W7_PREREGISTRATION_2026-08-23.md) builds to SEPARATE names. The pre-W7
# binaries are the provenance of every published hash_join number and are not
# overwritten -- F10 in W4.3_PROVENANCE_LEDGER_2026-08-23.md is exactly the
# failure of not being able to say which binary produced a row. Recorded here so
# a future reader can check:
#   build/cxl_join_bench       sha256 3755f1c974e30034ee0618bae33a6a8e6baf718cd67b769139f271971d550786
#   build/cxl_join_bench.gem5  sha256 917413d5fab4e61404b89e905e3d09af91fed37afbe357483f297fc07194a069
# Both predate --probe-batch; with --probe-batch 0 the W7 binaries take the same
# code path, but they are still different binaries and are named differently.

all: native

native: $(BUILD)/cxl_join_bench

$(BUILD)/cxl_join_bench: $(SRC)
	mkdir -p $(BUILD)
	$(CXX) $(CXXFLAGS) -o $@ $< $(LDFLAGS)

gem5: $(BUILD)/cxl_join_bench.gem5

$(BUILD)/cxl_join_bench.gem5: $(SRC)
	mkdir -p $(BUILD)
	$(CXX) -O3 -std=c++17 -Wall -Wextra -Wpedantic -DGEM5 -static -pthread -o $@ $<

test: native
	./$(BUILD)/cxl_join_bench --self-test reference
	./$(BUILD)/cxl_join_bench --self-test numa --fact-node 2 --fact-bytes 268435456 --cpu-list 0

clean:
	rm -rf $(BUILD)

w7: $(BUILD)/cxl_join_bench_w7 $(BUILD)/cxl_join_bench_w7.gem5

$(BUILD)/cxl_join_bench_w7: $(SRC)
	mkdir -p $(BUILD)
	$(CXX) $(CXXFLAGS) -o $@ $< $(LDFLAGS)

$(BUILD)/cxl_join_bench_w7.gem5: $(SRC)
	mkdir -p $(BUILD)
	$(CXX) -O3 -std=c++17 -Wall -Wextra -Wpedantic -DGEM5 -static -pthread -o $@ $<
