// SPDX-License-Identifier: MIT
// Fixed quiet native speaker trial; no general mixer setter or file player.
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
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

#define VERSION "curtana speaker-tone revision 2 (fixed quiet 3-second PCM tone, Xiaomi-miatoll card)"
#define RATE 48000U
#define TOTAL_FRAMES (RATE * 3U)
#define PERIOD 1024U
#define BUFFER (PERIOD * 4U)
#define ROUTE "TERT_MI2S_RX Audio Mixer MultiMedia1"

struct control {
    struct snd_ctl_elem_id id;
    snd_ctl_elem_type_t type;
    long saved;
};
static volatile sig_atomic_t stopped;
static void on_signal(int sig) { stopped = sig; }

static int64_t now_ms(void)
{
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t)) return -1;
    return (int64_t)t.tv_sec * 1000 + t.tv_nsec / 1000000;
}

static int read_control(int fd, const struct control *ctl, long *value)
{
    struct snd_ctl_elem_value v = {.id = ctl->id};
    if (ioctl(fd, SNDRV_CTL_IOCTL_ELEM_READ, &v)) return -1;
    *value = ctl->type == SNDRV_CTL_ELEM_TYPE_ENUMERATED ?
             (long)v.value.enumerated.item[0] : v.value.integer.value[0];
    return 0;
}

static int find_control(int fd, const char *name, snd_ctl_elem_type_t type,
                        long maximum, struct control *ctl)
{
    struct snd_ctl_elem_info info = {0};
    info.id.iface = SNDRV_CTL_ELEM_IFACE_MIXER;
    if (strlen(name) >= sizeof(info.id.name)) return -1;
    strcpy((char *)info.id.name, name);
    if (ioctl(fd, SNDRV_CTL_IOCTL_ELEM_INFO, &info)) return -1;
    if (info.type != type || info.count != 1 || info.id.index != 0 ||
        info.id.iface != SNDRV_CTL_ELEM_IFACE_MIXER ||
        strncmp((char *)info.id.name, name, sizeof(info.id.name)) ||
        (info.access & SNDRV_CTL_ELEM_ACCESS_READWRITE) != SNDRV_CTL_ELEM_ACCESS_READWRITE ||
        (info.access & SNDRV_CTL_ELEM_ACCESS_INACTIVE) || !info.id.numid) {
        fprintf(stderr, "Unexpected control metadata: %s\n", name);
        return -1;
    }
    if (type == SNDRV_CTL_ELEM_TYPE_ENUMERATED) {
        if (info.value.enumerated.items != 4) return -1;
        info.value.enumerated.item = 1;
        if (ioctl(fd, SNDRV_CTL_IOCTL_ELEM_INFO, &info) ||
            strncmp(info.value.enumerated.name, "Left", sizeof(info.value.enumerated.name))) return -1;
    } else if (info.value.integer.min != 0 || info.value.integer.max != maximum) {
        fprintf(stderr, "Unexpected control range: %s\n", name);
        return -1;
    }
    ctl->id = info.id;
    ctl->type = type;
    if (read_control(fd, ctl, &ctl->saved)) return -1;
    if (ctl->saved < 0 || ctl->saved > maximum) return -1;
    printf("saved name=\"%s\" value=%ld\n", name, ctl->saved);
    return 0;
}

static int write_control(int fd, const struct control *ctl, long value)
{
    struct snd_ctl_elem_value v = {.id = ctl->id};
    if (ctl->type == SNDRV_CTL_ELEM_TYPE_ENUMERATED)
        v.value.enumerated.item[0] = (unsigned)value;
    else
        v.value.integer.value[0] = value;
    if (ioctl(fd, SNDRV_CTL_IOCTL_ELEM_WRITE, &v)) return -1;
    long actual;
    if (read_control(fd, ctl, &actual) || actual != value) {
        fprintf(stderr, "Control readback mismatch: %.*s\n", (int)sizeof(ctl->id.name), ctl->id.name);
        return -1;
    }
    return 0;
}

