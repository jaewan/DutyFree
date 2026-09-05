# mmap-probe declaration-site harness (DuckDB C API 1.1.3)
DUCKDB_HOME ?= $(HOME)/duckdb-1.1.3
CXX ?= g++
CXXFLAGS ?= -O2 -std=c++17 -Wall -Wextra
CPPFLAGS += -I$(DUCKDB_HOME)
LDFLAGS += -L$(DUCKDB_HOME) -lduckdb -ldl -lpthread
BIN := build/mmap_probe
SRC := src/mmap_probe.cpp

.PHONY: all test gem5 clean
all: $(BIN)

$(BIN): $(SRC) | build
	$(CXX) $(CXXFLAGS) $(CPPFLAGS) -o $@ $(SRC) $(LDFLAGS)

build:
	mkdir -p build

# SE H2 kill-gate binary. Official libduckdb_static.a is not a closed
# archive (utf8proc/re2/mbedtls/fmt are unresolved). gem5 SE loads the
# host dynamic linker; rpath pins DuckDB 1.1.3. Not an arm.
gem5: build/mmap_probe.gem5
build/mmap_probe.gem5: $(SRC) | build
	$(CXX) $(CXXFLAGS) -DGEM5 -I$(DUCKDB_HOME) -o $@ $(SRC) \
	  -L$(DUCKDB_HOME) -Wl,-rpath,$(DUCKDB_HOME) -lduckdb -ldl -lpthread

test: $(BIN)
	LD_LIBRARY_PATH=$(DUCKDB_HOME):$$LD_LIBRARY_PATH ./$(BIN) --self-test

clean:
	rm -rf build
