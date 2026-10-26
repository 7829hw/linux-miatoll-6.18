#!/usr/bin/env python3
"""Build an ARM64 entry shim with the mainline kernel/DTB inside it."""
import argparse
import os
import json
from pathlib import Path
import struct
import subprocess
import re

ROOT=Path(__file__).resolve().parents[2]
TOOLROOT=ROOT.parent/'tools'
os.environ['PATH']=str(TOOLROOT/'llvm18/usr/lib/llvm-18/bin')+':'+str(TOOLROOT/'host-build/usr/bin')+':'+os.environ['PATH']
os.environ['LD_LIBRARY_PATH']=str(TOOLROOT/'host-build/usr/lib/x86_64-linux-gnu')+':'+os.environ.get('LD_LIBRARY_PATH','')
LIBFDT=ROOT/'scripts/dtc/libfdt'
SOURCES=['fdt.c','fdt_ro.c','fdt_rw.c','fdt_sw.c','fdt_wip.c','fdt_empty_tree.c','fdt_addresses.c']
WORKSPACE=0x40000


def build(kernel, dtb, directory):
    directory=directory.resolve()
    directory.mkdir(parents=True,exist_ok=True)
    kernel=kernel.resolve(); dtb=dtb.resolve()
    data=kernel.read_bytes()
    if data[56:60]!=b'ARM\x64': raise ValueError('Invalid ARM64 Image')
    text_offset,image_size,flags=struct.unpack_from('<QQQ',data,8)
    if text_offset!=0 or flags!=0xa: raise ValueError('Expected 4K little-endian Image with text_offset=0')
    if image_size<len(data): raise ValueError('Kernel footprint smaller than file')
    if any('"' in str(p) or '\n' in str(p) for p in (kernel,dtb)): raise ValueError('Unsupported assembly path')
    footprint=(image_size+65535)//65536*65536
    payload=directory/'payload.S'
    payload.write_text(f'''.section .payload,"awx"
.global __kernel_start, __dtb_template, __dtb_work, __stack_top, __shim_end
__kernel_start:
.incbin "{kernel}"
.space {footprint-len(data)}
.balign 4096
__dtb_template:
.incbin "{dtb}"
.balign 4096
__dtb_work:
.space {WORKSPACE}
.balign 16
.space 0x4000
__stack_top:
.balign 4096
__shim_end:
''')
    flags=['--target=aarch64-none-elf','-ffreestanding','-fno-builtin','-fno-stack-protector',
           '-fno-asynchronous-unwind-tables','-fno-unwind-tables','-fno-jump-tables',
           '-mgeneral-regs-only','-mstrict-align','-Os','-Wall','-Wextra',
           '-I'+str(LIBFDT),'-include',str(ROOT/'miatoll/boot/shim/env.h')]
    sources=[ROOT/'miatoll/boot/shim/entry.S',ROOT/'miatoll/boot/shim/fdt_handoff.c',ROOT/'miatoll/boot/shim/runtime.c',
             *[LIBFDT/name for name in SOURCES],payload]
    objects=[]
    for index,source in enumerate(sources):
        obj=directory/f'{index}-{source.stem}.o'
        subprocess.run(['clang',*flags,'-c',str(source),'-o',str(obj)],check=True)
        if source.suffix=='.c':
            relocations=subprocess.check_output(['llvm-readelf','-r',str(obj)],text=True)
            if re.search(r'R_AARCH64_(ABS64|ABS32|ABS16|.*GOT)',relocations):
                raise ValueError('Raw-image-unsafe absolute/GOT pointer relocation: '+str(source))
        objects.append(str(obj))
    elf=directory/'bootshim.elf'
    subprocess.run(['ld.lld','-T',str(ROOT/'miatoll/boot/shim/link.ld'),'-o',str(elf),*objects],check=True)
    binary=directory/'bootshim.bin'
    subprocess.run(['llvm-objcopy','-O','binary',str(elf),str(binary)],check=True)
    raw=binary.read_bytes()
    if raw[56:60]!=b'ARM\x64' or raw[0x180000:0x180000+len(data)]!=data:
        raise ValueError('Invalid embedded kernel')
    if struct.unpack_from('<Q',raw,16)[0]!=len(raw): raise ValueError('Shim footprint mismatch')
    summary=dict(shim_bytes=len(raw),kernel_file_bytes=len(data),kernel_runtime_bytes=image_size,
                 kernel_offset=0x180000,legacy_text_offset=0x80000,dtb_bytes=dtb.stat().st_size,
                 dtb_workspace_bytes=WORKSPACE,hardware_tested=False)
    (directory/'layout.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
    return binary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kernel',type=Path,default=ROOT.parent/'dist/miatoll-boot1/kernel/Image')
    parser.add_argument('--dtb',type=Path,default=ROOT.parent/'out-miatoll-boot1/arch/arm64/boot/dts/qcom/sm7125-xiaomi-curtana-boot1.dtb')
    parser.add_argument('--out',type=Path,default=ROOT.parent/'out-miatoll-boot1-shim')
    args=parser.parse_args()
    build(args.kernel,args.dtb,args.out)
