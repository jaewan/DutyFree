/* W8: a minimal in-guest `m5`, static, busybox-compatible.
 *
 * Subcommands are the ones the boot and benchmark scripts use, with gem5's own
 * argument order: exit [delay_ns], checkpoint [delay_ns [period_ns]],
 * resetstats, dumpstats, readfile (writes the --script file to stdout), fail
 * <code>. Unknown subcommands exit 2 loudly rather than silently succeeding --
 * a no-op m5 in the boot path would look exactly like a hung guest.
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

void m5_exit(uint64_t ns_delay);
void m5_fail(uint64_t ns_delay, uint64_t code);
void m5_reset_stats(uint64_t ns_delay, uint64_t ns_period);
void m5_dump_stats(uint64_t ns_delay, uint64_t ns_period);
void m5_checkpoint(uint64_t ns_delay, uint64_t ns_period);
uint64_t m5_read_file(void *buffer, uint64_t len, uint64_t offset);

static uint64_t arg(int argc, char **argv, int i, uint64_t dflt) {
    return (i < argc) ? strtoull(argv[i], NULL, 0) : dflt;
}

int main(int argc, char **argv) {
    if (argc < 2) { fprintf(stderr, "usage: m5 <exit|checkpoint|resetstats|dumpstats|readfile|fail>\n"); return 2; }
    const char *c = argv[1];
    if (!strcmp(c, "exit"))            { m5_exit(arg(argc, argv, 2, 0)); return 0; }
    if (!strcmp(c, "fail"))            { m5_fail(arg(argc, argv, 3, 0), arg(argc, argv, 2, 1)); return 0; }
    if (!strcmp(c, "resetstats"))      { m5_reset_stats(arg(argc, argv, 2, 0), arg(argc, argv, 3, 0)); return 0; }
    if (!strcmp(c, "dumpstats"))       { m5_dump_stats(arg(argc, argv, 2, 0), arg(argc, argv, 3, 0)); return 0; }
    if (!strcmp(c, "checkpoint"))      { m5_checkpoint(arg(argc, argv, 2, 0), arg(argc, argv, 3, 0)); return 0; }
    if (!strcmp(c, "readfile")) {
        static char buf[8192];
        uint64_t off = 0, n;
        while ((n = m5_read_file(buf, sizeof(buf), off)) > 0) {
            if (fwrite(buf, 1, (size_t)n, stdout) != (size_t)n) return 1;
            off += n;
            if (n < sizeof(buf)) break;
        }
        fflush(stdout);
        return 0;
    }
    fprintf(stderr, "m5: unknown command '%s'\n", c);
    return 2;
}
