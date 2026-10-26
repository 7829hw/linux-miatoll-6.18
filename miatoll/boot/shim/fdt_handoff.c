/* SPDX-License-Identifier: BSD-2-Clause */
#include <libfdt.h>

#define MAX_REG_BYTES 1024
#define MAX_SOURCE_DTB (4 * 1024 * 1024)
#define MAX_RANGES 128
struct range { uint64_t start,end; };

static int carry_firmware_reservations(const void *source,void *target)
{
    int from=fdt_path_offset(source,"/reserved-memory");
    int to=fdt_path_offset(target,"/reserved-memory"),node,len,count=0,ret;
    struct range existing[MAX_RANGES],pieces[MAX_RANGES];
    if (from<0) return 0;
    if (to<0) return to;
    const char digits[]="0123456789abcdef";
    fdt_for_each_subnode(node,target,to) {
        const fdt64_t *reg=fdt_getprop(target,node,"reg",&len);
        if (!reg) continue;
        if (len<0 || len%16) return -FDT_ERR_BADVALUE;
        for(int i=0;i<len/8;i+=2) {
            uint64_t a=fdt64_ld(reg+i),s=fdt64_ld(reg+i+1);
            if(!s) continue;
            if(a+s<a || count==MAX_RANGES) return -FDT_ERR_BADVALUE;
            existing[count++]=(struct range){a,a+s};
        }
    }
    fdt_for_each_subnode(node,source,from) {
        if(fdt_getprop(source,node,"reusable",&len)) continue;
        int nomap=fdt_getprop(source,node,"no-map",&len)!=NULL;
        const fdt64_t *reg=fdt_getprop(source,node,"reg",&len);
        if(!reg) continue; /* Dynamic pools are allocated by their driver. */
        if(len<=0 || len%16) return -FDT_ERR_BADVALUE;
        for(int i=0;i<len/8;i+=2) {
            uint64_t a=fdt64_ld(reg+i),s=fdt64_ld(reg+i+1);
            int n=1;
            if(!s || a+s<a) return -FDT_ERR_BADVALUE;
            pieces[0]=(struct range){a,a+s};
            for(int j=0;j<count;j++) {
                int before=n;
                for(int k=0;k<before;k++) {
                    struct range p=pieces[k],r=existing[j];
                    if(p.start==p.end || r.end<=p.start || r.start>=p.end) continue;
                    if(r.start<=p.start) pieces[k].start=r.end<p.end?r.end:p.end;
                    else {
                        pieces[k].end=r.start;
                        if(r.end<p.end) {
                            if(n==MAX_RANGES) return -FDT_ERR_NOSPACE;
                            pieces[n++]=(struct range){r.end,p.end};
                        }
                    }
                }
            }
            for(int k=0;k<n;k++) {
                struct range p=pieces[k];
                if(p.start==p.end) continue;
                char name[48]="firmware-reserved@";
                int pos=18,started=0;
                for(int shift=60;shift>=0;shift-=4) {
                    unsigned digit=(p.start>>shift)&15;
                    if(digit || started || shift==0) { name[pos++]=digits[digit]; started=1; }
                }
                name[pos]=0;
                to=fdt_path_offset(target,"/reserved-memory");
                int child=fdt_add_subnode(target,to,name);
                if(child<0) return child;
                fdt64_t values[2]={cpu_to_fdt64(p.start),cpu_to_fdt64(p.end-p.start)};
                if((ret=fdt_setprop(target,child,"reg",values,sizeof(values)))) return ret;
                if(nomap && (ret=fdt_setprop(target,child,"no-map",NULL,0))) return ret;
                if(count==MAX_RANGES) return -FDT_ERR_NOSPACE;
                existing[count++]=p;
            }
        }
    }
    return 0;
}

static int root_cells(const void *fdt)
{
    int len;
    const fdt32_t *a=fdt_getprop(fdt,0,"#address-cells",&len);
    if (!a || len!=4 || fdt32_to_cpu(*a)!=2) return -FDT_ERR_BADNCELLS;
    const fdt32_t *s=fdt_getprop(fdt,0,"#size-cells",&len);
    return (!s || len!=4 || fdt32_to_cpu(*s)!=2) ? -FDT_ERR_BADNCELLS : 0;
}

