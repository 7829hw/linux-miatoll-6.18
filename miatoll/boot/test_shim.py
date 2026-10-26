#!/usr/bin/env python3
"""Execute the actual ARM64 shim under QEMU with a mock kernel entry."""
import ctypes
import importlib.util
from pathlib import Path
import subprocess
import hashlib
import json
import argparse

ROOT=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--dtb',type=Path,default=ROOT.parent/'out-miatoll-boot1/arch/arm64/boot/dts/qcom/sm7125-xiaomi-curtana-boot1.dtb')
parser.add_argument('--output-dir',type=Path,default=ROOT.parent/'out-miatoll-boot1-shim-test')
args=parser.parse_args()
spec=importlib.util.spec_from_file_location('build_bootshim',ROOT/'miatoll/boot/build_shim.py')
builder=importlib.util.module_from_spec(spec); spec.loader.exec_module(builder)
out=args.output_dir.resolve(); out.mkdir(parents=True,exist_ok=True)
libfdt=builder.LIBFDT
sources=[str(libfdt/name) for name in builder.SOURCES]
common=['--target=aarch64-none-elf','-ffreestanding','-fno-builtin','-fno-stack-protector',
        '-fno-unwind-tables','-fno-asynchronous-unwind-tables','-mgeneral-regs-only','-Os',
        '-I'+str(libfdt),'-include',str(ROOT/'miatoll/boot/shim/env.h')]
objects=[]
for index,source in enumerate([str(ROOT/'miatoll/boot/shim/mock_kernel.S'),str(ROOT/'miatoll/boot/shim/mock_kernel.c'),
                              str(ROOT/'miatoll/boot/shim/runtime.c'),*sources]):
    obj=out/f'mock-{index}.o'
    subprocess.run(['clang',*common,'-c',source,'-o',str(obj)],check=True)
    objects.append(str(obj))
link=out/'mock.ld'
link.write_text('ENTRY(_start)\nSECTIONS { . = 0; .text : { KEEP(*(.image_header)) *(.text*) *(.rodata*) } .data : { *(.data*) *(.bss*) } /DISCARD/ : { *(.eh_frame*) *(.note*) *(.comment) } }\n')
subprocess.run(['ld.lld','-T',str(link),'-o',str(out/'mock.elf'),*objects],check=True)
subprocess.run(['llvm-objcopy','-O','binary',str(out/'mock.elf'),str(out/'mock.Image')],check=True)
fixture=out/'firmware.dts'
fixture.write_text('''/dts-v1/;
/memreserve/ 0x90000000 0x1000;
/ {
 #address-cells=<2>; #size-cells=<2>; compatible="qcom,cust-atoll";
 chosen { bootargs="rdinit=/init bootshim_test=1";
 linux,initrd-start=/bits/ 64 <0xa8000000>;
 linux,initrd-end=/bits/ 64 <0xa8100000>; };
 memory@80000000 { device_type="memory"; reg=<0 0x80000000 0 0x40000000 1 0 0 0x40000000>; };
 reserved-memory { #address-cells=<2>; #size-cells=<2>; ranges;
  firmware@9e000000 { reg=<0 0x9e000000 0 0x200000>; no-map; };
  hyp@80000000 { reg=<0 0x80000000 0 0x600000>; no-map; };
 };
 downstream-only { compatible="test,do-not-copy"; };
};
''')
firmware=out/'firmware.dtb'
subprocess.run(['dtc','-I','dts','-O','dtb','-o',str(firmware),str(fixture)],check=True)
template=args.dtb.resolve()
binary=builder.build(out/'mock.Image',template,out/'shim')
harness=out/'harness.c'
harness.write_text('''#include "env.h"
extern unsigned char test_shim[],test_shim_end[],test_fdt[];
static long call(long n,long a,long b,long c,long d,long e,long f) {
 register long x8 __asm__("x8")=n; register long x0 __asm__("x0")=a;
 register long x1 __asm__("x1")=b; register long x2 __asm__("x2")=c;
 register long x3 __asm__("x3")=d; register long x4 __asm__("x4")=e;
 register long x5 __asm__("x5")=f;
 __asm__ volatile("svc #0" : "+r"(x0) : "r"(x8),"r"(x1),"r"(x2),"r"(x3),"r"(x4),"r"(x5) : "memory"); return x0;
}
void _start(void) {
 size_t size=test_shim_end-test_shim;
 long address=call(222,0x84080000,(size+4095)&~4095UL,7,0x32,-1,0);
 if(address<0) { call(93,90,0,0,0,0,0); for(;;); }
 memcpy((void *)address,test_shim,size);
 ((void (*)(const void *))address)(test_fdt);
 call(93,91,0,0,0,0,0); for(;;);
}
''')
data=out/'harness_data.S'
data.write_text(f'''.section .rodata,"a"
.global test_shim,test_shim_end,test_fdt
test_shim:
.incbin "{binary}"
test_shim_end:
.balign 8
test_fdt:
.incbin "{firmware}"
''')
objs=[]
for index,source in enumerate((harness,ROOT/'miatoll/boot/shim/runtime.c',data)):
    obj=out/f'harness-{index}.o'
    subprocess.run(['clang',*common,'-I'+str(ROOT/'miatoll/boot/shim'),'-c',str(source),'-o',str(obj)],check=True)
    objs.append(str(obj))
