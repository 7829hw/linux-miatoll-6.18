# audio12 실기기 결과 — 진단 로그를 뺀 헤드셋 후보

2026-10-27 KST. 커널 소스(drivers, sound)는 audio9(21c271b0)와 같다. jack 등록 중 TX Slave를 유지한다.
DT는 audio11과 같다(2.7 V micbias, 헤드셋 2550000 µV / 헤드폰 75000 µV 임계값).

## 결과 (장치 런타임)
- 꽂은 채 부팅: z ≈ 47.8–50.3 Ω, Headphone/Mic Jack On.
  - 유휴 상태: TX(`sdw:3`, master-3) active, RX suspended.
- 뽑았다가 5초 뒤 재삽입:
  - 삽입 과도 상태의 `cross connection found` 1회 뒤 3초 보정으로 z ≈ 47.7–49.8 Ω가 측정됐다. Jack On.
  - `mbhc sw intr` 3회.
- 이어폰 마이크 녹음은 같은 커널 경로를 쓴 audio11에서 확인했다. 이번 부팅에서는 반복하지 않았다.

## 이어폰 버튼 (같은 부팅, 3버튼 유선 이어폰)
- 입력 장치: `event4 "Xiaomi-miatoll Headset Jack"`.
- 키 매핑(machine driver)은 BTN_0 KEY_MEDIA, BTN_2 KEY_VOLUMEUP, BTN_3 KEY_VOLUMEDOWN이다.
- 임계값: 75/150/237/500 mV(BTN4–7 = 500).
- 자유 누름: MEDIA 6회, VOLDOWN·VOLUP 각 4회. press/release IRQ 14/14.
- 볼륨 + 짧게 2회: VOLUP 2회.
- 볼륨 − 짧게 2회: press/release IRQ는 각 +2였지만 입력 이벤트가 없었다.
- 길게 누름(3초씩):
  - 볼륨 −(2회로 기록): VOLDOWN 1→0 각 약 2 s.
  - 볼륨 +: VOLUP.
  - 가운데: MEDIA.
  - 마지막 래치 결과 `ANA_MBHC_RESULT_3` 하위 3비트: 3 → 2 → 0.
- 가설: 볼륨 −가 BTN_3/BTN_4 경계(500 mV) 근처라서, 짧게 누를 때 BTN_4(키 없음)로 판정된다. audio13에서 구간을 나눠 측정한다.
