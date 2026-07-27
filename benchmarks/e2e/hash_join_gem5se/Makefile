CXX ?= g++
CXXFLAGS ?= -O3 -std=c++17 -Wall -Wextra -Wpedantic -march=native -pthread
LDFLAGS ?= -pthread

BUILD := build
SRC := src/cxl_join_bench.cpp

.PHONY: all native gem5 gem5-fs test clean

all: native

native: $(BUILD)/cxl_join_bench

$(BUILD)/cxl_join_bench: $(SRC)
	mkdir -p $(BUILD)
	$(CXX) $(CXXFLAGS) -o $@ $< $(LDFLAGS)

gem5: $(BUILD)/cxl_join_bench.gem5

$(BUILD)/cxl_join_bench.gem5: $(SRC)
	mkdir -p $(BUILD)
	$(CXX) -O3 -std=c++17 -Wall -Wextra -Wpedantic -DGEM5 -static -pthread -o $@ $<

# gem5 full-system: real kernel handles mbind/pin/perf, so DO NOT define GEM5
# (keep the native syscall paths). Static-linked to avoid glibc mismatch with
# the guest image and for easy rcS injection. NO -march=native / -mavx2: keep
# the default x86-64 (SSE2) ISA exactly like the SE build, because the gem5 x86
# CPU model does not reliably execute AVX/AVX2 (only SSE2).
gem5-fs: $(BUILD)/cxl_join_bench.gem5fs

$(BUILD)/cxl_join_bench.gem5fs: $(SRC)
	mkdir -p $(BUILD)
	$(CXX) -O3 -std=c++17 -Wall -Wextra -Wpedantic -static -pthread -o $@ $< $(LDFLAGS)

test: native
	./$(BUILD)/cxl_join_bench --self-test reference
	./$(BUILD)/cxl_join_bench --self-test numa --fact-node 2 --fact-bytes 268435456 --cpu-list 0

clean:
	rm -rf $(BUILD)
