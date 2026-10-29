# lineage1 Android 카메라 HAL (libcamera, 진행 중)

2026-10-29 KST. 커널은 [CCI 안정화 기록](../20261029-203842-lineage1-camera5/README.ko.md)과 같은 lineage1이다.
Android 쪽은 이 저장소 밖에 있다.
- device tree `android/device_xiaomi_curtana_ml`
- 빌드 도구 `android/lineage-tools`(libcamera 패치는 `libcamera-patches/`)

## 구성
- libcamera v0.7.2를 NDK r30으로 빌드한다.
  - simple 파이프라인과 CPU 소프트웨어 ISP를 쓴다. Qualcomm ISP 드라이버는 메인라인에 없다.
  - generic Android camera3 HAL을 `hw/camera.curtana_ml.so`로 넣는다.
- LineageOS AIDL camera provider가 이 HAL을 연다.
- `camera_hal.yaml`의 카메라 ID: 0 메인 S5KGM2, 1 전면 OV16A1Q, 2 초광각 OV8856, 3 매크로 S5K5E9.
- Aperture 보조 카메라 선택기 오버레이를 켰다.
- libcamera 패치 0001-0014(Android용):
  - bionic 대응, NV12 출력, dma-heap 읽기 전용 열기, logcat 로그
  - 색공간, 버퍼 수, 센서 방향, minigbm 버퍼 배치, gralloc0 없는 할당
  - 카메라 ID 고정, 단일 처리 스트림 합치기, 소프트 ISP 정지 중 작업 정리

## 장치 결과
- `dumpsys media.camera`: 카메라 4개 등록, HAL 등급 LIMITED.
- 메인 카메라 미리보기가 보인다(사용자 확인, lineage29 이후).
- 사진: `input keyevent KEYCODE_CAMERA`로 Aperture 셔터를 눌러 메인·전면에서 JPEG가 `DCIM/Camera`에 저장됐다(약 1.2 MB). 사용자 확인 전이다.
- 카메라를 다시 열 때 provider가 죽던 문제는 `cam2-cycle`과 Aperture로 재현해 원인을 고쳤다.
  - 원인: 소프트 ISP가 멈춘 뒤 큐에 들어간 디베이어 작업이 다음 시작 때 해제된 버퍼로 실행됐다.
  - 수정 뒤 전환 시험에서 충돌 0건(lineage31 + bind mount 시험).

## 미해결 (사용자 보고)
- 전환이 실제로 되지 않는 것처럼 보인다.
  - 닫을 때 HAL이 flush 뒤 재시작하고, 그 뒤 요청이 완료되지 않아 cameraserver가 5초 drain 시간 제한에 걸린다.
- 전면 미리보기 줄무늬: YUV 축소가 gralloc stride(128 정렬)를 무시했다. 수정은 빌드했지만 사용자 확인 전이다.
- 자동 초점 없음: simple 파이프라인과 소프트 ISP에 AF 알고리즘이 없어 렌즈(DW9800/DW9714)를 움직이지 않는다.
- 초점거리와 센서 크기를 보고하지 않아 앱이 렌즈를 1x로만 표시한다.
- `cam2-cycle`(NDK Camera2 시험 도구)은 YUV_420_888 ImageReader에서 cameraserver가 출력 버퍼를 받지 못해 프레임 0장으로 끝난다. 도구 쪽 문제로 보이며 미해결이다.
- 영상 품질, 동영상, 장시간 사용은 미시험이다.
- 새 sdexport1 직렬 로그와 fastboot 로그의 기기 시리얼은 지웠다.
