// Returns 1 only for a complete, checksum-valid newest Emerald save generation.
// x0 emulator context; x5 main base; x6 subsdk0 base.
stp x19, x20, [sp, #-64]!
stp x21, x22, [sp, #16]
stp x23, x24, [sp, #32]
stp x25, x30, [sp, #48]
mov x19, #0xf040
movk x19, #0x15e, lsl #16
add x19, x19, x6
// The binding hook sets this only after context+E8 and context+E0 are installed.
ldr x8, [x19, #32]
cmp x8, x0
b.ne reject
ldr x8, [x0, #0xd0]
cbz x8, reject
ldr x8, [x0, #0xe8]
cbz x8, reject
// main+0x548CC binds the machine at context+0x40.
// main+0x31F10 loads its backup manager at +0x98;
// main+0x1F3A0 loads the active flash at manager+0x10.
ldr x8, [x0, #0x40]
cbz x8, reject
ldr x8, [x8, #0x98]
cbz x8, reject
ldr x8, [x8, #0x10]
cbz x8, reject
ldr w9, [x8, #0x34]
cmp w9, #4
b.ne reject
ldr w9, [x8, #0x20]
cmp w9, #0x20, lsl #12
b.ne reject
ldr x20, [x8, #0x10]
cbz x20, reject
mov x0, x20
bl headers
mov w23, w0
mov w22, w1
mov w24, w2
mov w25, w3
add x0, x20, #0xe, lsl #12
bl headers
mov x21, xzr
cbz w23, candidate_second
mov x21, x20
candidate_second:
cbz w0, select_max
cbz x21, use_second
sub w8, w1, w22
cmp w8, #0
b.le select_max
use_second:
add x21, x20, #0xe, lsl #12
mov w22, w1
select_max:
cbz x21, reject
cbz w3, max_ready
cbz w25, second_max
sub w8, w2, w24
cmp w8, #0
b.le max_ready
second_max:
mov w24, w2
max_ready:
cmp w22, w24
b.ne reject
ldr w8, [x19, #4]
cbz w8, checksums
ldr x8, [x19, #8]
cmp x8, x20
b.ne checksums
ldr w8, [x19]
cmp w8, w22
b.eq reject
checksums:
mov x8, x21
mov w9, #14
adr x10, lengths
sector:
ldrh w11, [x8, #0xff4]
ldrh w11, [x10, x11, lsl #1]
mov x12, x8
mov w13, wzr
sum:
ldr w14, [x12], #4
add w13, w13, w14
subs w11, w11, #4
b.ne sum
add w13, w13, w13, lsr #16
and w13, w13, #0xffff
ldrh w14, [x8, #0xff6]
cmp w13, w14
b.ne reject
add x8, x8, #1, lsl #12
subs w9, w9, #1
b.ne sector
str w22, [x19, #16]
str x20, [x19, #24]
mov w0, #1
b finish
reject:
mov w0, wzr
finish:
ldp x25, x30, [sp, #48]
ldp x23, x24, [sp, #32]
ldp x21, x22, [sp, #16]
ldp x19, x20, [sp], #64
ret
// Check 14 sector footers. Return complete, counter, newest observed, observed flag.
headers:
mov x8, x0
mov w0, wzr
mov w1, wzr
mov w2, wzr
mov w3, wzr
mov w4, wzr
mov w5, wzr
mov w6, #0x2025
movk w6, #0x801, lsl #16
header_loop:
ldrh w7, [x8, #0xff4]
ldr w9, [x8, #0xff8]
cmp w9, w6
b.ne bad_header
cmp w7, #14
b.hs bad_header
ldr w9, [x8, #0xffc]
cbnz w3, max_compare
mov w2, w9
mov w3, #1
max_compare:
sub w10, w9, w2
cmp w10, #0
csel w2, w9, w2, gt
cbnz w5, compare_counter
mov w1, w9
compare_counter:
cmp w9, w1
b.ne bad_header
mov w10, #1
lsl w10, w10, w7
tst w0, w10
b.ne bad_header
orr w0, w0, w10
b next_header
bad_header:
mov w4, #1
next_header:
add x8, x8, #1, lsl #12
add w5, w5, #1
cmp w5, #14
b.ne header_loop
mov w10, #0x3fff
cmp w0, w10
cset w0, eq
bic w0, w0, w4
ret
lengths:
.hword 0xf2c, 0xf80, 0xf80, 0xf80, 0xf08, 0xf80, 0xf80, 0xf80, 0xf80, 0xf80, 0xf80, 0xf80, 0xf80, 0x7d0

