# touch1 실기기 결과 — FT8756 터치 입력 확인

2026-10-27 KST. 브랜치 `miatoll/6.18-touch1`, 커널 `6.18.58-miatoll-touch1+`.
`fastboot boot` 1회로 RAM 부팅했다(flash/erase 없음).
판정: **SPI 연결·RAM firmware 시작·실제 좌표/다중 터치 입력 확인, 화면은 계속 정상**.
화면 상태와 실제 터치 동작은 사용자가 직접 보고 알려 준 관찰이다.
원본은 `touch1-serial-*.txt`(probe·dmesg), `steps.txt`(이벤트 원본), `touch-events-summary.json`(호스트 해석)이다.

## 로그 확인

- `spi11.0`이 `ft8756-spi`에 bound되고 deferred probe는 없다. QUP1/GPI DMA1/SPI11만 추가로 활성화했다.
- 0.64초에 probe가 시작되고 0.87초에 `Focaltech FT8756 Touchscreen` 입력 장치(event2)가 등록됐다.
- 1.24초에 `Touch IC FW loaded successfully`가 기록됐다. 6.14.7 포크 드라이버의 PRAM/DRAM 전송과 ECC 비교가
  수정 없이 통과했다. 포크는 DRAM ECC 요청에 상대 offset을 쓰지만, 이 기기와 고정 firmware에서는 일치했다.
  이전 아카이브에서는 절대 주소로 확인했으므로 ROM이 두 방식을 모두 받아들이는 것으로 보인다(추론).
- 앱 시작 직후 첫 IRQ의 읽기 1회가 `Failed to read data status: 0xC3` 3회 뒤 `-EIO`로 실패했다.
  이후 재발하지 않았고 터치 IRQ는 계속 전달됐다. 원인(앱 준비 전 IRQ)은 미확인이며 기록만 남긴다.
- SMMU fault와 커널 WARNING은 0건이다. display2의 화면 경로는 그대로 유지됐다.

## 터치 시험

| 단계 | 결과 |
| --- | --- |
| touch-events-40s | 이벤트 0건, 터치 IRQ 1 유지. 사용자가 시간 안에 시험하지 못해 재시도를 요청했다 |
| touch-events-30s-retry | 시작 전 IRQ 1,565, 종료 후 2,866. 이벤트 5,107개, SYN frame 713개, 접촉 101개 |

- 좌표 범위 x 30–1071, y 0–2396으로 1080×2400 패널과 일치한다. 축 반전이나 회전은 없다.
  네 모서리 근처 탭 (32,27), (1029,0), (113,2396), (978,2390)과 위→아래 드래그가 기록됐다.
- 최대 5개 동시 접촉, 슬롯별 tracking ID 할당·해제, BTN_TOUCH 107회가 확인됐다.
- 사용자는 모서리 탭, 아래 방향 드래그, 여러 손가락 터치가 로그와 일치하며 화면도 정상이었다고 확인했다.
- 창 종료 시점에 1프레임만 기록된 접촉 2개(ID 201, 202)의 해제 기록이 없다.
  `timeout` 종료와 겹친 것으로 보이지만, 접촉이 해제되지 않고 남는 문제의 가능성을 배제하지는 않았다.

## 미검증

suspend/resume 및 화면 blank 중 터치 전원 처리(panel follower 경로), 장시간 사용, 압력·면적 값의 정확도,
Tianma/NT36xxx 터치, firmware 오류 후 자동 복구(드라이버의 40000 jiffies 지연 포함)는 확인하지 않았다.
