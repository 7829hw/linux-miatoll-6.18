# lineage1 진동 (SD 카드 LineageOS 22.2)

2026-10-29 KST.

## 커널 쪽 변경
- `CONFIG_INPUT_AW8695_HAPTICS`, `CONFIG_INPUT_DRV2624_HAPTICS`를 lineage1에서 내장(=y)으로 바꿨다. 모듈이었고 Android는 커널 모듈을 올리지 않는다.
- lineage1 DT에서 `i2c4`를 켰다. boot1 기반에서 꺼진 뒤 다시 켜지지 않아 진동 칩 노드가 probe되지 않았다.

## 장치 런타임 결과
- 4-005a는 AW8624(칩 ID 확인)이고 `aw8695-haptics` 드라이버가 붙었다. 입력 장치 FF 기능: RUMBLE, PERIODIC, SQUARE, TRIANGLE, SINE, GAIN(ff-memless).
- NDK로 만든 시험 프로그램이 FF_RUMBLE 0.5 s를 세 번 재생했고, 세 번 떨렸다(사용자 확인).
- Android: 기기 트리의 FF_RUMBLE용 IVibrator V2 HAL로 `cmd vibrator_manager` 0.6 s 진동과 키보드·길게 누르기 피드백 진동을 확인했다(사용자 확인).
- 미확인: DRV2624 변형 기기, 진동 세기 단계별 차이, 장시간 사용.
