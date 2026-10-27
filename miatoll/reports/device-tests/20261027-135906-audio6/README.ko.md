# audio6 실기기 결과 — GIC 직결 wake IRQ는 무효, 버스를 active로 붙잡으면 헤드셋 감지·녹음 동작

2026-10-27 KST. audio5에 TX SoundWire(swr2) `wakeup` 인터럽트로 `GIC_SPI 555`를 추가했다. 커널에는 GIC 587 `swr_wake_irq`로 등록됐다.

## 결과 (장치 런타임)
- 기본 상태: 이어폰을 빼고 다시 꽂아도 `swr_wake_irq` 0회, `mbhc sw intr` 0회였다. Headphone/Mic Jack은 Off였다. 부팅 때의 1회 인터럽트도 없었다.
- 유휴 상태 runtime PM: SoundWire 컨트롤러 2개, master 2개, WCD937x RX/TX slave가 모두 `suspended`였다.
  레지스터는 `MBHC_MECH 0x3014=0xbd`, `MICB2 0x3023=0x22`(바이어스 꺼짐, 2.7 V 코드)였다.
- 진단 조치: 모든 SoundWire 장치의 `power/control`에 `on`을 써서 버스를 active로 고정했다.
  - 고정 직후 대기 중이던 `mbhc sw intr`가 바로 처리됐다(+1).
  - 이후 빼고 다시 꽂자 MBHC가 정상 동작했다. z ≈ 49 Ω, Headphone Jack On, Mic Jack On(헤드셋으로 판정).
- 헤드셋 마이크 녹음(`audio-path headset-mic`, amic2 = ADC2 INP2, DEC0_BCS, MICB2 `0x62` = 2.7 V 켜짐)을 했다. 0.5초 창 단위 RMS(dBFS)는 다음과 같다.
  - 말하기 6초: −36.6, −37.4, −38.2, −41.2, −48.4, −44.9, −44.6, −43.6, −41.5, −46.0, −48.5, −62.2(말을 멈춘 뒤)
  - 침묵 대조 6초: −39.8(시작 과도), −46.9, −52.5, −51.4, −56.9, −65.3, −58.8, −55.6, −59.5, −56.1, −57.2, −54.1
  - 말하는 구간이 침묵보다 10–20 dB 높고 음절 모양으로 변한다. 이어폰 마이크가 소리를 받는다는 강한 근거다.
  - 녹음을 사람이 직접 들어 확인하지는 않았다.

## 해석
- audio3에서 부팅 후 꽂은 이어폰이 감지된 것은 직전 스트림 때문에 버스가 아직 깨어 있었기 때문으로 보인다(autosuspend 3초).
- 오디오 경로 자체(바이어스, ADC2, DEC0)는 정상이다. 남은 문제는 clock-stop 동안 WCD의 slave 알림이 CPU에 전달되지 않는 것이다.
- sc7180/sm7125의 `qcom,pdc-ranges = <0 480 94>`에 따르면 SPI 555는 PDC 핀 75다.
  - GIC에 직접 요청하면 PDC 핀이 켜지지 않아 wake가 GIC에 도달하지 않는다.
  - 비교: sc7280 TX master는 같은 wake를 `<&pdc 130>`으로 기술한다.
  - audio7에서 `<&pdc 75 IRQ_TYPE_LEVEL_HIGH>`로 시험한다.
