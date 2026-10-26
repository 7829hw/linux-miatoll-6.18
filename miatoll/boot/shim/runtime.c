/* SPDX-License-Identifier: BSD-2-Clause */
#include "env.h"
void *memcpy(void *d, const void *s, size_t n)
{ unsigned char *p=d; const unsigned char *q=s; for (size_t i=0;i<n;i++) p[i]=q[i]; return d; }
void *memmove(void *d, const void *s, size_t n)
{ if ((uintptr_t)d < (uintptr_t)s) return memcpy(d,s,n); unsigned char *p=d; const unsigned char *q=s; while(n) { n--; p[n]=q[n]; } return d; }
void *memset(void *d, int c, size_t n)
{ unsigned char *p=d; for(size_t i=0;i<n;i++) p[i]=(unsigned char)c; return d; }
int memcmp(const void *a, const void *b, size_t n)
{ const unsigned char *p=a,*q=b; for(size_t i=0;i<n;i++) if(p[i]!=q[i]) return p[i]-q[i]; return 0; }
int strcmp(const char *a, const char *b)
{ while(*a && *a==*b) { a++; b++; } return (unsigned char)*a-(unsigned char)*b; }
int strncmp(const char *a, const char *b, size_t n)
{ for(size_t i=0;i<n;i++) { if(a[i]!=b[i]) return (unsigned char)a[i]-(unsigned char)b[i]; if(!a[i]) break; } return 0; }
size_t strlen(const char *s) { size_t n=0; while(s[n]) n++; return n; }
size_t strnlen(const char *s,size_t m) { size_t n=0; while(n<m && s[n]) n++; return n; }
char *strchr(const char *s,int c)
{ do { if(*s==(char)c) return (char *)s; } while(*s++); return NULL; }
char *strrchr(const char *s,int c)
{ const char *p=NULL; do { if(*s==(char)c) p=s; } while(*s++); return (char *)p; }
void *memchr(const void *s,int c,size_t n)
{ const unsigned char *p=s; for(size_t i=0;i<n;i++) if(p[i]==(unsigned char)c) return (void *)(p+i); return NULL; }
