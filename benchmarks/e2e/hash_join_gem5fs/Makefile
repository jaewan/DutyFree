CXX ?= g++

BUILD := build
SRC := src/cxl_join_bench.cpp

.PHONY: all gem5fs clean

all: gem5fs

# gem5 full-system (FS) build: the guest kernel handles mbind/pin/perf, so
# DO NOT define GEM5 (keep the native syscall paths). Static-linked to avoid
# glibc mismatch with the guest image and for easy rcS injection. No
# -march/-mavx2: keep default x86-64 (SSE2) — the gem5 x86 CPU model does
# not execute AVX/AVX2.
gem5fs: $(BUILD)/cxl_join_bench.gem5fs

$(BUILD)/cxl_join_bench.gem5fs: $(SRC)
	mkdir -p $(BUILD)
	$(CXX) -O3 -std=c++17 -Wall -Wextra -Wpedantic -static -pthread -o $@ $<

clean:
	rm -rf $(BUILD)
