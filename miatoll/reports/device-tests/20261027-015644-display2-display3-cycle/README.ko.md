# display3 시험 1회차 — 밝기·blank 반복·2분 유지 (display2 이미지)

2026-10-27 KST. 커널 수정 없이 확인된 display2 이미지
(`6.18.58-miatoll-display2+`, SHA256 `dea36fe4…681c`)를 `fastboot boot`로 1회 RAM 부팅했다.
그 뒤 USB 셸에서 단계별 명령을 실행했다. 각 단계 직후 사용자가 화면을 보고 결과를 알려 줬다.
명령과 출력 원본은 `steps.txt`에 있고, 단계별 관찰은 `result.json`의 `step_observations`에 있다.
판정: **세 단계 모두 사용자 관찰로 통과**.

| 단계 | 명령 | 로그 | 사용자 관찰 |
| --- | --- | --- | --- |
| brightness-cycle | WLED 4095→200→0을 4초씩 3회 반복한 뒤 1024 | `actual_brightness`가 설정값을 그대로 반환(소프트웨어 값) | 밝음→어두움→꺼짐 3회 뒤 중간 밝기로 문구 표시 |
| blank-cycle | `fb0/blank` 4↔0을 5초 간격으로 3회 반복 | CRTC `active` 1→0→1 반복, 오류 없음 | 화면·백라이트가 3회 꺼졌다 켜지고, 복귀 후 녹색 완료 문구 표시 |
| hold-120s | VT 카운터를 10초마다 갱신(uptime 147→274초) | SMMU/WLED short·OVP IRQ 0, MDSS IRQ 2,066→9,668(약 60/s) | 카운터가 꾸준히 갱신되고 깜빡임·잡상 없음 |

## 해석과 한계

- blank 4는 DRM CRTC를 끄고 0은 다시 켠다. 이 경로는 DSI·패널 전원을 끄고 다시 켜는 순서를 거친다.
  따라서 부트로더가 초기화한 상태가 아닌, 커널의 패널 재초기화 경로도 3회 동작한 것으로 본다.
  이는 sysfs 상태와 사용자 관찰을 근거로 한 추론이다.
- MDSS IRQ 증가율은 60 Hz 비디오 모드 vsync와 일치한다.
- 시험 중 BusyBox `seq`/`cut` applet 링크가 RAMdisk에 없어 첫 hold 시도의 루프가 실행되지 않았다.
  두 번째 시도에서 `cut`이 없어 화면의 uptime 값만 비어 있었다. 이는 시험 도구의 한계이며 커널 문제가 아니다.
- 아직 확인하지 않은 범위: suspend/resume, 장시간(수십 분 이상) 표시, Tianma 패널, 밝기 곡선의 정확도.
  `actual_brightness`는 하드웨어 측정값이 아니다.
- 커널·DT를 바꾸지 않았으므로 `miatoll/6.18-display3` 브랜치는 만들지 않았다.
