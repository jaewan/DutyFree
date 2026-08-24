CC      = gcc
CFLAGS  = -O2 -fno-tree-vectorize -march=native -g -Wall -Wextra -I./lib
LDFLAGS = -lnuma -lm

LIB_SRCS = lib/msr.c lib/hugepage.c lib/pmu.c
LIB_OBJS = $(LIB_SRCS:.c=.o)

VICTIM_BINS = victim/pointer_chase victim/pointer_chase_nocap
AGGR_BINS   = aggressor/stream_wb    \
              aggressor/stream_wb_nopf \
              aggressor/stream_wc    \
              aggressor/stream_wc_nopf \
              aggressor/stream_nt    \
              aggressor/random_chase \
              aggressor/forced_turnover \
              aggressor/stream_wb_flushbehind \
              aggressor/stream_sw_prefetch

ALL_BINS = $(VICTIM_BINS) $(AGGR_BINS)

.PHONY: all clean check-deps

all: check-deps $(ALL_BINS)

check-deps:
	@command -v numactl >/dev/null || (echo "ERROR: numactl not found. Install libnuma-dev." && exit 1)
	@pkg-config --libs numa >/dev/null 2>&1 || (echo "ERROR: libnuma-dev not found." && exit 1)

# Victim binaries
# pointer_chase: time-bounded run, MSR disable optional (--pf-disable flag)
victim/pointer_chase: victim/pointer_chase.c $(LIB_OBJS)
	$(CC) $(CFLAGS) $^ -o $@ $(LDFLAGS)

# pointer_chase_nocap: identical binary (same source, time-bounded by --run-sec)
victim/pointer_chase_nocap: victim/pointer_chase.c $(LIB_OBJS)
	$(CC) $(CFLAGS) $^ -o $@ $(LDFLAGS)

# Aggressors
aggressor/stream_wb: aggressor/stream_wb.c $(LIB_OBJS)
	$(CC) $(CFLAGS) $^ -o $@ $(LDFLAGS)

aggressor/stream_wb_nopf: aggressor/stream_wb_nopf.c $(LIB_OBJS)
	$(CC) $(CFLAGS) $^ -o $@ $(LDFLAGS)

aggressor/stream_wc: aggressor/stream_wc.c $(LIB_OBJS)
	$(CC) $(CFLAGS) $^ -o $@ $(LDFLAGS)

# stream_wc_nopf: MOVNTDQA on WB with the four HW prefetchers disabled (MSR 0x1A4,
# read-back verified). Added 2026-08-24 for T2; the honest WC proxy, since
# stream_wc leaves the prefetchers ON. Additive -- no existing arm changed.
aggressor/stream_wc_nopf: aggressor/stream_wc_nopf.c $(LIB_OBJS)
	$(CC) $(CFLAGS) $^ -o $@ $(LDFLAGS)

aggressor/stream_nt: aggressor/stream_nt.c $(LIB_OBJS)
	$(CC) $(CFLAGS) $^ -o $@ $(LDFLAGS)

aggressor/random_chase: aggressor/random_chase.c $(LIB_OBJS)
	$(CC) $(CFLAGS) $^ -o $@ $(LDFLAGS)

aggressor/forced_turnover: aggressor/forced_turnover.c $(LIB_OBJS)
	$(CC) $(CFLAGS) $^ -o $@ $(LDFLAGS)

# stream_wb_flushbehind: WB fetch + clflushopt behind the stream (the non-allocating,
# fully-coherent middle rung of the AMD ladder). Was built by hand and never listed here.
aggressor/stream_wb_flushbehind: aggressor/stream_wb_flushbehind.c $(LIB_OBJS)
	$(CC) $(CFLAGS) $^ -o $@ $(LDFLAGS)

aggressor/stream_sw_prefetch: aggressor/stream_sw_prefetch.c $(LIB_OBJS)
	$(CC) $(CFLAGS) $^ -o $@ $(LDFLAGS)

# Library objects
lib/msr.o: lib/msr.c lib/msr.h
lib/hugepage.o: lib/hugepage.c lib/hugepage.h
lib/pmu.o: lib/pmu.c lib/pmu.h

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(LIB_OBJS) $(ALL_BINS)