static int restore_control(int fd, const struct control *ctl)
{
    for (unsigned attempt = 0; attempt < 3; attempt++) {
        if (!write_control(fd, ctl, ctl->saved)) return 0;
        if (errno != EINTR) break;
    }
    return -1;
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

static int pcm_configure(int fd)
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
    const unsigned values[] = {2, RATE, 16, 32, PERIOD, 4, BUFFER};
    for (unsigned n = 0; n < sizeof(parameters) / sizeof(parameters[0]); n++)
        exact_interval(&p, parameters[n], values[n]);
    if (ioctl(fd, SNDRV_PCM_IOCTL_HW_PARAMS, &p)) return -1;
    const unsigned masks[] = {SNDRV_PCM_ACCESS_RW_INTERLEAVED, SNDRV_PCM_FORMAT_S16_LE, SNDRV_PCM_SUBFORMAT_STD};
    for (unsigned n = 0; n < 3; n++)
        for (unsigned word = 0; word < sizeof(p.masks[n].bits) / sizeof(p.masks[n].bits[0]); word++)
            if (p.masks[n].bits[word] != (word == masks[n] / 32 ? (1U << (masks[n] % 32)) : 0)) {
                fprintf(stderr, "PCM negotiated an unexpected access/format\n"); return -1;
            }
    for (unsigned n = 0; n < sizeof(parameters) / sizeof(parameters[0]); n++) {
        struct snd_interval *i = &p.intervals[parameters[n] - SNDRV_PCM_HW_PARAM_FIRST_INTERVAL];
        if (i->min != values[n] || i->max != values[n] || i->empty || i->openmin || i->openmax) {
            fprintf(stderr, "PCM negotiated an unexpected parameter\n");
            return -1;
        }
    }
    struct snd_pcm_sw_params sw = {
        .period_step = 1, .avail_min = PERIOD, .xfer_align = 1,
        .start_threshold = BUFFER, .stop_threshold = BUFFER,
    };
    if (ioctl(fd, SNDRV_PCM_IOCTL_SW_PARAMS, &sw) ||
        ioctl(fd, SNDRV_PCM_IOCTL_PREPARE, NULL)) return -1;
    printf("pcm_configured=1 rate=%u channels=2 format=S16_LE period_frames=%u buffer_frames=%u\n",
           RATE, PERIOD, BUFFER);
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
        if (TOTAL_FRAMES - 1 - pos < ramp) ramp = TOTAL_FRAMES - 1 - pos;
        int16_t value = (int16_t)(wave[pos % 48] * (int)ramp / 480);
        samples[n * 2] = samples[n * 2 + 1] = value;
    }
}

