CXX ?= g++

BUILD := build
SRC := src/cxl_join_bench.cpp

.PHONY: all gem5se clean

all: gem5se

# gem5 syscall-emulation (SE) build:
#   -DGEM5   : mbind/pin/perf become no-ops; placement and STREAMING tagging
#              go through m5 pseudo-ops instead (gem5_bind_pool 0x56,
#              gem5_set_streaming 0x55).
#   -static  : SE has no dynamic loader.
#   No -march/-mavx2: keep default x86-64 (SSE2) — the gem5 x86 CPU model
#   does not execute AVX/AVX2.
gem5se: $(BUILD)/cxl_join_bench.gem5se

$(BUILD)/cxl_join_bench.gem5se: $(SRC)
	mkdir -p $(BUILD)
	$(CXX) -O3 -std=c++17 -Wall -Wextra -Wpedantic -DGEM5 -static -pthread -o $@ $<

clean:
	rm -rf $(BUILD)
