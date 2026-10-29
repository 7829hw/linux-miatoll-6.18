// SPDX-License-Identifier: GPL-2.0
/*
 * Raw CAMSS capture probe for the miatoll RAM tests.
 *
 * Links sensor -> CSIPHY -> CSID<n> -> VFE<n> RDI0 -> video node through
 * the media controller, after disabling the CSIPHY/CSID links of earlier
 * runs, propagates the sensor format, streams a few frames
 * from the RDI video node and prints simple statistics of each frame. The
 * last frame is written raw to OUT. No ISP: the data is the sensor's Bayer
 * output as packed by the VFE write master.
 *
 * usage: cam-capture SENSOR CSID VFE FRAMES OUT
 *   SENSOR is a substring of the sensor entity name, e.g. "s5kgm2".
 */
#include <errno.h>
#include <fcntl.h>
#include <glob.h>
#include <linux/media.h>
#include <linux/v4l2-subdev.h>
#include <linux/videodev2.h>
#include <poll.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <unistd.h>

#define MAX_ENTITIES 128
#define NUM_BUFS 4

static struct media_entity_desc entities[MAX_ENTITIES];
static int num_entities;

static void die(const char *what)
{
	fprintf(stderr, "cam-capture: %s: %s\n", what, strerror(errno));
	exit(1);
}

static const struct media_entity_desc *find_entity(const char *name, int exact)
{
	for (int i = 0; i < num_entities; i++)
		if (exact ? !strcmp(entities[i].name, name) : !!strstr(entities[i].name, name))
			return &entities[i];
	fprintf(stderr, "cam-capture: no entity %s\n", name);
	exit(1);
}

/* Device node of an entity, matched by its character device number */
static int open_node(const struct media_entity_desc *e)
{
	const char *patterns[] = { "/dev/v4l-subdev*", "/dev/video*" };
	dev_t want = makedev(e->dev.major, e->dev.minor);

	for (int p = 0; p < 2; p++) {
		glob_t g;

		if (glob(patterns[p], 0, NULL, &g))
			continue;
		for (size_t i = 0; i < g.gl_pathc; i++) {
			struct stat st;

			if (!stat(g.gl_pathv[i], &st) && st.st_rdev == want) {
				int fd = open(g.gl_pathv[i], O_RDWR);

				globfree(&g);
				if (fd < 0)
					die(e->name);
				return fd;
			}
		}
		globfree(&g);
	}
	fprintf(stderr, "cam-capture: no device node for %s\n", e->name);
	exit(1);
}

static void setup_link(int media, const struct media_entity_desc *src, int src_pad,
		       const struct media_entity_desc *sink, int sink_pad)
{
	struct media_link_desc link = {
		.source = { .entity = src->id, .index = src_pad },
		.sink = { .entity = sink->id, .index = sink_pad },
		.flags = MEDIA_LNK_FL_ENABLED,
	};

	if (ioctl(media, MEDIA_IOC_SETUP_LINK, &link))
		die("MEDIA_IOC_SETUP_LINK");
	printf("link %s:%d -> %s:%d\n", src->name, src_pad, sink->name, sink_pad);
}

/* Disable the enabled CSIPHY -> CSID and CSID -> VFE links of earlier runs */
static void reset_links(int media)
{
	for (int i = 0; i < num_entities; i++) {
		struct media_pad_desc pads[16];
		struct media_link_desc links[32];
		struct media_links_enum le = { .entity = entities[i].id, .pads = pads, .links = links };

		if (strncmp(entities[i].name, "msm_csi", 7) || entities[i].pads > 16 ||
		    entities[i].links > 32 || ioctl(media, MEDIA_IOC_ENUM_LINKS, &le))
			continue;
		for (int j = 0; j < entities[i].links; j++) {
			if (links[j].source.entity != entities[i].id ||
			    !(links[j].flags & MEDIA_LNK_FL_ENABLED) ||
			    (links[j].flags & MEDIA_LNK_FL_IMMUTABLE))
				continue;
			links[j].flags &= ~MEDIA_LNK_FL_ENABLED;
			if (ioctl(media, MEDIA_IOC_SETUP_LINK, &links[j]))
				die("MEDIA_IOC_SETUP_LINK reset");
		}
	}
}

