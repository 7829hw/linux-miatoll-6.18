# lineage1 실기기 결과 — SD 카드 LineageOS 22.2 부팅

2026-10-28 KST. lineage1 커널(6.18.58-miatoll-lineage1)을 `fastboot boot`로 RAM에서 실행했다.
Android는 SM32G microSD(`soc@0/8804000.mmc`)의 super·userdata로 부팅했다.
- 내부 UFS, MPSS, IPA, Wi-Fi는 lineage1 DT에서 꺼져 있다.
- 플래시와 파티션 쓰기는 하지 않았다. 쓴 것은 사용자가 허락한 SM32G 카드뿐이다.
- Android userspace(LineageOS 22.2 기기 트리와 Mesa prebuilt)는 이 저장소 밖에서 관리한다.
- 이 기록은 커널 쪽 결과만 다룬다. 원본 logcat/dmesg/getprop에는 기기 식별자가 있어 Git에 넣지 않았다.

## 시행과 커널 수정

| 시행 | 커널 | 결과 |
| --- | --- | --- |
| 191921 | 첫 lineage1 | FBE `init_user0` 실패로 내부 리커버리로 감(keymaster 3.0을 keystore2가 못 씀). 기기 트리에서 FBE를 끔 |
| 193935–194823 | + 치명 init 오류 정지 | userdata f2fs casefold 마운트 실패. 커널에 `CONFIG_UNICODE`가 없음 |
| 195830 | `33d2bb4e` UNICODE | LineageOS 부팅 완료(`sys.boot_completed=1`, SurfaceFlinger 66 s). 터치 정확(사용자 관찰) |
| 203923 | `b349e8dc` CPUSETS_V1·UCLAMP | `/dev/cpuset` 생성, task profile 실패 25건 → 0건, SurfaceFlinger 42 s. ADSP `running`, ALSA 카드 `Xiaomi-miatoll` 등록 |
| 205935 | 같은 커널 | Mesa 26.2.5 freedreno/Turnip userspace에서 GPU 렌더링(사용자: 화면 정상·빨라짐) |

195830에서 확인한 커널 쪽 문제:
- `/dev/cpuset`이 없었다. 6.18은 v1 cpuset 파일을 `CPUSETS_V1` 뒤에 둔다. b349e8dc에서 추가했다.
- ADSP 펌웨어 로드 실패: 커널이 0.35 s에 ADSP를 띄우려 하지만 `/vendor`는 0.95 s에 마운트된다.
  - 커널은 바꾸지 않았다. Android vendor init이 post-fs에서 remoteproc을 다시 `start`한다.
- BpfLoader 실패: GKI 전용 tracepoint를 쓰는 선택 객체(gpuMem, gpuWork 등)다. 부팅에는 영향이 없다.
- `prng_seeder`가 `/dev/hw_random`을 기다린다. SC7180 DT에 RNG 노드가 없어 그대로 두었다.

## 205935 GPU 확인 (장치 런타임)
- SurfaceFlinger `GLES: freedreno, FD618, OpenGL ES 3.2 Mesa 26.2.5`.
- `cmd gpu vkjson`: `Turnip Adreno (TM) 618`, Vulkan 1.3.
- devfreq `5000000.gpu` simple_ondemand, UI 사용 중 750 MHz.
- systemui gfxinfo(부팅 직후, 설정 마법사 포함):
  - 1502 프레임, janky 11.8 %.
  - 50/90/99번째 백분위 20/40/97 ms.
- 이전 ANGLE/SwiftShader(CPU 렌더링)는 사용자가 "매우 느리다"고 보고했다.

## 남은 일
- 이후 Android 쪽 수정(같은 lineage1 커널):
  - 공식 LineageOS sm6250 overlay와 handheld 기능 선언을 넣었다. 소프트키와 Trebuchet이 정상이다(사용자 확인, 213111/220438).
  - 오디오 HAL(dragonboard tinyalsa 기반)이 PCM 0(스피커)·1(이어폰)과 RAM 시험 mixer 경로를 쓴다. 스피커와 이어폰 모두 들렸다(사용자 확인, 230420).
  - 마이크 녹음은 Android에서 아직 미확인이다.
- Wi-Fi·모뎀·Bluetooth: [lineage24 기록](../20261029-172800-lineage1-lineage24-btprofiles/README.ko.md). 두 번 탭 켜기: [lineage20 기록](../20261029-005930-lineage1-lineage20-oncmd/README.ko.md)(미해결).
- FBE(KeyMint), 절전·suspend, 장시간 안정성은 미시험이다.
