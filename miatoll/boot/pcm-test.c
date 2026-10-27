// SPDX-License-Identifier: MIT
// Fixed PCM checks for curtana RAM tests; routing is left to audio-path.
//   pcm-test play DEVICE            quiet 3 s 1 kHz stereo tone to pcmC0D<DEVICE>p
//   pcm-test record DEVICE SECONDS FILE
//                                   48 kHz mono capture from pcmC0D<DEVICE>c to a WAV
// Uses the S16/48 kHz/960-frame period setup confirmed by speaker-tone revision 6.
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <math.h>
#include <poll.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <time.h>
#include <unistd.h>
#include <sound/asound.h>

#define VERSION "curtana pcm-test revision 1 (quiet tone playback, mono capture, 960-frame periods)"
#define RATE 48000U
#define TONE_FRAMES (RATE * 3U)
// q6asm-dai requires period and buffer sizes in multiples of 480 frames.
#define PERIOD 960U
#define BUFFER (PERIOD * 4U)
#define MAX_RECORD_SECONDS 10U

static volatile sig_atomic_t stopped;
static void on_signal(int sig) { stopped = sig; }

static int64_t now_ms(void)
{
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t)) return -1;
    return (int64_t)t.tv_sec * 1000 + t.tv_nsec / 1000000;
}

static void exact_interval(struct snd_pcm_hw_params *p, unsigned parameter, unsigned value)
{
    struct snd_interval *i = &p->intervals[parameter - SNDRV_PCM_HW_PARAM_FIRST_INTERVAL];
    *i = (struct snd_interval){.min = value, .max = value, .integer = 1};
}

static void exact_mask(struct snd_pcm_hw_params *p, unsigned parameter, unsigned bit)
{
    struct snd_mask *m = &p->masks[parameter - SNDRV_PCM_HW_PARAM_FIRST_MASK];
    memset(m, 0, sizeof(*m));
    m->bits[bit / 32] = 1U << (bit % 32);
}

static void print_refine(const char *tag, const struct snd_pcm_hw_params *p)
{
    static const char *const names[] = {"sample_bits", "frame_bits", "channels", "rate",
        "period_time", "period_size", "period_bytes", "periods", "buffer_time", "buffer_size",
        "buffer_bytes", "tick_time"};
    printf("%s format_mask=0x%08x%08x access_mask=0x%08x\n", tag,
           p->masks[SNDRV_PCM_HW_PARAM_FORMAT].bits[1], p->masks[SNDRV_PCM_HW_PARAM_FORMAT].bits[0],
           p->masks[SNDRV_PCM_HW_PARAM_ACCESS].bits[0]);
    for (unsigned n = 0; n < sizeof(names) / sizeof(names[0]); n++)
        printf("%s %s=%u..%u%s\n", tag, names[n], p->intervals[n].min, p->intervals[n].max,
               p->intervals[n].empty ? " empty" : "");
}

// On a rejected configuration, print what the PCM would accept; changes nothing.
static void report_refine(int fd)
{
    struct snd_pcm_hw_params p = {0};
    for (unsigned n = 0; n < sizeof(p.masks) / sizeof(p.masks[0]); n++)
        memset(&p.masks[n], 0xff, sizeof(p.masks[n]));
    for (unsigned n = 0; n < sizeof(p.intervals) / sizeof(p.intervals[0]); n++)
        p.intervals[n].max = UINT_MAX;
    p.rmask = UINT_MAX;
    if (ioctl(fd, SNDRV_PCM_IOCTL_HW_REFINE, &p)) {
        perror("PCM HW_REFINE");
        return;
    }
    print_refine("refine_open", &p);
}

