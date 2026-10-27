# audio11 실기기 결과 — 2.7 V 기준 MBHC 임계값으로 헤드셋 감지·제거·재삽입 정상

2026-10-27 KST. 구성:
- 커널은 audio10과 같다(TX Slave 유지 + `mbhc-dbg` 진단 로그).
- DT에 2.7 V 기준 임계값을 넣었다: `qcom,mbhc-headset-vthreshold-microvolt = <2550000>`, `qcom,mbhc-headphone-vthreshold-microvolt = <75000>`.

## 결과 (장치 런타임)
- 꽂은 채 부팅:
  - `correct start mv=1762 plug=1 hs_thr=2550` → `report insertion type=0x3`(HEADSET).
  - z ≈ 47.7–49.6 Ω, ramp error 없음. Headphone/Mic Jack On.
- 뽑기: `switch irq removal plug=1` → `report removal type=0x3`, Jack Off.
- 다시 꽂기:
  - 삽입 과도 상태로 `cross_conn=1`이 나왔다. 3초 보정 루프 뒤 `mv=2043 plug=1`.
  - z ≈ 47–50 Ω, `report insertion type=0x3`, Jack On.
- 헤드셋 마이크 녹음(셸에서 PM 강제 없이 정상 경로 그대로). 0.5초 창 RMS(dBFS)는 다음과 같다.
  - 말하기: −38.4 −44.4 −63.7 −66.7 −62.9 −60.9 −66.8 −46.6 −48.4 −52.7 −55.4 −59.9
  - 침묵: −39.3 −45.4(시작 과도) −68.1 −67.9 −67.8 −69.4 −69.3 −68.7 −69.2 −66.6 −69.1 −68.9
  - 말하기의 뒤쪽 창이 침묵보다 최대 약 20 dB 높다. 사람이 녹음을 직접 들어 확인하지는 않았다.
- 앞선 라운드의 ramp error는 LINEOUT 오판 경로에서만 났다. 헤드셋 판정 경로에서는 재생 이력과 무관하게 zdet가 성공했다.