/* The CSIPHY whose sink pad the sensor's source pad links to */
static const struct media_entity_desc *sensor_phy(int media, const struct media_entity_desc *sensor)
{
	struct media_pad_desc pads[8];
	struct media_link_desc links[8];
	struct media_links_enum le = { .entity = sensor->id, .pads = pads, .links = links };

	if (sensor->links > 8 || ioctl(media, MEDIA_IOC_ENUM_LINKS, &le))
		die("MEDIA_IOC_ENUM_LINKS");
	for (int i = 0; i < sensor->links; i++)
		for (int j = 0; j < num_entities; j++)
			if (entities[j].id == links[i].sink.entity)
				return &entities[j];
	fprintf(stderr, "cam-capture: %s has no link\n", sensor->name);
	exit(1);
}

static struct v4l2_mbus_framefmt get_fmt(int fd, int pad)
{
	struct v4l2_subdev_format f = { .which = V4L2_SUBDEV_FORMAT_ACTIVE, .pad = pad };

	if (ioctl(fd, VIDIOC_SUBDEV_G_FMT, &f))
		die("VIDIOC_SUBDEV_G_FMT");
	return f.format;
}

static void set_fmt(int fd, const char *name, int pad, struct v4l2_mbus_framefmt fmt)
{
	struct v4l2_subdev_format f = {
		.which = V4L2_SUBDEV_FORMAT_ACTIVE, .pad = pad, .format = fmt,
	};

	if (ioctl(fd, VIDIOC_SUBDEV_S_FMT, &f))
		die("VIDIOC_SUBDEV_S_FMT");
	printf("fmt %s:%d %ux%u code 0x%04x\n", name, pad, f.format.width,
	       f.format.height, f.format.code);
}

