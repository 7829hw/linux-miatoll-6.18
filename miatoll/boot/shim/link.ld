/* SPDX-License-Identifier: BSD-2-Clause */
ENTRY(_start)
SECTIONS {
    . = 0;
    .text : { KEEP(*(.image_header)) *(.text.entry) *(.text*) *(.rodata*) }
    .data : { *(.data*) *(.bss*) *(COMMON) }
    ASSERT(. < 0x180000, "Shim code overlaps embedded kernel")
    . = 0x180000;
    .payload : { *(.payload) }
    /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) *(.llvm_addrsig) }
}
