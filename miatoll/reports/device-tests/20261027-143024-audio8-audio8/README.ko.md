# audio8 실기기 결과 — simple clock stop Slave WakeUpEnable도 무효

2026-10-27 KST. audio7 DT에 커널 변경 1개를 더했다.
`sdw_bus_prep_clk_stop()`이 wake_capable인 simple clock stop Slave에 `SCP_SystemCtrl.WakeUpEnable`(bit 3)을 쓰게 했다.
upstream은 simple clock stop Slave에서 SystemCtrl 쓰기를 건너뛴다. downstream도 이 비트를 명시적으로 쓰지 않는다.

## 결과 (장치 런타임)
- 부팅 때 `mbhc sw intr` 1회와 ramp error는 audio5/7과 같았다.
- 버스 suspended 상태에서 빼고 다시 꽂았을 때 `swr_wake_irq` 0회, Jack Off였다.
- RX/TX/VA macro를 `power/control=on`으로 active에 고정하고(LPASS 클록·HW vote 유지) SoundWire만 clock stop에 둔 채 다시 빼고 꽂아도 결과가 같았다.
- 결론: wake IRQ 라우팅, WakeUpEnable, LPASS 클록 유지 어느 것으로도 clock stop 중 MBHC 알림은 전달되지 않았다. bus.c 변경은 audio9에서 되돌린다.
- 다음(audio9): WCD937x가 jack을 등록한 동안 TX Slave의 runtime PM 참조를 잡아 버스가 clock stop에 들어가지 않게 한다(downstream `qcom,is-always-on`과 같은 취지). 전력 비용이 있다.
