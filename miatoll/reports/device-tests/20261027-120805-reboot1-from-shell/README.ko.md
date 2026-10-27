# reboot1 실기기 결과 — 셸 명령으로 Fastboot 재부팅, 버튼 없는 순환

2026-10-27 KST. 브랜치 `miatoll/6.18-reboot1`, 커널 `6.18.58-miatoll-reboot1+`(battery2와 이름만 다름).
RAMdisk에 `/bin/reboot-mode`(SHA-256 `481c210c…`, battery2 세션에서 먼저 확인한 것과 같은 빌드)와 `fastboot-reboot`가 들어 있다.

1. `20261027-120729-reboot1`: Fastboot에서 reboot1을 `fastboot boot` 1회로 RAM 부팅했다.
2. 이 회차: `ram_boot_test.py boot --from-shell`이 실행 중인 reboot1의 USB 셸에 `reboot-mode bootloader`를 보냈다.
   `REBOOT_MODE_REQUESTED: bootloader` 뒤 ACM이 닫히고 Fastboot가 돌아왔다. 이어서 평소 절차
   (`getvar product` → `reboot bootloader` → `fastboot boot` 1회)로 reboot1이 다시 USB 셸까지 부팅됐다.
3. 같은 세션에서 `ram_boot_test.py reboot-bootloader`로 다시 Fastboot로 돌아왔다(`reboot-bootloader.txt`).

사용자는 매번 RAM 시험 문구와 Fastboot 화면이 번갈아 나타났고 멈춘 상태는 없었다고 확인했다.
이제 전원·볼륨 버튼 없이 시험 회차를 반복할 수 있다. 셸이 응답하지 않으면 기존처럼 버튼으로 Fastboot에 진입한다.
