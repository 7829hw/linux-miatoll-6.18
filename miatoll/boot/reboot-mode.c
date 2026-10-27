// SPDX-License-Identifier: GPL-2.0-only
/*
 * Restart a curtana RAM test into a bootloader mode from the USB shell.
 *
 * BusyBox reboot cannot pass a restart command. The kernel's reboot-mode
 * driver (qcom-pon, mode-bootloader/mode-recovery) turns the RESTART2
 * argument into the PMIC PON soft reboot reason that the bootloader reads.
 * Only the modes below are accepted; nothing else is written by this tool.
 */
#include <stdio.h>
#include <string.h>
#include <sys/syscall.h>
#include <unistd.h>

#define LINUX_REBOOT_MAGIC1		0xfee1dead
#define LINUX_REBOOT_MAGIC2		672274793
#define LINUX_REBOOT_CMD_RESTART	0x01234567
#define LINUX_REBOOT_CMD_RESTART2	0xa1b2c3d4

int main(int argc, char **argv)
{
	const char *mode = argc == 2 ? argv[1] : "";
	long ret;

	if (!strcmp(mode, "--version")) {
		puts("curtana reboot-mode revision 1");
		return 0;
	}
	if (strcmp(mode, "bootloader") && strcmp(mode, "recovery") && strcmp(mode, "normal")) {
		fputs("usage: reboot-mode bootloader|recovery|normal\n", stderr);
		return 2;
	}
	printf("REBOOT_MODE_REQUESTED: %s\n", mode);
	fflush(stdout);
	sync();
	if (!strcmp(mode, "normal"))
		ret = syscall(SYS_reboot, LINUX_REBOOT_MAGIC1, LINUX_REBOOT_MAGIC2,
			      LINUX_REBOOT_CMD_RESTART, NULL);
	else
		ret = syscall(SYS_reboot, LINUX_REBOOT_MAGIC1, LINUX_REBOOT_MAGIC2,
			      LINUX_REBOOT_CMD_RESTART2, mode);
	perror("reboot");
	return ret ? 1 : 0;
}
