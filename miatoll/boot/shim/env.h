/* SPDX-License-Identifier: BSD-2-Clause */
/* Freestanding little-endian environment for the bundled libfdt. */
#ifndef CURTANA_SHIM_ENV_H
#define CURTANA_SHIM_ENV_H
#define SHIM_FDT_CAPACITY 0x40000
#ifndef __ASSEMBLER__
#define LIBFDT_ENV_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#define FDT_FORCE
#define FDT_BITWISE
#define INT_MAX 2147483647
typedef uint16_t fdt16_t;
typedef uint32_t fdt32_t;
typedef uint64_t fdt64_t;
static inline uint16_t fdt16_to_cpu(fdt16_t v) { return __builtin_bswap16(v); }
static inline fdt16_t cpu_to_fdt16(uint16_t v) { return __builtin_bswap16(v); }
static inline uint32_t fdt32_to_cpu(fdt32_t v) { return __builtin_bswap32(v); }
static inline fdt32_t cpu_to_fdt32(uint32_t v) { return __builtin_bswap32(v); }
static inline uint64_t fdt64_to_cpu(fdt64_t v) { return __builtin_bswap64(v); }
static inline fdt64_t cpu_to_fdt64(uint64_t v) { return __builtin_bswap64(v); }
void *memcpy(void *, const void *, size_t);
void *memmove(void *, const void *, size_t);
void *memset(void *, int, size_t);
int memcmp(const void *, const void *, size_t);
int strcmp(const char *, const char *);
int strncmp(const char *, const char *, size_t);
size_t strlen(const char *);
size_t strnlen(const char *, size_t);
char *strchr(const char *, int);
char *strrchr(const char *, int);
void *memchr(const void *, int, size_t);
#endif
#endif