executable=out/'handoff-test.elf'
subprocess.run(['ld.lld','-static','-Ttext=0x1000000','--entry=_start','-o',str(executable),*objs],check=True)
subprocess.run([str(ROOT.parent/'tools/qemu/qemu-aarch64-static'),str(executable)],check=True,timeout=20)
print('PASS: real ARM64 shim reached aligned mock kernel with x1-x3=0, mainline FDT, and firmware reservations')
# Host execution of the same C routine covers rejected firmware inputs.
shared=out/'libhandoff.so'
subprocess.run(['cc','-shared','-fPIC','-O2','-I'+str(libfdt),str(ROOT/'miatoll/boot/shim/fdt_handoff.c'),
                *sources,'-o',str(shared)],check=True)
library=ctypes.CDLL(str(shared))
fn=library.shim_prepare_fdt
fn.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int]
fn.restype=ctypes.c_int
source=ctypes.create_string_buffer(firmware.read_bytes())
target_template=ctypes.create_string_buffer(template.read_bytes())
destination=ctypes.create_string_buffer(0x100000)
assert fn(source,target_template,destination,len(destination))==0
assert fn(source,target_template,destination,16)<0
bad=ctypes.create_string_buffer(b'bad FDT header'+bytes(64))
assert fn(bad,target_template,destination,len(destination))<0
for prop in ('linux,initrd-end','linux,initrd-start'):
    missing=out/f'missing-{prop.rsplit(",",1)[-1]}.dtb'
    missing.write_bytes(firmware.read_bytes())
    subprocess.run(['fdtput','-d',str(missing),'/chosen',prop],check=True)
    buffer=ctypes.create_string_buffer(missing.read_bytes())
    assert fn(buffer,target_template,destination,len(destination))<0
print('PASS: host handoff validation rejects invalid FDT, small workspace, and missing initrd bounds')
checked=[ROOT/'miatoll/boot/shim'/name for name in ('env.h','entry.S','runtime.c','fdt_handoff.c',
                                                 'link.ld','mock_kernel.S','mock_kernel.c')]
checked+=[ROOT/'miatoll/boot/build_shim.py',Path(__file__).resolve()]
result=dict(arm64_emulation_passed=True,host_validation_passed=True,linux_kernel_executed=False,
            template_sha256=hashlib.sha256(template.read_bytes()).hexdigest(),
            sources={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in checked})
(out/'test-result.json').write_text(json.dumps(result,indent=2)+'\n')
