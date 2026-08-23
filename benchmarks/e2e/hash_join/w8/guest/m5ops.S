/* W8: the five m5ops the guest needs, assembled exactly as gem5 does it in
 * util/m5/src/abi/x86/m5op.S -- ".byte 0x0F, 0x04" then a 16-bit function
 * number, arguments in the ordinary SysV registers, result in rax.
 *
 * gem5's own util/m5 builds with SCons, which is not installed on this host
 * and which we do not need for five entry points. Function numbers are copied
 * from include/gem5/asm/generic/m5ops.h and each is spelled out rather than
 * pulled through M5OP_FOREACH so that a mismatch is visible here.
 */
.macro m5op_func, name, func
        .globl \name
        .func \name
\name:
        .byte 0x0F, 0x04
        .word \func
        ret
        .endfunc
.endm

.text
m5op_func m5_exit,        0x21      /* M5OP_EXIT         */
m5op_func m5_fail,        0x22      /* M5OP_FAIL         */
m5op_func m5_reset_stats, 0x40      /* M5OP_RESET_STATS  */
m5op_func m5_dump_stats,  0x41      /* M5OP_DUMP_STATS   */
m5op_func m5_checkpoint,  0x43      /* M5OP_CHECKPOINT   */
m5op_func m5_read_file,   0x50      /* M5OP_READ_FILE    */

.section .note.GNU-stack,"",@progbits
