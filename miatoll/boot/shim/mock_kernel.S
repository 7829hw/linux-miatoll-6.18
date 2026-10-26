/* SPDX-License-Identifier: BSD-2-Clause */
.section .image_header,"ax"
.global _start
_start:
    b mock_entry
    nop
    .quad 0
    .quad 0x10000
    .quad 0xa
    .quad 0, 0, 0
    .ascii "ARM\x64"
    .long 0
.text
mock_entry:
    orr x5, x1, x2
    orr x5, x5, x3
    cbnz x5, mock_bad_registers
    adrp x5, _start
    tst x5, #0x1fffff
    b.ne mock_bad_registers
    b mock_main
mock_bad_registers:
    mov x0, #21
    mov x8, #93
    svc #0
