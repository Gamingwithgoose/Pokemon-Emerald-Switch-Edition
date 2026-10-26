// W3 diagnostic boundary. x0=context, x2=service, x3=guest CPU,
// x5=main base, x6=subsdk0 base. Own state follows existing save/RTC state.
stp x19,x20,[sp,#-96]!
stp x21,x22,[sp,#16]
stp x23,x30,[sp,#32]
mov x23,x5
mov x19,#0xf080
movk x19,#0x15e,lsl #16
add x19,x19,x6
cmp w2,#0x49
b.eq poll
cmp w2,#0x4a
b.ne capture
poll:
ldr w8,[x19,#4]
add w8,w8,#1
str w8,[x19,#4]
tst w8,#0x3f
b.ne finish
capture:
ldr w8,[x19]
cmp w8,#32
b.hs finish
add w8,w8,#1
str w8,[x19]
stp w8,w2,[sp,#48]
ldr x9,[x0,#0xd0]
mov w10,#-1
mov w11,#-1
mov w12,#-1
cbz x9,record
ldr w10,[x9,#0x2770]
ldr w11,[x9,#0x730]
ldr w12,[x9,#0x688]
record:
stp w10,w11,[sp,#56]
ldr w13,[x3,#0x48]
stp w12,w13,[sp,#64]
adr x0,path
adr x1,append_mode
cmp w8,#1
b.ne open
adr x1,write_mode
open:
mov x16,#0x320
movk x16,#0x16,lsl #16
add x16,x16,x23
blr x16
cbz x0,finish
mov x20,x0
add x0,sp,#48
mov x1,#24
mov x2,#1
mov x3,x20
mov x16,#0x370
movk x16,#0x16,lsl #16
add x16,x16,x23
blr x16
mov x0,x20
mov x16,#0x340
movk x16,#0x16,lsl #16
add x16,x16,x23
blr x16
mov x8,#0x638
movk x8,#0x1d,lsl #16
ldr x8,[x23,x8]
ldr x0,[x8]
mov w1,#0
mov x16,#0x9d28
movk x16,#4,lsl #16
add x16,x16,x23
blr x16
finish:
ldp x23,x30,[sp,#32]
ldp x21,x22,[sp,#16]
ldp x19,x20,[sp],#96
ret
path:
.ascii "save:/Emerald_W3.bin\0"
append_mode:
.ascii "ab\0"
write_mode:
.ascii "wb\0"