static int pcm_configure(int fd, unsigned channels, int capture)
{
    struct snd_pcm_hw_params p = {0};
    for (unsigned n = 0; n < sizeof(p.masks) / sizeof(p.masks[0]); n++)
        memset(&p.masks[n], 0xff, sizeof(p.masks[n]));
    for (unsigned n = 0; n < sizeof(p.intervals) / sizeof(p.intervals[0]); n++)
        p.intervals[n].max = UINT_MAX;
    p.rmask = UINT_MAX;
    p.info = UINT_MAX;
    exact_mask(&p, SNDRV_PCM_HW_PARAM_ACCESS, SNDRV_PCM_ACCESS_RW_INTERLEAVED);
    exact_mask(&p, SNDRV_PCM_HW_PARAM_FORMAT, SNDRV_PCM_FORMAT_S16_LE);
    exact_mask(&p, SNDRV_PCM_HW_PARAM_SUBFORMAT, SNDRV_PCM_SUBFORMAT_STD);
    const unsigned parameters[] = {SNDRV_PCM_HW_PARAM_CHANNELS, SNDRV_PCM_HW_PARAM_RATE,
        SNDRV_PCM_HW_PARAM_SAMPLE_BITS, SNDRV_PCM_HW_PARAM_FRAME_BITS,
        SNDRV_PCM_HW_PARAM_PERIOD_SIZE, SNDRV_PCM_HW_PARAM_PERIODS, SNDRV_PCM_HW_PARAM_BUFFER_SIZE};
    const unsigned values[] = {channels, RATE, 16, 16 * channels, PERIOD, 4, BUFFER};
    for (unsigned n = 0; n < sizeof(parameters) / sizeof(parameters[0]); n++)
        exact_interval(&p, parameters[n], values[n]);
    if (ioctl(fd, SNDRV_PCM_IOCTL_HW_PARAMS, &p)) {
        int saved = errno;
        report_refine(fd);
        errno = saved;
        return -1;
    }
    for (unsigned n = 0; n < sizeof(parameters) / sizeof(parameters[0]); n++) {
        struct snd_interval *i = &p.intervals[parameters[n] - SNDRV_PCM_HW_PARAM_FIRST_INTERVAL];
        if (i->min != values[n] || i->max != values[n] || i->empty) {
            fprintf(stderr, "PCM negotiated an unexpected parameter\n");
            return -1;
        }
    }
    // Playback starts once the buffer is full; capture starts explicitly.
    struct snd_pcm_sw_params sw = {
        .period_step = 1, .avail_min = PERIOD, .xfer_align = 1,
        .start_threshold = capture ? INT_MAX : BUFFER, .stop_threshold = BUFFER,
    };
    if (ioctl(fd, SNDRV_PCM_IOCTL_SW_PARAMS, &sw) ||
        ioctl(fd, SNDRV_PCM_IOCTL_PREPARE, NULL)) return -1;
    printf("pcm_configured=1 rate=%u channels=%u format=S16_LE period_frames=%u buffer_frames=%u\n",
           RATE, channels, PERIOD, BUFFER);
    return 0;
}

static void fill_tone(int16_t *samples, unsigned offset, unsigned frames)
{
    // 48-sample 1kHz cycle, peak 256/32768 (-42.14 dBFS), equal L/R.
    static const int16_t wave[48] = {
        0,33,66,98,128,156,181,203,222,237,247,254,256,254,247,237,222,203,181,156,128,98,66,33,
        0,-33,-66,-98,-128,-156,-181,-203,-222,-237,-247,-254,-256,-254,-247,-237,-222,-203,-181,-156,-128,-98,-66,-33
    };
    for (unsigned n = 0; n < frames; n++) {
        unsigned pos = offset + n, ramp = 480;
        if (pos < ramp) ramp = pos;
        if (TONE_FRAMES - 1 - pos < ramp) ramp = TONE_FRAMES - 1 - pos;
        int16_t value = (int16_t)(wave[pos % 48] * (int)ramp / 480);
        samples[n * 2] = samples[n * 2 + 1] = value;
    }
}

static int wait_io(int fd, short events)
{
    struct pollfd pfd = {.fd = fd, .events = events};
    int ret = poll(&pfd, 1, 100);
    if (ret < 0 && errno != EINTR) return -1;
    if (ret > 0 && (pfd.revents & (POLLERR | POLLHUP | POLLNVAL))) { errno = EIO; return -1; }
    return 0;
}

static int play(int fd)
{
    unsigned sent = 0;
    int16_t samples[PERIOD * 2];
    int64_t start = now_ms();
    if (start < 0 || pcm_configure(fd, 2, 0)) return -1;
    printf("tone_start=1 duration_ms=3000 frequency_hz=1000 peak_s16=256\n");
    while (sent < TONE_FRAMES && !stopped) {
        int64_t now = now_ms();
        if (now < 0 || now - start > 8000) { errno = ETIMEDOUT; return -1; }
        unsigned frames = TONE_FRAMES - sent;
        if (frames > PERIOD) frames = PERIOD;
        fill_tone(samples, sent, frames);
        struct snd_xferi x = {.buf = samples, .frames = frames};
        if (ioctl(fd, SNDRV_PCM_IOCTL_WRITEI_FRAMES, &x) < 0) {
            if (errno == EINTR && !stopped) continue;
            if (errno != EAGAIN || wait_io(fd, POLLOUT)) return -1;
            continue;
        }
        if (x.result <= 0 || (unsigned long)x.result > frames) { errno = EIO; return -1; }
        sent += (unsigned)x.result;
    }
    if (stopped) { errno = EINTR; return -1; }
    printf("pcm_frames_submitted=%u\n", sent);
    if (ioctl(fd, SNDRV_PCM_IOCTL_DRAIN, NULL) < 0 && errno != EAGAIN) return -1;
    while (!stopped) {
        struct snd_pcm_status status = {0};
        if (ioctl(fd, SNDRV_PCM_IOCTL_STATUS, &status)) return -1;
        if (status.state == SNDRV_PCM_STATE_SETUP) {
            printf("pcm_drain_complete=1 elapsed_ms=%lld\n", (long long)(now_ms() - start));
            return 0;
        }
        if (status.state != SNDRV_PCM_STATE_RUNNING && status.state != SNDRV_PCM_STATE_DRAINING) {
            fprintf(stderr, "Unexpected PCM state during drain: %d\n", status.state);
            errno = EIO;
            return -1;
        }
        if (now_ms() - start > 8000) { errno = ETIMEDOUT; return -1; }
        struct timespec delay = {.tv_nsec = 10000000};
        nanosleep(&delay, NULL);
    }
    errno = EINTR;
    return -1;
}

