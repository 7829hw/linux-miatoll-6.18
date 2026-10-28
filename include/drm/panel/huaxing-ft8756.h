/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef __DRM_PANEL_HUAXING_FT8756_H__
#define __DRM_PANEL_HUAXING_FT8756_H__

#include <linux/errno.h>
#include <linux/kconfig.h>
#include <linux/types.h>

struct drm_panel;

/*
 * The FT8756 is a TDDI: its touch controller only works while the panel
 * keeps its supply on and its reset released. The touch driver asks the
 * panel to stay powered (in sleep-in) across unprepare for wake gestures.
 */
#if IS_REACHABLE(CONFIG_DRM_PANEL_HUAXING_FT8756)
int huaxing_ft8756_keep_powered(struct drm_panel *panel, bool keep);
#else
static inline int huaxing_ft8756_keep_powered(struct drm_panel *panel, bool keep)
{
	return -ENODEV;
}
#endif

#endif
