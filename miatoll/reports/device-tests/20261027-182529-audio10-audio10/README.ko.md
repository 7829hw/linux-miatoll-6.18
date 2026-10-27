# audio10 실기기 결과 — MBHC 진단 로그: 2.7 V 바이어스에서 헤드셋 임계값이 1.7 V로 고정돼 연장 케이블로 오판

2026-10-27 KST. audio9에 진단 로그(`mbhc-dbg:`)를 더한 빌드다. 테스트 전용이며 유지하지 않는다.
- 이번 부팅 전에 폰이 audio9에서 빠져나와 Android로 부팅돼 있었다.
- 사용자 허락을 받아 `adb reboot bootloader`를 1회 실행해 fastboot로 진입했다.

## 결과 (장치 런타임)
- 부팅 때 꽂혀 있던 이어폰: `correct start mv=1762 plug=3 hs_thr=1700 micb=2700` → `correct end mv=2062 plug=3`.
  - 결과는 `report insertion type=0x4`(LINEOUT)이었고, Headphone/Mic Jack은 Off였다.
- 뽑기: `switch irq removal plug=3` → `report removal type=0x4`. 제거 처리는 정상이었다.
- 다시 꽂기:
  - 삽입 과도 상태로 `cross_conn=1`이 나왔다. 이어진 3초 보정 루프에서 swap_cnt=0으로 해소됐다.
  - 결과는 `mv=2043 plug=3`, 이번에도 LINEOUT 판정, Jack Off였다.
- zdet 시점 상태: `bias=80 rxsup=00 anaclk=10 digclk=f0 ctl1=82 mech=9d elect=89 micb2=62 hph=0c`. 매번 ramp error가 났다.
  - LINEOUT 판정은 zdet가 아니라 ADC 임계값에서 나왔다(zl=zr=0).

## 원인
- 공통 DT(`sm7125-xiaomi-common.dtsi`)의 `qcom,mbhc-headset-vthreshold-microvolt = <1700000>`는 1.8 V 바이어스 기준값이다.
- 드라이버는 `cfg->micb_mv`(DT의 micbias2 = 2.7 V)와 실제 바이어스가 같으면 임계값을 그대로 쓴다. 따라서 2.7 V에서도 1.7 V가 적용된다.
- downstream은 임계값을 지정하지 않는다. 기본 1700 mV를 1.8 V → 바이어스 비율로 환산하므로 2.7 V에서는 2550 mV다.
- audio3(1.8 V)에서 헤드셋으로 판정된 것과 일치한다.
- 다음(audio11): 2.7 V 기준 임계값으로 바꾼다(헤드셋 2550000 µV, 헤드폰 75000 µV).
