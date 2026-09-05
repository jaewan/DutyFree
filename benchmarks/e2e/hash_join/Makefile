CXX ?= g++
CXXFLAGS ?= -O3 -std=c++17 -Wall -Wextra -Wpedantic -march=native -pthread
LDFLAGS ?= -pthread

BUILD := build
SRC := src/cxl_join_bench.cpp

.PHONY: all native gem5 gem5fs h3-dirty-owner h3-dirty-owner-fs w7 test clean

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

h3-dirty-owner: $(BUILD)/streaming_h3_dirty_owner.gem5

$(BUILD)/streaming_h3_dirty_owner.gem5: src/streaming_h3_dirty_owner.cpp
	mkdir -p $(BUILD)
	$(CXX) -O2 -std=c++17 -Wall -Wextra -Wpedantic -static -pthread -o $@ $<

h3-dirty-owner-fs: $(BUILD)/streaming_h3_dirty_owner.gem5fs

$(BUILD)/streaming_h3_dirty_owner.gem5fs: src/streaming_h3_dirty_owner.cpp
	mkdir -p $(BUILD)
	$(CXX) -O2 -std=c++17 -Wall -Wextra -Wpedantic -DGEM5_FS -static -pthread -o $@ $<

$(BUILD)/cxl_join_bench.gem5: $(SRC)
	mkdir -p $(BUILD)
	$(CXX) -O3 -std=c++17 -Wall -Wextra -Wpedantic -mclflushopt -DGEM5 -static -pthread -o $@ $<

# H1BW single-core certification (H1BW_SINGLECORE_PREREG_2026-09-04.md).  A
# SEPARATE name, for the reason the W7/W8 targets above are separate names:
# build/cxl_join_bench.gem5 sha256 cac9e27ab42448a89c7c51e93749107357795ced6456
# babf2f51bfe625140f93 is the provenance of all 24 h1bw_mc_* cells and of the
# h1bw_multicore / h1bw_cxlbw / h1bw_slice_bracket campaigns, and overwriting a
# binary that published magnitudes are attributed to is exactly the F13 defect
# BUILD_PROVENANCE.md was written to stop.  Same source, same flags; the only
# behavioural difference is reachable through --window-brackets, which defaults
# off.
gem5-window: $(BUILD)/cxl_join_bench.gem5wbrk

$(BUILD)/cxl_join_bench.gem5wbrk: $(SRC)
	mkdir -p $(BUILD)
	$(CXX) -O3 -std=c++17 -Wall -Wextra -Wpedantic -mclflushopt -DGEM5 -static -pthread -o $@ $<

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
	$(CXX) -O3 -std=c++17 -Wall -Wextra -Wpedantic -mclflushopt -DGEM5 -static -pthread -o $@ $<

# W8 (GEM5_FS_OS_CONTRACT_*): the full-system binary. Separate name again --
# this one carries the --declare mprotect path (PROT_READ|PROT_STREAMING),
# which the W7 binaries do not have, and it must be possible to say which of
# the two produced any given row. Static, no -march=native: it runs inside a
# gem5 FS guest, not on this host.
gem5fs: $(BUILD)/cxl_join_bench.gem5fs

$(BUILD)/cxl_join_bench.gem5fs: $(SRC)
	mkdir -p $(BUILD)
	# GEM5_FS is deliberately distinct from GEM5/SE: FS has real Linux NUMA
	# syscalls, whereas GEM5/SE needs the bindpool pseudo-op.
	$(CXX) -O3 -std=c++17 -Wall -Wextra -Wpedantic -mclflushopt -DGEM5 -DGEM5_FS -static -pthread -o $@ $<
