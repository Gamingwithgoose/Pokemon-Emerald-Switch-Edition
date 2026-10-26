/* Guest-side Sloop bridge. Data layout matches the verified FRLG svc_47 ABI.
 * No persistent guest allocation: parameter block lives on the caller's stack. */
.syntax unified
.cpu arm7tdmi
.thumb
.section .text.shims,"ax",%progbits
.align 2
.global emerald_publish
.type emerald_publish,%function
.thumb_func
emerald_publish:
 push {r4,lr}
 sub sp,#24
 mov r0,sp
 movs r1,#0
 str r1,[r0,#12]
 ldr r1,=0x02022b14
 movs r2,#0
1:
 ldrb r3,[r1,r2]
 strb r3,[r0,r2]
 adds r2,#1
 cmp r2,#13
 blo 1b
 ldr r1,=0x02022b22
 adds r0,#16
 movs r2,#0
2:
 ldrb r3,[r1,r2]
 strb r3,[r0,r2]
 adds r2,#1
 cmp r2,#8
 blo 2b
 mov r0,sp
 svc #0x47
 add sp,#24
 pop {r4}
 pop {r0}
 bx r0
.size emerald_publish,.-emerald_publish
.align 2
.global emerald_scan
.type emerald_scan,%function
.thumb_func
emerald_scan:
 push {lr}
 ldr r0,=0x03007890
 ldr r0,[r0]
 svc #0x45
 pop {r0}
 bx r0
.size emerald_scan,.-emerald_scan
.ltorg