static int playback(int fd)
{
    unsigned sent = 0;
    int16_t samples[PERIOD * 2];
    int64_t start = now_ms();
    if (start < 0) return -1;
    printf("tone_start=1 duration_ms=3000 frequency_hz=1000 peak_s16=256 amp_gain_raw=0 digital_volume_unchanged=1\n");
    while (sent < TOTAL_FRAMES && !stopped) {
        int64_t now = now_ms();
        if (now < 0 || now - start > 8000) { errno = ETIMEDOUT; return -1; }
        unsigned frames = TOTAL_FRAMES - sent;
        if (frames > PERIOD) frames = PERIOD;
        fill_tone(samples, sent, frames);
        struct snd_xferi x = {.buf = samples, .frames = frames};
        if (ioctl(fd, SNDRV_PCM_IOCTL_WRITEI_FRAMES, &x) < 0) {
            if (errno == EINTR && !stopped) continue;
            if (errno != EAGAIN) return -1;
            struct pollfd pfd = {.fd = fd, .events = POLLOUT};
            int ret = poll(&pfd, 1, 100);
            if (ret < 0 && errno != EINTR) return -1;
            if (ret > 0 && (pfd.revents & (POLLERR | POLLHUP | POLLNVAL))) { errno = EIO; return -1; }
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
        int64_t now = now_ms();
        if (now < 0 || now - start > 8000) { errno = ETIMEDOUT; return -1; }
        struct timespec delay = {.tv_nsec = 10000000};
        nanosleep(&delay, NULL);
    }
    errno = EINTR;
    return -1;
}

static int play(void)
{
    int ctl_fd = -1, pcm_fd = -1, result = 1, dirty = 0, restore_failed = 0;
    struct control gain = {0}, source = {0}, route = {0}, check = {0};
    struct snd_ctl_card_info card = {0};
    struct sigaction action = {.sa_handler = on_signal};
    sigemptyset(&action.sa_mask);
    const int signals[] = {SIGHUP, SIGINT, SIGTERM, SIGALRM};
    for (unsigned n = 0; n < sizeof(signals) / sizeof(signals[0]); n++)
        if (sigaction(signals[n], &action, NULL)) return 1;
    alarm(15);
    ctl_fd = open("/dev/snd/controlC0", O_RDWR | O_CLOEXEC | O_NOFOLLOW);
    if (ctl_fd < 0 || ioctl(ctl_fd, SNDRV_CTL_IOCTL_CARD_INFO, &card)) goto done;
    // The 6.14.7 fork's sm8250 card is named after its DT model.
    if (card.card != 0 || strncmp((char *)card.id, "Xiaomimiatoll", sizeof(card.id)) ||
        strncmp((char *)card.name, "Xiaomi-miatoll", sizeof(card.name))) {
        fprintf(stderr, "Expected Xiaomi-miatoll card 0\n"); goto done;
    }
    if (find_control(ctl_fd, "Amp Gain Volume", SNDRV_CTL_ELEM_TYPE_INTEGER, 28, &gain) ||
        find_control(ctl_fd, "ASI1 Sel", SNDRV_CTL_ELEM_TYPE_ENUMERATED, 3, &source) ||
        find_control(ctl_fd, ROUTE, SNDRV_CTL_ELEM_TYPE_BOOLEAN, 1, &route) ||
        find_control(ctl_fd, "Digital Volume Control", SNDRV_CTL_ELEM_TYPE_INTEGER, 110, &check)) goto done;
    if (route.saved != 0) { fprintf(stderr, "Expected idle speaker route\n"); goto done; }
    for (unsigned n = 2; n <= 8; n++) {
        char name[44];
        snprintf(name, sizeof(name), "TERT_MI2S_RX Audio Mixer MultiMedia%u", n);
        if (find_control(ctl_fd, name, SNDRV_CTL_ELEM_TYPE_BOOLEAN, 1, &check) || check.saved) {
            fprintf(stderr, "Another tertiary MI2S route is enabled or unreadable\n"); goto done;
        }
    }
    for (unsigned n = 0; n < 2; n++)
        if (find_control(ctl_fd, n ? "VSENSE Switch" : "ISENSE Switch", SNDRV_CTL_ELEM_TYPE_BOOLEAN, 1, &check) || check.saved) {
            fprintf(stderr, "Expected idle sense switches\n"); goto done;
        }
    if (stopped) goto done;
    pcm_fd = open("/dev/snd/pcmC0D0p", O_WRONLY | O_NONBLOCK | O_CLOEXEC | O_NOFOLLOW);
    if (pcm_fd < 0) goto done;
    struct snd_pcm_info info = {0};
    if (ioctl(pcm_fd, SNDRV_PCM_IOCTL_INFO, &info) || info.card != 0 || info.device != 0 ||
        info.stream != SNDRV_PCM_STREAM_PLAYBACK || strncmp((char *)info.id, "MultiMedia1", 11)) {
        fprintf(stderr, "Unexpected PCM playback endpoint\n"); goto done;
    }
    dirty = 1; // Even a failed write may have partially changed a control.
    if (stopped || write_control(ctl_fd, &gain, 0) || stopped ||
        write_control(ctl_fd, &source, 1) || stopped || write_control(ctl_fd, &route, 1) ||
        stopped || pcm_configure(pcm_fd) || stopped || playback(pcm_fd)) goto done;
    result = 0;
done:
    if (result) fprintf(stderr, "speaker trial stopped: signal=%d errno=%d (%s)\n", stopped, errno, strerror(errno));
    if (pcm_fd >= 0) {
        // Closing also stops/frees the stream if DROP reports an error.
        if (ioctl(pcm_fd, SNDRV_PCM_IOCTL_DROP, NULL) < 0 && errno != EBADFD) {
            perror("PCM DROP"); result = 1;
        }
        if (close(pcm_fd)) result = 1;
    }
    if (dirty) {
        // Disconnect first, then restore source and gain; never touch the cached DVC.
        if (restore_control(ctl_fd, &route)) restore_failed = 1;
        if (restore_control(ctl_fd, &source)) restore_failed = 1;
        if (restore_control(ctl_fd, &gain)) restore_failed = 1;
        printf("mixer_restored=%d route=%ld source=%ld gain=%ld digital_volume_written=0\n",
               !restore_failed, route.saved, source.saved, gain.saved);
        if (restore_failed) { fprintf(stderr, "Mixer restoration failed; send this output\n"); result = 1; }
    }
    if (ctl_fd >= 0 && close(ctl_fd)) result = 1;
    alarm(0);
    if (stopped) result = 128 + stopped;
    printf("speaker_tone_exit=%d\n", result);
    return result;
}

int main(int argc, char **argv)
{
    setvbuf(stdout, NULL, _IOLBF, 0);
    if (argc == 2 && !strcmp(argv[1], "--version")) { puts(VERSION); return 0; }
    if (argc != 2 || strcmp(argv[1], "--play")) {
        fprintf(stderr, "Usage: %s --version | --play\n", argv[0]); return 2;
    }
    puts(VERSION);
    return play();
}
