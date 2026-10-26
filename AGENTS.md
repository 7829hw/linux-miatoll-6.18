# miatoll Linux 6.18 LTS development

- Perform ongoing kernel work in this Git repository, `/data/hwkim/kernel/miatoll-6.18`, on `miatoll/6.18-sm7125` or a new feature branch based on it.
- Use official `v6.18.58` as the current upstream base. Preserve official version files and upstream implementations.
- The hardware reference is `sm7125-mainline/linux` at `linux-6.14.7`, commit `d7ab6144bdf26837785ee51d6148664471afdf1b`. Adapt Xiaomi changes selectively to 6.18. Exclude Samsung-only changes and already implemented upstream code.
- Keep `/data/hwkim/kernel/linux-6.18` and the original workspace artifacts as historical evidence. Do not overwrite or delete them.
- Preserve branches `archive/curtana-6.18-20261026` and `miatoll/6.18-lts`; they contain the previous local bring-up and an earlier migration attempt. Treat their hardware test logs as evidence for those builds only.
- Do not flash a device or change modem calibration data or partitions. Device boot commands require an explicit user request. On 2026-10-26 the user authorized a standalone kernel RAM boot test on the existing curtana connected to their Windows PC. Prepare a reviewed `fastboot boot` candidate and collect its logs; no partition writes or Android data mounts. Do not execute the archived Android init or fstab reference files.
- The user subsequently authorized the next hardware RAM test and reported a blank screen with the backlight on. Prepare a separate native display candidate while preserving boot1; the no-flash and no-partition-write limits remain in effect.
- On 2026-10-27 the user authorized an automated WSL loop of `fastboot boot` RAM tests (display, touch, storage, USB), and for the Wi-Fi tests: read-only access to the modem EFS partitions (modemst1/modemst2/fsg/fsc) through the RAM-shadow rmtfs, and a brief read-only VFAT mount of the `modem` firmware partition to copy `image/bdwlan.bin` into RAM. Nothing may be written to these partitions.
- Build with `bash miatoll/build.sh`. The build writes to sibling `out-miatoll-6.18` and `dist/miatoll-6.18` directories, outside this repository. Keep toolchain downloads and binary artifacts out of Git.
- Track source, configuration, build scripts, audit evidence and status documents in Git. Record source pins and distinguish source review, compilation, host ABI checks, and actual device runtime validation.
- Read `miatoll/STATUS.ko.md` and `miatoll/STRATEGY.ko.md` before continuing. Do not assume that a compiled driver proves hardware operation or vendor HAL compatibility.
