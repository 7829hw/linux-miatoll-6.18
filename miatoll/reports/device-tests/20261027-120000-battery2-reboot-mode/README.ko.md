# 실행 중 RAM 시험에서 Fastboot로 재부팅 — 실기기 확인

2026-10-27 KST. 실행 중이던 battery2 RAM 세션(`20261027-114455`)에서 새 부팅 없이 시험했다.
`miatoll/boot/reboot-mode.c`를 고정 toolchain·sysroot로 정적 ARM64 빌드했다(SHA-256 `481c210c…`).
이를 USB 셸로 `/run`에 넣고 폰에서 해시를 확인한 뒤 `/run/reboot-mode bootloader`를 실행했다.

- 출력 `REBOOT_MODE_REQUESTED: bootloader` 뒤 ACM 포트가 닫혔다. usbipd 재연결 확인을 시작한 지 약 4초 만에 `fastboot devices`에 `REDACTED`가 나타났다.
- 커널 쪽은 수정하지 않았다. upstream `qcom-pon` reboot-mode가 PON `SOFT_RB_SPARE`(0x8F) 7:1비트에 `mode-bootloader = <0x2>`를 쓴다.
  이는 downstream `qpnp_pon_set_restart_reason`(gen2, `reason << 1`)과 같다.
  downstream이 추가로 쓰는 IMEM 매직(0x77665500)은 curtana ABL에서 필요하지 않았다.
- 파티션 쓰기는 없다. PMIC의 재부팅 사유 레지스터는 Android의 `adb reboot bootloader`도 쓰는 일반 재부팅 경로다.
- 근거 소스 해시는 `miatoll/reference/reboot1/sources.json`에 있다.
