# audio5 실기기 결과 — 2.7 V 바이어스 적용, MBHC 인터럽트가 첫 1회 뒤 끊김

2026-10-27 KST. audio3에 WCD937x micbias1–3만 2700 mV로 바꿨다. 유휴 상태 `ANA_MICB2 = 0x22`로 2.7 V 설정이 적용됐다.
이어폰을 꽂은 채 부팅하자 `mbhc sw intr`가 한 번 발생했고, 4.6초에 `Impedance detect ramp error`가 났다.
그 뒤에는 유휴 상태에서도, 30초 녹음 중에도 빼고 다시 꽂을 때 MBHC 인터럽트가 전혀 없었다.
WCD937x 상위 IRQ 1회, Elect Insert/Remove 0회였다.
가설: TX SoundWire(swr2)에 wakeup 인터럽트가 없다. 버스가 clock-stop 상태일 때 WCD가 낸 알림이 사라지고,
상태가 latch되어 이후 엣지가 생기지 않는다. downstream atoll TX master에는 `swr_wake_irq <0 555 0>`가 있다. audio6에서 시험한다.
