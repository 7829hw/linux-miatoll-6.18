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
