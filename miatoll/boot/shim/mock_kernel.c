/* SPDX-License-Identifier: BSD-2-Clause */
#include <libfdt.h>
static void finish(int code)
{
    register long x0 __asm__("x0")=code;
    register long x8 __asm__("x8")=93;
    __asm__ volatile("svc #0" : : "r"(x0),"r"(x8) : "memory");
    __builtin_unreachable();
}
void mock_main(const void *tree)
{
    int node,len;
    if (fdt_check_header(tree) || fdt_node_check_compatible(tree,0,"xiaomi,curtana")) finish(22);
    node=fdt_path_offset(tree,"/memory@80000000");
    const fdt64_t *reg=fdt_getprop(tree,node,"reg",&len);
    if (!reg || len!=32 || fdt64_ld(reg)!=0x80000000ULL ||
        fdt64_ld(reg+1)!=0x40000000ULL || fdt64_ld(reg+2)!=0x100000000ULL) finish(23);
    node=fdt_path_offset(tree,"/chosen");
    const char *args=fdt_getprop(tree,node,"bootargs",&len);
    if (!args || strcmp(args,"rdinit=/init bootshim_test=1")) finish(24);
    const fdt64_t *start=fdt_getprop(tree,node,"linux,initrd-start",&len);
    if (!start || len!=8 || fdt64_ld(start)!=0xa8000000ULL) finish(25);
    int reservations=fdt_num_mem_rsv(tree),found=0;
    if (reservations<2) finish(26);
    for(int i=0;i<reservations;i++) {
        uint64_t address,size;
        if (fdt_get_mem_rsv(tree,i,&address,&size)) finish(28);
        if (address==(uintptr_t)tree && size==SHIM_FDT_CAPACITY) found=1;
    }
    if (!found) finish(29);
    node=fdt_path_offset(tree,"/reserved-memory/firmware-reserved@9e000000");
    const fdt64_t *firmware=fdt_getprop(tree,node,"reg",&len);
    if(!firmware || len!=16 || fdt64_ld(firmware)!=0x9e000000ULL ||
       fdt64_ld(firmware+1)!=0x200000ULL) finish(30);
    if(!fdt_getprop(tree,node,"no-map",&len)) finish(31);
    if(fdt_path_offset(tree,"/reserved-memory/firmware-reserved@80000000")>=0) finish(32);
    if (fdt_path_offset(tree,"/downstream-only")>=0) finish(27);
    finish(0);
}
