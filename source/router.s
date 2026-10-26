/* W3: keep original RFU bodies in place. One header gateway dispatches by LR. */
.syntax unified
.cpu arm7tdmi
.thumb
.text
.align 2
.global emerald_router
.type emerald_router,%function
.thumb_func
emerald_router:
 push {r0-r7,lr}
 mov r4,lr
 adr r7,emerald_routes
1:
 ldr r0,[r7]
 cmp r0,#0
 beq 9f
 cmp r0,r4
 beq 2f
 adds r7,#12
 b 1b
2:
 ldr r3,[r7,#4]
 ldr r6,[r7,#8]
 ldr r0,[sp]
 ldr r1,[sp,#4]
 ldr r2,[sp,#8]
 bl emerald_call_r3
 cmp r6,#0x47
 bne 3f
 bl emerald_publish
 b 9f
3:
 cmp r6,#0x45
 bne 4f
 bl emerald_scan
 b 9f
4:
 cmp r6,#0x42
 bne 5f
 svc #0x42
 b 9f
5:
 cmp r6,#0x43
 bne 6f
 ldr r0,[sp]
 svc #0x43
 b 9f
6:
 cmp r6,#0x44
 bne 7f
 svc #0x44
 b 9f
7:
 cmp r6,#0x49
 bne 8f
 svc #0x49
 b 9f
8:
 svc #0x4a
9:
 add sp,#16
 pop {r4-r7}
 pop {r0}
 bx r0
.thumb_func
emerald_call_r3:
 bx r3
.align 2
emerald_routes:
/* Generated table follows: Thumb LR, original Thumb target, service number. */