static int record(int fd, unsigned seconds, const char *path)
{
    unsigned total = RATE * seconds, got = 0;
    int16_t *data = calloc(total, sizeof(*data));
    int out = -1, result = -1;
    if (!data || pcm_configure(fd, 1, 1) || ioctl(fd, SNDRV_PCM_IOCTL_START, NULL)) goto done;
    int64_t start = now_ms();
    printf("capture_start=1 seconds=%u\n", seconds);
    while (got < total && !stopped) {
        if (now_ms() - start > (int64_t)seconds * 1000 + 3000) { errno = ETIMEDOUT; goto done; }
        unsigned frames = total - got;
        if (frames > PERIOD) frames = PERIOD;
        struct snd_xferi x = {.buf = data + got, .frames = frames};
        if (ioctl(fd, SNDRV_PCM_IOCTL_READI_FRAMES, &x) < 0) {
            if (errno == EINTR && !stopped) continue;
            if (errno != EAGAIN || wait_io(fd, POLLIN)) goto done;
            continue;
        }
        if (x.result <= 0 || (unsigned long)x.result > frames) { errno = EIO; goto done; }
        got += (unsigned)x.result;
    }
    if (stopped) { errno = EINTR; goto done; }
    double sum = 0;
    int peak = 0;
    for (unsigned n = 0; n < total; n++) {
        int v = data[n] < 0 ? -data[n] : data[n];
        if (v > peak) peak = v;
        sum += (double)data[n] * data[n];
    }
    double rms = sqrt(sum / total);
    printf("capture_frames=%u peak_s16=%d peak_dbfs=%.1f rms_dbfs=%.1f\n", got, peak,
           peak ? 20 * log10(peak / 32768.0) : -999.0, rms > 0 ? 20 * log10(rms / 32768.0) : -999.0);
    uint32_t bytes = total * 2;
    const struct {
        char riff[4]; uint32_t riff_size; char wave[4]; char fmt[4]; uint32_t fmt_size;
        uint16_t format, channels; uint32_t rate, byte_rate; uint16_t align, bits;
        char data[4]; uint32_t data_size;
    } __attribute__((packed)) header = {{'R','I','F','F'}, 36 + bytes, {'W','A','V','E'}, {'f','m','t',' '}, 16,
        1, 1, RATE, RATE * 2, 2, 16, {'d','a','t','a'}, bytes};
    out = open(path, O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC | O_NOFOLLOW, 0600);
    if (out < 0 || write(out, &header, sizeof(header)) != (ssize_t)sizeof(header) ||
        write(out, data, bytes) != (ssize_t)bytes) goto done;
    printf("capture_file=%s bytes=%u\n", path, (unsigned)sizeof(header) + bytes);
    result = 0;
done:
    if (out >= 0 && close(out)) result = -1;
    free(data);
    return result;
}

int main(int argc, char **argv)
{
    if (argc == 2 && !strcmp(argv[1], "--version")) { puts(VERSION); return 0; }
    int playback = argc == 3 && !strcmp(argv[1], "play");
    int capture = argc == 5 && !strcmp(argv[1], "record");
    unsigned device = argc >= 3 ? (unsigned)strtoul(argv[2], NULL, 10) : 99;
    unsigned seconds = capture ? (unsigned)strtoul(argv[3], NULL, 10) : 0;
    if ((!playback && !capture) || device > 7 || (capture && (seconds < 1 || seconds > MAX_RECORD_SECONDS))) {
        fprintf(stderr, "usage: %s play DEVICE | record DEVICE SECONDS FILE | --version\n", argv[0]);
        return 2;
    }
    struct sigaction action = {.sa_handler = on_signal};
    sigemptyset(&action.sa_mask);
    const int signals[] = {SIGHUP, SIGINT, SIGTERM, SIGALRM};
    for (unsigned n = 0; n < sizeof(signals) / sizeof(signals[0]); n++)
        if (sigaction(signals[n], &action, NULL)) return 1;
    alarm(capture ? seconds + 10 : 15);
    char node[32];
    snprintf(node, sizeof(node), "/dev/snd/pcmC0D%u%c", device, playback ? 'p' : 'c');
    int fd = open(node, (playback ? O_WRONLY : O_RDONLY) | O_NONBLOCK | O_CLOEXEC | O_NOFOLLOW);
    int result = fd < 0 || (playback ? play(fd) : record(fd, seconds, argv[4]));
    if (result) fprintf(stderr, "pcm-test stopped: signal=%d errno=%d (%s)\n", stopped, errno, strerror(errno));
    if (fd >= 0) {
        // Closing also stops/frees the stream if DROP reports an error.
        if (ioctl(fd, SNDRV_PCM_IOCTL_DROP, NULL) < 0 && errno != EBADFD) result = 1;
        if (close(fd)) result = 1;
    }
    alarm(0);
    if (stopped) result = 128 + stopped;
    printf("pcm_test_exit=%d\n", result);
    return result;
}