static int is_memory(const void *fdt, int node)
{
    int len;
    const char *type=fdt_getprop(fdt,node,"device_type",&len);
    return type && len==7 && !memcmp(type,"memory",7);
}

/* Only firmware-populated boot parameters cross the DT boundary. Device
 * nodes from the downstream tree are never copied into the mainline tree. */
int shim_prepare_fdt(const void *source, const void *template, void *target, int capacity)
{
    int ret, len, source_chosen, target_chosen, node, memory=-1, used=0;
    unsigned char registers[MAX_REG_BYTES];
    /* Fixed arrays avoid absolute pointer relocations in a raw ARM64 Image. */
    static const char properties[][32]={"bootargs","linux,initrd-start",
        "linux,initrd-end","kaslr-seed","rng-seed"};
    if (!source || !template || !target || capacity<65536) return -FDT_ERR_BADVALUE;
    if ((ret=fdt_check_header(source)) || (ret=fdt_check_header(template))) return ret;
    if (fdt_totalsize(source)>MAX_SOURCE_DTB || fdt_totalsize(template)>(unsigned)capacity)
        return -FDT_ERR_NOSPACE;
    if ((ret=root_cells(source)) || (ret=root_cells(template))) return ret;
    if (fdt_node_check_compatible(template,0,"xiaomi,curtana")) return -FDT_ERR_BADVALUE;
    source_chosen=fdt_path_offset(source,"/chosen");
    if (source_chosen<0) return source_chosen;
    for (unsigned i=1;i<=2;i++) {
        const void *value=fdt_getprop(source,source_chosen,properties[i],&len);
        if (!value || (len!=4 && len!=8)) return -FDT_ERR_BADVALUE;
    }
    fdt_for_each_subnode(node,source,0) {
        if (!is_memory(source,node)) continue;
        const void *reg=fdt_getprop(source,node,"reg",&len);
        if (!reg || len<=0 || len%16 || len>MAX_REG_BYTES-used) return -FDT_ERR_BADVALUE;
        for (int offset=0;offset<len;offset+=16) {
            const unsigned char *entry=(const unsigned char *)reg+offset;
            uint64_t start=fdt64_ld((const fdt64_t *)entry);
            uint64_t size=fdt64_ld((const fdt64_t *)(entry+8));
            if (!size || start+size<start) return -FDT_ERR_BADVALUE;
        }
        memcpy(registers+used,reg,len);
        used+=len;
    }
    if (!used) return -FDT_ERR_BADVALUE;
    if ((ret=fdt_open_into(template,target,capacity))) return ret;
    fdt_for_each_subnode(node,target,0) {
        if (is_memory(target,node)) {
            if (memory>=0) return -FDT_ERR_BADVALUE;
            memory=node;
        }
    }
    if (memory<0) return -FDT_ERR_NOTFOUND;
    if ((ret=fdt_setprop(target,memory,"reg",registers,used))) return ret;
    target_chosen=fdt_path_offset(target,"/chosen");
    if (target_chosen<0) return target_chosen;
    for (unsigned i=0;i<sizeof(properties)/sizeof(properties[0]);i++) {
        const void *value=fdt_getprop(source,source_chosen,properties[i],&len);
        if (!value) continue;
        if (len<=0 || len>8192) return -FDT_ERR_BADVALUE;
        if (i==0 && ((const char *)value)[len-1]) return -FDT_ERR_BADVALUE;
        if ((ret=fdt_setprop(target,target_chosen,properties[i],value,len))) return ret;
    }
    if ((ret=carry_firmware_reservations(source,target))) return ret;
    int count=fdt_num_mem_rsv(source);
    if (count<0 || count>128) return -FDT_ERR_BADVALUE;
    for (int i=0;i<count;i++) {
        uint64_t address,size;
        if ((ret=fdt_get_mem_rsv(source,i,&address,&size))) return ret;
        if (address+size<address) return -FDT_ERR_BADVALUE;
        if ((ret=fdt_add_mem_rsv(target,address,size))) return ret;
    }
    /* Keep the live FDT workspace out of Linux's page allocator. */
    if ((ret=fdt_add_mem_rsv(target,(uintptr_t)target,capacity))) return ret;
    return fdt_pack(target);
}
