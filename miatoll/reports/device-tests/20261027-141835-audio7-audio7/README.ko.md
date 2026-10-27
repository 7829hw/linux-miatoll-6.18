# audio7 실기기 결과 — PDC 경유 wake IRQ도 무효

2026-10-27 KST. TX SoundWire(swr2) wakeup을 `<&pdc 75 IRQ_TYPE_LEVEL_HIGH>`로 바꿨다(SPI 555 = PDC 핀 75).
DT 확인: `interrupts-extended = <&intc GIC_SPI 296>, <&pdc 75>`이고, 커널에는 `PDC 75 Level swr_wake_irq`로 등록됐다.

## 결과 (장치 런타임)
- 이어폰을 꽂은 채 부팅하자 audio5처럼 `mbhc sw intr`가 1회 발생했고, 4.6초에 `Impedance detect ramp error`가 났다.
- 유휴 상태에서 SoundWire 장치는 모두 `suspended`였다.
- 빼고 다시 꽂아도 `swr_wake_irq` 0회, `mbhc sw intr` 1회 그대로였고, Headphone/Mic Jack은 Off였다. 개선되지 않았다.
- 참고: downstream도 SPI 555를 wake로 쓴다(`swrm_register_wake_irq`, "TLMM connect gpio"). 다만 이 보드의 clock-stop 동안 wake가 실제로 들어오는 경로는 확인하지 못했다.
