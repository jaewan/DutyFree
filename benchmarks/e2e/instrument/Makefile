# Build rule for the vendored aggressor, carrying the exact flags used by
# ~/tmp_dutyfree_exp/Makefile at upstream 481115c. Do not "improve" these:
# every co-run number in benchmarks/e2e was produced by a binary built with
# this line, and changing it silently changes the instrument.
#
# -march=native means the binary is host-specific. Each host builds its own;
# binaries are never copied between hosts (see README, "Why native builds").

CC       = gcc
CFLAGS   = -O2 -march=native -mavx2 -msse4.1 -Wall -Wextra -pthread
LDFLAGS  = -lnuma -lm -lpthread

SRCDIR   = src
BINDIR   = bin

.PHONY: all clean verify

all: $(BINDIR)/aggressor $(BINDIR)/amd_flushbehind_aggressor

$(BINDIR):
	mkdir -p $(BINDIR)

$(BINDIR)/aggressor: $(SRCDIR)/aggressor.c $(SRCDIR)/common.h | $(BINDIR)
	$(CC) $(CFLAGS) -o $@ $< $(LDFLAGS)

# The AMD flush-behind streamer. Its own header documents a slightly different
# build line (-mavx2, no -msse4.1, -lnuma -lm); both that line and the one above
# were verified on moscxl to produce a binary bit-identical to the one that
# produced the FB0/FB256 arms, so the uniform flags are used here.
$(BINDIR)/amd_flushbehind_aggressor: $(SRCDIR)/amd_flushbehind_aggressor.c $(SRCDIR)/common.h | $(BINDIR)
	$(CC) $(CFLAGS) -o $@ $< $(LDFLAGS)

# Fail loudly if this checkout's sources have drifted from the recorded manifest.
verify:
	@md5sum -c MANIFEST.md5

clean:
	rm -rf $(BINDIR)
