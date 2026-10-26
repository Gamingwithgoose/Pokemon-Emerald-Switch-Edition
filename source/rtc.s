// Entry ABI: original cartridge ABI x0 object, x1 cycles, w2 address,
// w3 write value/read sequential, w4 write sequential; x5 main base,
// x6 subsdk0 base, w7 operation (0 read16, 1 write16).
// State is in an explicitly appended BSS allocation in locally rebuilt subsdk0.
stp x19, x20, [sp, #-96]!
stp x21, x30, [sp, #16]
str x0, [sp, #32]
mov x20, x5
mov x19, STATE_LO
movk x19, STATE_HI, lsl #16
add x19, x19, x6
// Account for the same wait-state cycles as the original handlers.
add x8, x0, #0x24
add x9, x0, #0x28
cmp w7, #0
csel w10, w3, w4, eq
cmp w10, #0
csel x8, x9, x8, eq
ldr w8, [x8]
ldr w9, [x1]
add w8, w8, w9
add w8, w8, #1
str w8, [x1]
and w2, w2, #0x1ffffff
cmp w7, #0
b.ne write
ldr w8, [x19, #8]
cbz w8, rom
cmp w2, #0xc6
b.eq rdir
cmp w2, #0xc8
b.eq rctl
ldr w0, [x19]
ldr w8, [x19, #4]
and w0, w0, w8
ldr w9, [x19, #36]
bic w9, w9, w8
orr w0, w0, w9
b done
rdir:
ldr w0, [x19, #4]
b done
rctl:
ldr w0, [x19, #8]
b done
rom:
ldr x8, [x0, #0x10]
ldrh w0, [x8, w2, uxtw]
b done
write:
cmp w2, #0xc6
b.eq wdir
cmp w2, #0xc8
b.eq wctl
ldr w8, [x19]
ldr w9, [x19, #4]
and w3, w3, w9
bic w10, w8, w9
orr w3, w3, w10
str w3, [x19]
tbz w3, #2, reset_bus
tbz w8, #2, reset_bus
// RTC samples writes on rising SCK. Reads shift on rising SCK too.
tbnz w8, #0, done
tbz w3, #0, done
ldr w10, [x19, #12]
cmp w10, #8
b.hs transfer
ubfx w11, w3, #1, #1
ldr w12, [x19, #16]
lsl w11, w11, w10
orr w12, w12, w11
str w12, [x19, #16]
add w10, w10, #1
str w10, [x19, #12]
cmp w10, #8
b.ne done
// Accept either command bit order; normalize to 0x6n.
and w11, w12, #0xf0
cmp w11, #0x60
b.eq command
rbit w12, w12
lsr w12, w12, #24
str w12, [x19, #16]
command:
cmp w12, #0x60
b.eq reset_status
cmp w12, #0x63
b.eq status_read
cmp w12, #0x65
b.eq clock_read
cmp w12, #0x67
b.eq clock_read
b done
reset_status:
mov w8, #0x40
str w8, [x19, #32]
b done
status_read:
ldr w8, [x19, #32]
orr w8, w8, #0x40
str x8, [x19, #24]
b done
clock_read:
mov x8, #0x35a0
movk x8, #0x1d, lsl #16
ldr x8, [x20, x8]
blr x8
cbnz w0, time_ready
mov x8, #0x35a8
movk x8, #0x1d, lsl #16
ldr x8, [x20, x8]
blr x8
time_ready:
// nn::time::StandardUserSystemClock::GetCurrentTime(&posix)
add x0, sp, #40
mov x8, #0x35b0
movk x8, #0x1d, lsl #16
ldr x8, [x20, x8]
blr x8
cbnz w0, done
// nn::time::ToCalendarTime(&calendar, &additional, &posix)
add x0, sp, #48
add x1, sp, #64
add x2, sp, #40
mov x8, #0x35d8
movk x8, #0x1d, lsl #16
ldr x8, [x20, x8]
blr x8
cbnz w0, done
// CalendarTime: s16 year, s8 month/day/hour/minute/second.
ldrsh w0, [sp, #48]
mov w8, #2000
sub w0, w0, w8
bl bcd
strb w0, [x19, #24]
mov w21, #1
calendar_loop:
add x8, sp, #49
ldrb w0, [x8, x21]
bl bcd
cmp w21, #3
cinc w9, w21, hs
add x8, x19, #24
strb w0, [x8, x9]
add w21, w21, #1
cmp w21, #6
b.ne calendar_loop
strb wzr, [x19, #27]
ldr w8, [x19, #16]
cmp w8, #0x67
b.ne done
ldr x8, [x19, #24]
lsr x8, x8, #32
str x8, [x19, #24]
b done
transfer:
ldr w8, [x19, #16]
tbz w8, #0, receive
ldr x8, [x19, #24]
and w9, w8, #1
lsl w9, w9, #1
str w9, [x19, #36]
lsr x8, x8, #1
str x8, [x19, #24]
b done
receive:
// Status write is supported; calendar writes deliberately ignored for host clock.
cmp w8, #0x62
b.ne done
sub w11, w10, #8
cmp w11, #8
b.hs done
ubfx w8, w3, #1, #1
ldr w9, [x19, #32]
mov w12, #1
lsl w12, w12, w11
bic w9, w9, w12
lsl w8, w8, w11
orr w9, w9, w8
str w9, [x19, #32]
add w10, w10, #1
str w10, [x19, #12]
b done
reset_bus:
str wzr, [x19, #12]
str wzr, [x19, #16]
str wzr, [x19, #36]
b done
wdir:
and w3, w3, #15
str w3, [x19, #4]
b done
wctl:
and w3, w3, #1
str w3, [x19, #8]
done:
ldp x21, x30, [sp, #16]
ldp x19, x20, [sp], #96
ret
bcd:
mov w8, #10
udiv w9, w0, w8
msub w0, w9, w8, w0
orr w0, w0, w9, lsl #4
ret