int main(int argc, char **argv)
{
	if (argc != 6) {
		fprintf(stderr, "usage: %s SENSOR CSID VFE FRAMES OUT\n", argv[0]);
		return 2;
	}
	int nframes = atoi(argv[4]);
	char name[64];
	int media = open("/dev/media0", O_RDWR);

	if (media < 0)
		die("/dev/media0");
	for (num_entities = 0; num_entities < MAX_ENTITIES; num_entities++) {
		struct media_entity_desc *e = &entities[num_entities];

		e->id = (num_entities ? entities[num_entities - 1].id : 0) | MEDIA_ENT_ID_FLAG_NEXT;
		if (ioctl(media, MEDIA_IOC_ENUM_ENTITIES, e))
			break;
	}

	const struct media_entity_desc *sensor = find_entity(argv[1], 0);
	const struct media_entity_desc *phy = sensor_phy(media, sensor);
	snprintf(name, sizeof(name), "msm_csid%s", argv[2]);
	const struct media_entity_desc *csid = find_entity(name, 1);
	snprintf(name, sizeof(name), "msm_vfe%s_rdi0", argv[3]);
	const struct media_entity_desc *rdi = find_entity(name, 1);
	snprintf(name, sizeof(name), "msm_vfe%s_video0", argv[3]);
	const struct media_entity_desc *video = find_entity(name, 1);

	reset_links(media);
	setup_link(media, phy, 1, csid, 0);
	setup_link(media, csid, 1, rdi, 0);

	int sensor_fd = open_node(sensor), phy_fd = open_node(phy);
	int csid_fd = open_node(csid), rdi_fd = open_node(rdi);
	struct v4l2_mbus_framefmt fmt = get_fmt(sensor_fd, 0);

	printf("sensor %s %ux%u code 0x%04x via %s\n", sensor->name, fmt.width,
	       fmt.height, fmt.code, phy->name);
	set_fmt(phy_fd, phy->name, 0, fmt);
	set_fmt(csid_fd, csid->name, 0, get_fmt(phy_fd, 1));
	set_fmt(rdi_fd, rdi->name, 0, get_fmt(csid_fd, 1));
	fmt = get_fmt(rdi_fd, 1);

	int vfd = open_node(video);
	struct v4l2_fmtdesc desc = {
		.type = V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE, .mbus_code = fmt.code,
	};
	if (ioctl(vfd, VIDIOC_ENUM_FMT, &desc))
		die("VIDIOC_ENUM_FMT");

	struct v4l2_format vf = { .type = V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE };
	vf.fmt.pix_mp.width = fmt.width;
	vf.fmt.pix_mp.height = fmt.height;
	vf.fmt.pix_mp.pixelformat = desc.pixelformat;
	vf.fmt.pix_mp.field = V4L2_FIELD_NONE;
	vf.fmt.pix_mp.num_planes = 1;
	if (ioctl(vfd, VIDIOC_S_FMT, &vf))
		die("VIDIOC_S_FMT");
	printf("video %s %ux%u %.4s bytesperline %u sizeimage %u\n", video->name,
	       vf.fmt.pix_mp.width, vf.fmt.pix_mp.height, (char *)&vf.fmt.pix_mp.pixelformat,
	       vf.fmt.pix_mp.plane_fmt[0].bytesperline, vf.fmt.pix_mp.plane_fmt[0].sizeimage);

	struct v4l2_requestbuffers req = {
		.count = NUM_BUFS, .type = vf.type, .memory = V4L2_MEMORY_MMAP,
	};
	if (ioctl(vfd, VIDIOC_REQBUFS, &req))
		die("VIDIOC_REQBUFS");
	void *mem[NUM_BUFS];
	size_t len[NUM_BUFS];
	for (unsigned int i = 0; i < req.count; i++) {
		struct v4l2_plane plane;
		struct v4l2_buffer b = {
			.type = vf.type, .memory = V4L2_MEMORY_MMAP, .index = i,
			.m.planes = &plane, .length = 1,
		};

		if (ioctl(vfd, VIDIOC_QUERYBUF, &b))
			die("VIDIOC_QUERYBUF");
		len[i] = plane.length;
		mem[i] = mmap(NULL, plane.length, PROT_READ, MAP_SHARED, vfd, plane.m.mem_offset);
		if (mem[i] == MAP_FAILED)
			die("mmap");
		if (ioctl(vfd, VIDIOC_QBUF, &b))
			die("VIDIOC_QBUF");
	}

	int type = vf.type;
	if (ioctl(vfd, VIDIOC_STREAMON, &type))
		die("VIDIOC_STREAMON");
	printf("streaming\n");

	int got = 0;
	for (; got < nframes; got++) {
		struct pollfd pfd = { .fd = vfd, .events = POLLIN };
		struct v4l2_plane plane;
		struct v4l2_buffer b = {
			.type = vf.type, .memory = V4L2_MEMORY_MMAP, .m.planes = &plane, .length = 1,
		};

		if (poll(&pfd, 1, 3000) <= 0) {
			printf("timeout waiting for frame %d\n", got);
			break;
		}
		if (ioctl(vfd, VIDIOC_DQBUF, &b))
			die("VIDIOC_DQBUF");

		const uint8_t *p = mem[b.index];
		size_t used = plane.bytesused, nonzero = 0;
		uint64_t sum = 0;
		unsigned int lo = 255, hi = 0;
		for (size_t i = 0; i < used; i++) {
			nonzero += p[i] != 0;
			sum += p[i];
			lo = p[i] < lo ? p[i] : lo;
			hi = p[i] > hi ? p[i] : hi;
		}
		printf("frame %d seq %u bytes %zu nonzero %zu min %u max %u mean %.1f ts %ld.%06ld\n",
		       got, b.sequence, used, nonzero, lo, hi, used ? (double)sum / used : 0.0,
		       (long)b.timestamp.tv_sec, (long)b.timestamp.tv_usec);
		if (got == nframes - 1) {
			FILE *out = fopen(argv[5], "wb");

			if (!out || fwrite(p, 1, used, out) != used || fclose(out))
				die(argv[5]);
		}
		if (ioctl(vfd, VIDIOC_QBUF, &b))
			die("VIDIOC_QBUF");
	}

	ioctl(vfd, VIDIOC_STREAMOFF, &type);
	for (unsigned int i = 0; i < req.count; i++)
		munmap(mem[i], len[i]);
	printf("captured %d of %d frames\n", got, nframes);
	return got == nframes ? 0 : 1;
}
