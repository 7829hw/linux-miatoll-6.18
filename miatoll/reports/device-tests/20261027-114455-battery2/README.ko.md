# battery2 실기기 결과 — QG 전류 배율·부호 수정 확인

2026-10-27 KST. 브랜치 `miatoll/6.18-battery2`, 커널 `6.18.58-miatoll-battery2+`.
battery1과의 차이는 이름과 `qcom_qg` 변경 하나(`a986acac`)다. 이 변경은 probe 때 SUBTYPE을 한 번 읽어
downstream과 같은 배율(0x3이면 152.588, 그 밖에는 305.176 µA/LSB)을 고르고, power_supply ABI에 맞게 부호를 뒤집는다.
`fastboot boot` 1회. 판정: **충전 시 양수·방전 시 음수, 크기 약 2배로 예측과 일치.** 화면은 사용자가 정상이라고 확인했다.

| 구간 | 전압 | current_now |
| --- | --- | --- |
| USB 연결 | 4.479 V | +144~+154 mA |
| 분리(363–395초) | 4.399–4.408 V | −99~−163 mA(대부분 약 −112 mA) |
| 재연결 | 4.480 V | +158~+167 mA |

- 첫 90초 기록(`battery-unplug-log.txt`)은 분리가 기록 종료 뒤에 일어나 포함되지 않았다.
  화면 카운터에 맞춰 다시 한 180초 기록(`battery-unplug-log-2.txt`)에 분리·재연결이 들어갔다.
- battery1의 같은 시험(연결 −81~−92 mA, 분리 +48~+76 mA)과 비교해 부호가 바뀌고 크기가 약 2배가 됐다.
- 독립 전류계·Android 순간 전류와는 비교하지 못했다. 배율의 근거는 SUBTYPE 레지스터와 downstream 소스다.
- capacity(전압 선형)·status(Unknown 고정)·충전 제어 부재는 그대로다.
