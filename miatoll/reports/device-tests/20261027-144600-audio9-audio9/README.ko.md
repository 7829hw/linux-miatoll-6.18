# audio9 실기기 결과 — TX 버스 유지로 MBHC 인터럽트는 전달됨, 감지 상태기계는 아직 불안정

2026-10-27 KST. 이 빌드의 변경:
- `wcd937x_codec_set_jack()`이 jack을 등록한 동안 TX Slave의 runtime PM 참조를 잡는다.
- audio8의 bus.c 변경은 되돌렸다.
- DT는 audio5와 같다(2.7 V micbias, TX wake IRQ 없음).

## 결과 (장치 런타임)
- 유휴 상태: `sdw:3`(TX)과 `sdw-master-3-0`은 `active`, RX 쪽은 `suspended`였다. 의도한 상태다.
- 부팅 때 꽂혀 있던 이어폰: `Impedance detect ramp error` 후 Jack Off였다(audio5와 같다).
- 첫 재삽입(45 s): `mbhc sw intr` 1→3으로 인터럽트가 도착했다. audio5–8에서는 0회였다. 하지만 ramp error로 Jack Off였다.
- RX Slave를 `power/control=on`으로 유지한 채 재삽입(109 s): ramp error, Jack Off.
- 헤드폰 재생 1회 후 재삽입(198 s):
  - z ≈ 47.9–49.7 Ω로 측정됐고 Headphone/Mic Jack On이 됐다.
  - 사용자는 재생음을 양쪽 귀에서 들었다고 했다.
- 몇 분 뒤 재삽입(322 s): ramp error가 났지만 Jack On이었다.
- 뺐을 때(약 358 s): 인터럽트가 왔고, 드라이버는 `MBHC_MECH`를 삽입 대기(0xbd, bit5=1)로 되돌렸다. 그런데 Jack은 On으로 남았다. 제거 보고가 반영되지 않았다.
- 사용자의 꽂기→뽑기→꽂기(606–620 s): ramp error, `cross connection found, Plug type 4`, ramp error 순서였다. 최종 상태는 Jack On이다.
- WCD 인터럽트 레지스터: `INTR_MASK_0=0x4c`(Elect insert/remove 마스크, mbhc sw 활성), STATUS 0.

## 해석
- clock stop 중 알림이 사라지는 문제는 TX Slave 유지로 해결됐다. 인터럽트는 이제 들어온다.
- 남은 문제는 MBHC 판정이다.
  - 첫 측정의 ramp error(c1=2, x1=0)가 재생 이력에 따라 달라진다.
  - 제거가 jack 보고에 반영되지 않는다.
  - cross connection(plug type 4)으로 판정되기도 한다.
- 다음: MBHC 상태기계(`wcd-mbhc-v2.c` plug detect work, `current_plug`/`hph_status`)에 진단 로그를 넣는다. 그리고 재생 전후 레지스터 차이를 비교한다. `wcd937x-regs-post-play.txt`는 재생 후 상태의 덤프다.
