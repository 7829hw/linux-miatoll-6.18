# bt1 실기기 결과 — WCN3991 Bluetooth 초기화·전원·LE/BR 검색

2026-10-27 KST. 브랜치 `miatoll/6.18-bt1`, 커널 `6.18.58-miatoll-bt1+`(wifi3 기반). `fastboot boot` 1회.
DT는 QUP0와 UART3(공통 DT의 `qcom,wcn3991-bt`)만 다시 켰고, Bluetooth·LE·HCI UART QCA를 내장했다.
판정: **firmware 초기화, 임시 주소 설정 후 전원 켜짐, LE·BR/EDR 검색 성공. 페어링·연결은 미시험.**
화면·터치 유지는 사용자가 확인했다. 검색 중 주변에 검색 가능 상태의 기기가 있었다.

## 결과

- UART3 → serdev → `hci_uart_qca` 바인딩. Product 0x0a, SOC 0x40010320, ROM 0x0302.
  `qca/crbtfw32.tlv`, `qca/crnv32.bin`(고정 Alpine 패키지)을 받아 1.49초에 `QCA setup on UART is completed`.
- 컨트롤러는 공개 주소가 없어 `unconfigured`(`missing_options=0x2`)로 등록됐다. 아카이브와 같은 결과다.
- `bt-start --test-address`: btctl rev 4가 `02:`로 시작하는 임시 진단 주소를 이번 부팅에만 설정했다.
  공장 주소가 아니며 파일·DT에 기록하지 않는다. 그 뒤 `powered=1`.
- LE 검색 exit 0: 보고 30건, 주소 26개, RSSI -101~-48 dBm. LE 설정은 검색 중에만 켜졌다가 복원됐다.
- BR/EDR 검색 exit 0: 보고 7건, 주소 3개, RSSI -100~-78 dBm. 주소 수가 물리 기기 수와 같다고 단정하지 않는다.

## 개인정보

주변 기기 주소·이름이 있는 원본은 Git 밖 `dist/miatoll-bt1/private-logs/`에 있다.
Git에는 가린 사본과 원본 해시만 넣었다.

## 미검증

공장 BD 주소, 페어링·연결·오디오 프로필, Wi-Fi 동시 동작(이번 회차에서 Wi-Fi는 시작하지 않음), 절전·복귀.
