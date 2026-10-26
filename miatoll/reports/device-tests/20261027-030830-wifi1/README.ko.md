# wifi1 실기기 결과 — MPSS·WCN3990 firmware·wlan0·수동 검색

2026-10-27 KST. 브랜치 `miatoll/6.18-wifi1`, 커널 `6.18.58-miatoll-wifi1+`. `fastboot boot` 1회로 RAM 부팅했다.
DT는 usb2에 MPSS와 WLAN 노드만 공통 DT 상태로 복구했고, ath10k SNOC·GLINK SMEM·SYSMON·RFKILL을 내장했다.
판정: **MPSS 실행, WLAN firmware·`wlan0` 등록, 45초 수동 검색으로 AP 7개 수신. AP 연결은 시험하지 않음.**
화면·터치 유지는 사용자가 직접 확인했다.

## 사용자 허가 범위와 실제 동작

- 모든 UFS 블록 장치는 read-only 상태다.
- `wifi-board`는 `modem` 파티션(`/dev/sde4`, ro=1)을 `ro,nosuid,nodev,noexec` VFAT로 마운트했다.
  `image/bdwlan.bin`(26,328 bytes, SHA-256 `902d380c…8fd9`)을 RAM에 복사해 해시를 비교한 뒤 즉시 해제했다.
  같은 디렉터리의 다른 `bdwlan.*` 파일은 이름과 크기만 기록했다.
- rmtfs는 modemst1/modemst2/fsg/fsc(`/dev/sdf2–5`, ro=1)를 `O_RDONLY`로 열었다. 모뎀 NV 쓰기는 RAM shadow에만 반영된다.
  이 동작의 단위 테스트 10개를 이번 회차 전에 다시 통과시켰다.

## 결과

- `wifi-start`: BDF 준비 → tqftpserv·rmtfs 시작 → MPSS 자동 복구 비활성화 → 시작. MPSS `running`, `q6v5 fatal` IRQ 0.
- QMI: chip_id 0x320, board_id 0xff, soc_id 0x400c0000. firmware WLAN.HL.3.2.2-00947(API 5).
- 공개 `board-2.bin`에는 0x320/0xff 항목이 없다. 그래서 기기 BDF를 `cal file`로 사용했다(아카이브와 같은 결과).
- `invalid MAC address; choosing random`: 공장 MAC을 제공하지 않았으므로 임의 주소가 쓰였다.
- `wlan0` 등록. `iw reg get`은 US(DFS-FCC)를 보고했다.
- 45초 수동(passive) 검색 exit 0: BSS 7개(2.4 GHz 6개, 5 GHz 1개), 신호 -27~-81 dBm.
- tqftpserv의 `lctoem.tmp`·`mcfg.tmp` 열기 실패 메시지는 모뎀의 선택 파일 요청이다. 시험 범위에는 영향이 없었다.

## 개인정보 처리

검색 결과에는 주변 AP의 SSID와 BSSID가 있다. Git에 넣은 `steps.txt`는 MAC/BSSID를 번호로, SSID를 `<redacted>`로 바꿨다.
원본은 Git 밖 `dist/miatoll-wifi1/private-logs/steps-original.txt`에 두고, 그 SHA-256을 `result.json`에 기록했다.

## 미검증

AP 연결(WPA2/WPA3·PMF)과 IP 통신, 공장 MAC 사용, 국가 설정, 절전·장시간 동작,
MPSS 오류 복구, 모뎀/통화 기능. 시험 중 SD 슬롯의 SH64G 카드는 storage1과 같은 CMD48 오류를 냈다.
