// SPDX-License-Identifier: GPL-2.0-only
/*
 * Minimal Adreno check for the curtana RAM test, through the MSM DRM uapi.
 *
 * gpu-probe [render-node]
 *   Prints the MSM GPU parameters, then submits one command buffer on the
 *   3D pipe that holds a single CP_MEM_WRITE packet writing a known value to
 *   a second buffer. Success means the GMU powered the GPU, the SQE firmware
 *   and zap shader loaded and the command processor executed the packet.
 *   It does not render anything and does not touch the display.
 */
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <time.h>
#include <unistd.h>
#include <drm/drm.h>
#include <drm/msm_drm.h>

#define MAGIC 0xc0ffee18U
#define CP_MEM_WRITE 0x3d

static unsigned int odd_parity(uint32_t val)
{
	return (0x9669 >> (0xf & (val ^ (val >> 4) ^ (val >> 8) ^ (val >> 12) ^
				 (val >> 16) ^ (val >> 20) ^ (val >> 24) ^ (val >> 28)))) & 1;
}

/* PM4 type 7 header, as freedreno's pm4_pkt7_hdr(). */
static uint32_t pkt7(uint32_t opcode, uint32_t count)
{
	return 0x70000000U | count | (odd_parity(count) << 15) |
	       ((opcode & 0x7f) << 16) | (odd_parity(opcode) << 23);
}

static int get_param(int fd, uint32_t param, uint64_t *value)
{
	struct drm_msm_param req = { .pipe = MSM_PIPE_3D0, .param = param };

	if (ioctl(fd, DRM_IOCTL_MSM_GET_PARAM, &req))
		return -errno;
	*value = req.value;
	return 0;
}

static int new_bo(int fd, uint64_t size, uint32_t *handle, uint64_t *iova, void **map)
{
	struct drm_msm_gem_new create = { .size = size, .flags = MSM_BO_WC };
	struct drm_msm_gem_info info = { 0 };

	if (ioctl(fd, DRM_IOCTL_MSM_GEM_NEW, &create))
		return -errno;
	*handle = create.handle;
	info.handle = create.handle;
	info.info = MSM_INFO_GET_IOVA;
	if (ioctl(fd, DRM_IOCTL_MSM_GEM_INFO, &info))
		return -errno;
	*iova = info.value;
	info.info = MSM_INFO_GET_OFFSET;
	info.value = 0;
	if (ioctl(fd, DRM_IOCTL_MSM_GEM_INFO, &info))
		return -errno;
	*map = mmap(NULL, size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, info.value);
	return *map == MAP_FAILED ? -errno : 0;
}

int main(int argc, char **argv)
{
	const char *node = argc > 1 ? argv[1] : "/dev/dri/renderD128";
	static const struct { uint32_t param; const char *name; } params[] = {
		{ MSM_PARAM_GPU_ID, "gpu_id" }, { MSM_PARAM_CHIP_ID, "chip_id" },
		{ MSM_PARAM_GMEM_SIZE, "gmem_size" }, { MSM_PARAM_MAX_FREQ, "max_freq" },
		{ MSM_PARAM_VA_START, "va_start" }, { MSM_PARAM_VA_SIZE, "va_size" },
		{ MSM_PARAM_FAULTS, "faults" },
	};
	struct drm_msm_gem_submit_bo bos[2] = { 0 };
	struct drm_msm_gem_submit_cmd cmd = { 0 };
	struct drm_msm_gem_submit submit = { 0 };
	struct drm_msm_wait_fence wait = { 0 };
	uint32_t cmd_handle, dst_handle;
	uint64_t cmd_iova, dst_iova, value;
	volatile uint32_t *dst;
	struct timespec start, now;
	uint32_t *cs;
	void *map;
	unsigned int i;
	int fd, ret;

	fd = open(node, O_RDWR | O_CLOEXEC);
	if (fd < 0) {
		printf("GPU_PROBE_FAIL open %s errno=%d\n", node, errno);
		return 1;
	}
	for (i = 0; i < sizeof(params) / sizeof(params[0]); i++) {
		ret = get_param(fd, params[i].param, &value);
		if (ret)
			printf("gpu_param %s error=%d\n", params[i].name, ret);
		else
			printf("gpu_param %s=0x%llx (%llu)\n", params[i].name,
			       (unsigned long long)value, (unsigned long long)value);
	}

	ret = new_bo(fd, 4096, &cmd_handle, &cmd_iova, &map);
	if (ret) {
		printf("GPU_PROBE_FAIL cmd bo error=%d\n", ret);
		return 1;
	}
	cs = map;
	ret = new_bo(fd, 4096, &dst_handle, &dst_iova, &map);
	if (ret) {
		printf("GPU_PROBE_FAIL dst bo error=%d\n", ret);
		return 1;
	}
	dst = map;
	dst[0] = 0;
	printf("cmd_iova=0x%llx dst_iova=0x%llx\n", (unsigned long long)cmd_iova,
	       (unsigned long long)dst_iova);

	cs[0] = pkt7(CP_MEM_WRITE, 3);
	cs[1] = (uint32_t)dst_iova;
	cs[2] = (uint32_t)(dst_iova >> 32);
	cs[3] = MAGIC;

	bos[0].flags = MSM_SUBMIT_BO_READ;
	bos[0].handle = cmd_handle;
	bos[0].presumed = cmd_iova;
	bos[1].flags = MSM_SUBMIT_BO_WRITE;
	bos[1].handle = dst_handle;
	bos[1].presumed = dst_iova;
	cmd.type = MSM_SUBMIT_CMD_BUF;
	cmd.submit_idx = 0;
	cmd.size = 4 * sizeof(uint32_t);
	submit.flags = MSM_PIPE_3D0;
	submit.nr_bos = 2;
	submit.nr_cmds = 1;
	submit.bos = (uintptr_t)bos;
	submit.cmds = (uintptr_t)&cmd;

	clock_gettime(CLOCK_MONOTONIC, &start);
	if (ioctl(fd, DRM_IOCTL_MSM_GEM_SUBMIT, &submit)) {
		printf("GPU_PROBE_FAIL submit errno=%d\n", errno);
		return 1;
	}
	wait.fence = submit.fence;
	wait.timeout.tv_sec = start.tv_sec + 5;
	wait.timeout.tv_nsec = start.tv_nsec;
	if (ioctl(fd, DRM_IOCTL_MSM_WAIT_FENCE, &wait)) {
		printf("GPU_PROBE_FAIL wait fence=%u errno=%d\n", submit.fence, errno);
		return 1;
	}
	clock_gettime(CLOCK_MONOTONIC, &now);
	printf("fence=%u done_us=%ld dst=0x%08x\n", submit.fence,
	       (long)((now.tv_sec - start.tv_sec) * 1000000 + (now.tv_nsec - start.tv_nsec) / 1000),
	       dst[0]);
	if (dst[0] != MAGIC) {
		printf("GPU_PROBE_FAIL value mismatch\n");
		return 1;
	}
	printf("GPU_PROBE_OK CP_MEM_WRITE executed\n");
	close(fd);
	return 0;
}
