# display2 실기기 결과 — 화면 표시·백라이트 확인

2026-10-27 KST. WSL 실행기 `miatoll/boot/ram_boot_test.py`의 첫 회차다.
판정: **Linux 부팅·USB 셸 성공, 패널에 시험 문구와 RED/GREEN/BLUE 색상 표시, 백라이트 켜짐**.
화면·백라이트 판정은 로그가 아니라 실행 중 사용자가 직접 본 관찰이다.
원본 로그 해시와 Fastboot 명령 목록은 `result.json`에 있다.

## Fastboot 동작

`devices` → `getvar product`(curtana) → `reboot bootloader` → 재연결 확인 → `fastboot boot` 1회.
flash/erase/format/set_active/oem 명령은 없다. 실행기는 이 네 가지 외의 fastboot 명령을 코드에서 거부한다.
USB는 usbipd-win 5.3.0으로 WSL에 연결했고 Linux ACM은 `/dev/ttyACM0`이었다.

## display1 대비 변화

| 항목 | display1 | display2 |
| --- | --- | --- |
| 물리 화면 | 검정 | 시험 문구·색상 표시 |
| 백라이트(사용자 관찰) | 꺼짐 | 켜짐 |
| SMMU context fault 메시지 / IRQ | 20 / 7,796 | 0 / 0 |
| pixel RCG `didn't update` WARN | 있음 | 없음 |
| `FBINFO_VIRTFB` 경고 | 있음 | 없음 |
| fb0 `blank` | 4 | 0 |
| 커널 `WARNING: CPU` | 2 | 0 |

공통: 1080×2400 `msmdrmfb`, DSI-1 connected/DPMS On, CRTC active=1,
WLED `brightness=actual_brightness=256`(소프트웨어 값), uptime 약 5.5초에 probe 수집.

## 해석과 한계

- display1에서 fault는 DPU bind 직후(0.43초) 부트로더 scanout 주소 0x9c000000에서 시작했다.
  display2는 MDSS probe 때 `DISP_CC_MDSS_CORE_BCR` reset이 먼저 수행되므로 이 경로가 사라진 것과 일치한다.
  pixel RCG 경고 소멸도 reset으로 이전 클록 상태가 정리된 결과로 보인다(추론).
- 세 변경(MDSS reset, `FBINFO_VIRTFB`, `blank=0` 1회)은 함께 시험했으므로 각각의 기여는 분리 검증하지 않았다.
  fault와 클록 경고 소멸은 reset과 직접 대응하며, 나머지 두 변경은 경고 제거·fbdev 상태 정리 성격이다.
- 확인 범위는 **부팅 직후 정지 화면 1회 표시**다. 밝기 조절, blank/unblank 반복, 장시간 안정성,
  suspend/resume, Tianma 패널, 터치는 미검증이다.
- 로그 수집 이후의 자동 재부팅 여부는 기록하지 않았다.
