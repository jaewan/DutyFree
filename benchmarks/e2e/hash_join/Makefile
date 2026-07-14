CXX ?= g++
CXXFLAGS ?= -O3 -std=c++17 -Wall -Wextra -Wpedantic -march=native -pthread
LDFLAGS ?= -pthread

BUILD := build
SRC := src/cxl_join_bench.cpp

.PHONY: all native gem5 test clean

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
