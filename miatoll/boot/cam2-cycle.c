// SPDX-License-Identifier: GPL-2.0
/*
 * Camera2 open/stream/close cycle probe for the miatoll Android tests.
 *
 * Opens each camera ID given on the command line in turn through the NDK
 * camera API (the same path as camera apps: cameraserver -> camera provider
 * -> libcamera HAL), streams a YUV_420_888 image reader of WIDTHxHEIGHT for
 * SECONDS, counts the frames and closes the camera. Optionally adds a second,
 * larger JPEG reader to exercise the mapped JPEG stream.
 *
 * Known issue: with a YUV_420_888 reader cameraserver never gets output
 * buffers and no frame arrives (see the lineage31 camera record).
 *
 * usage: cam2-cycle WIDTH HEIGHT SECONDS JPEG_WIDTH JPEG_HEIGHT ID...
 *   JPEG_WIDTH/JPEG_HEIGHT 0 0 for a preview-only session.
 */
#include <camera/NdkCameraDevice.h>
#include <camera/NdkCameraManager.h>
#include <media/NdkImageReader.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>

static atomic_int frames;
static atomic_int jpegs;
static atomic_int errors;

static void on_image(void *ctx, AImageReader *reader)
{
	AImage *image = NULL;

	while (AImageReader_acquireNextImage(reader, &image) == AMEDIA_OK) {
		atomic_fetch_add(ctx ? &jpegs : &frames, 1);
		AImage_delete(image);
	}
}

static void on_disconnected(void *ctx, ACameraDevice *dev)
{
	(void)ctx;
	printf("  %s disconnected\n", ACameraDevice_getId(dev));
}

static void on_error(void *ctx, ACameraDevice *dev, int err)
{
	(void)ctx;
	printf("  %s device error %d\n", ACameraDevice_getId(dev), err);
	atomic_fetch_add(&errors, 1);
}

static void on_capture_failed(void *ctx, ACameraCaptureSession *s, ACaptureRequest *r,
			      ACameraCaptureFailure *f)
{
	(void)ctx; (void)s; (void)r; (void)f;
	atomic_fetch_add(&errors, 1);
}

static double now(void)
{
	struct timespec ts;

	clock_gettime(CLOCK_MONOTONIC, &ts);
	return ts.tv_sec + ts.tv_nsec / 1e9;
}

static AImageReader *reader(int w, int h, int format, void *ctx, ANativeWindow **win)
{
	AImageReader *r = NULL;
	AImageReader_ImageListener listener = { ctx, on_image };

	if (AImageReader_new(w, h, format, 4, &r) != AMEDIA_OK)
		return NULL;
	AImageReader_setImageListener(r, &listener);
	AImageReader_getWindow(r, win);
	return r;
}

int main(int argc, char **argv)
{
	if (argc < 7) {
		fprintf(stderr, "usage: %s WIDTH HEIGHT SECONDS JPEG_WIDTH JPEG_HEIGHT ID...\n", argv[0]);
		return 2;
	}
	int w = atoi(argv[1]), h = atoi(argv[2]), secs = atoi(argv[3]);
	int jw = atoi(argv[4]), jh = atoi(argv[5]);
	ACameraManager *mgr = ACameraManager_create();
	int failed = 0;

	for (int i = 6; i < argc; i++) {
		const char *id = argv[i];
		ACameraDevice_StateCallbacks dcb = { NULL, on_disconnected, on_error };
		ACameraCaptureSession_stateCallbacks scb = { 0 };
		ACameraCaptureSession_captureCallbacks ccb = { 0 };
		ACameraDevice *dev = NULL;
		ACameraCaptureSession *session = NULL;
		ACaptureSessionOutputContainer *outputs = NULL;
		ACaptureSessionOutput *out = NULL, *jout = NULL;
		ACameraOutputTarget *target = NULL;
		ACaptureRequest *req = NULL;
		ANativeWindow *win = NULL, *jwin = NULL;
		AImageReader *yuv, *jpeg = NULL;
		double t0 = now();
		camera_status_t st;

		ccb.onCaptureFailed = on_capture_failed;
		atomic_store(&frames, 0);
		atomic_store(&jpegs, 0);
		atomic_store(&errors, 0);

		st = ACameraManager_openCamera(mgr, id, &dcb, &dev);
		printf("camera %s: open %d (%.2f s)\n", id, st, now() - t0);
		if (st != ACAMERA_OK) {
			failed++;
			continue;
		}

		yuv = reader(w, h, AIMAGE_FORMAT_YUV_420_888, NULL, &win);
		ACaptureSessionOutputContainer_create(&outputs);
		ACaptureSessionOutput_create(win, &out);
		ACaptureSessionOutputContainer_add(outputs, out);
		if (jw && jh) {
			jpeg = reader(jw, jh, AIMAGE_FORMAT_JPEG, (void *)1, &jwin);
			ACaptureSessionOutput_create(jwin, &jout);
			ACaptureSessionOutputContainer_add(outputs, jout);
		}
		st = ACameraDevice_createCaptureSession(dev, outputs, &scb, &session);
		printf("  session %d\n", st);
		if (st == ACAMERA_OK) {
			ACameraDevice_createCaptureRequest(dev, TEMPLATE_PREVIEW, &req);
			ACameraOutputTarget_create(win, &target);
			ACaptureRequest_addTarget(req, target);
			ACameraCaptureSession_setRepeatingRequest(session, &ccb, 1, &req, NULL);
			sleep(secs);
			if (jpeg) {
				ACaptureRequest *still = NULL;
				ACameraOutputTarget *jtarget = NULL;

				ACameraDevice_createCaptureRequest(dev, TEMPLATE_STILL_CAPTURE, &still);
				ACameraOutputTarget_create(jwin, &jtarget);
				ACaptureRequest_addTarget(still, jtarget);
				ACameraCaptureSession_capture(session, &ccb, 1, &still, NULL);
				sleep(2);
				ACaptureRequest_free(still);
				ACameraOutputTarget_free(jtarget);
			}
			ACameraCaptureSession_stopRepeating(session);
		}
		t0 = now();
		if (session)
			ACameraCaptureSession_close(session);
		ACameraDevice_close(dev);
		printf("  %d frames, %d jpeg, %d errors, close %.2f s\n",
		       atomic_load(&frames), atomic_load(&jpegs), atomic_load(&errors), now() - t0);
		if (!atomic_load(&frames) || atomic_load(&errors) || (jpeg && !atomic_load(&jpegs)))
			failed++;

		if (req)
			ACaptureRequest_free(req);
		if (target)
			ACameraOutputTarget_free(target);
		ACaptureSessionOutputContainer_free(outputs);
		ACaptureSessionOutput_free(out);
		if (jout)
			ACaptureSessionOutput_free(jout);
		AImageReader_delete(yuv);
		if (jpeg)
			AImageReader_delete(jpeg);
	}

	ACameraManager_delete(mgr);
	printf("failed %d of %d\n", failed, argc - 6);
	return failed ? 1 : 0;
}
