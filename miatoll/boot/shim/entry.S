/* SPDX-License-Identifier: BSD-2-Clause */
.section .image_header,"ax"
.global _start
_start:
    b shim_entry
    nop
    .quad 0x80000
    .quad __shim_end - _start
    .quad 0xa
    .quad 0, 0, 0
    .ascii "ARM\x64"
    .long 0
.section .text.entry,"ax"
shim_entry:
    adrp x9, __stack_top
    add x9, x9, :lo12:__stack_top
    mov sp, x9
    adrp x1, __dtb_template
    add x1, x1, :lo12:__dtb_template
    adrp x2, __dtb_work
    add x2, x2, :lo12:__dtb_work
    mov w3, #SHIM_FDT_CAPACITY
    bl shim_prepare_fdt
    cbnz w0, shim_halt
    adrp x4, __kernel_start
    add x4, x4, :lo12:__kernel_start
    tst x4, #0x1fffff
    b.ne shim_halt
    adrp x0, __dtb_work
    add x0, x0, :lo12:__dtb_work
    mov x1, xzr
    mov x2, xzr
    mov x3, xzr
    dsb sy
    isb
    br x4
shim_halt:
    wfe
    b shim_halt
