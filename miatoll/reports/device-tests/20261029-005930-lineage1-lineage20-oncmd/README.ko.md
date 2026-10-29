# lineage1 두 번 탭 켜기(DT2W) 시도 — 미해결, 보류

2026-10-28~29 KST. lineage1 커널(SD 카드 LineageOS 22.2)에서 FT8756 TDDI의 두 번 탭 켜기를 시도했다.
시행 lineage8–lineage20(이 디렉터리 포함)의 커널은 진단 코드를 포함했고, 진단 코드는 이후 기록에서 뺐다.

## 커널에 남긴 것
- `ft8756`: `double_tap_enable` sysfs, 패널 off 때 제스처 모드 진입(0xD1/D2/D5–D8=0xFF, 0xD0=1; Xiaomi curtana-q-oss
  `focaltech_gesture.c`), IRQ wake, 제스처 0x24에 `KEY_WAKEUP`.
- `panel-huaxing-ft8756`: `huaxing_ft8756_keep_powered()` — 제스처 사용 시 unprepare에서 리셋·vddio를 유지.
- 함께 고친 기존 버그: SPI 읽기 TX 버퍼 크기(4바이트에 전체 길이 전송), 접근마다 devm 할당 누수,
  CRC 재시도·실패 처리, 절전 명령 레지스터(0x03→0xA5), IRQ 에지(rising→DT·벤더와 같은 falling).
- 패널 on/off 시퀀스를 벤더 `dsi-panel-ft8756-huaxing-fhd-video.dtsi`에 맞춤(command2 unlock, CABC, B5/CA,
  off 끝의 low power `F7 5A A5 95 27`).
- 화면 표시와 일반 터치는 이 변경 뒤에도 정상(사용자 확인).

## 장치 런타임 결과(미해결)
- 제스처 모드 진입 후 앱 펌웨어가 유지된다: 칩 ID 0x87, FW 0x0e, 0xD0=1, 탭 없이 10 s 이상.
- **탭하는 순간 컨트롤러가 스스로 리셋된다.** INT 하강 직후 첫 읽기부터 0xA3/0xA6/점 데이터가 모두 0xEF(ROM boot).
  0xD0=1은 Xiaomi 설정표의 `upgsts_boot = 0x01`(boot 상태)과 같은 값이다.
- 배제한 것(LineageOS 공식 커널 `android_kernel_xiaomi_sm6250` lineage-22.2 `803b5586`과 비교):
  - 펌웨어 바이트 동일(`fw_huaxing_v0e.i` = 우리 `focaltech_ts_fw_huaxing.bin`, 180224 B).
  - PRAM/DRAM 적재·half_length·ECC 절차 동일. 두 번째 이미지(0x16000)는 공장 시험용이다.
  - SPI 프레이밍·제스처 레지스터 시퀀스 동일.
  - PM6150L LCDB(0xEC00–0xECFF) 256개 레지스터가 화면 on/off에서 동일, L18A 유지.
  - 패널·터치 리셋, INT, SPI 핀 상태 동일.
  - 패널 off 명령 유무(전체/없음/sleep-in만), on 시퀀스 전체 적용, 충전기 모드(0x8B=1), 화면 켜진 상태 진입 — 모두 같은 리셋.
- Android에서는 설정 항목을 숨겼다(`config_supportDoubleTapWake` 제거). power HAL과 커널 인터페이스는 남겼다.
