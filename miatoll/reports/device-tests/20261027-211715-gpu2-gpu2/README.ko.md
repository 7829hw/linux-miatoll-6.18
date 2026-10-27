# gpu2 실기기 결과 — Mesa freedreno로 화면 렌더링 확인

2026-10-27 KST. gpu1과 같은 커널과 DT에 Mesa 25.1.9와 kmscube를 RAM 디스크로 추가했다.
- Mesa: freedreno만, EGL/GBM/GLES2, LLVM·X11·Wayland 없음.
- kmscube: 2c1f2646. Mesa·kmscube 모두 고정 SHA-256으로 교차 빌드했다.
- 런타임 라이브러리(musl 로더, libdrm, libpciaccess, zlib, libstdc++, libgcc_s)는 APKINDEX로 검증한 Alpine v3.22 패키지에서 가져왔다.
- 빌드 입력과 결과 기록: `miatoll/reference/gpu2/`, 스크립트: `miatoll/gpu/`. 이미지는 91.8 MB(128 MiB 안).

## 결과 (장치 런타임)
- EGL 1.5(Mesa Project), `OpenGL ES 3.2 Mesa 25.1.9`, vendor `freedreno`, renderer `FD618`, GLSL ES 3.20.
- 오프스크린(`kmscube -O -D /dev/dri/renderD128 -v 1080x2400 -c 300`): 299프레임 0.336 s(약 890 fps). 종료 코드 0.
- 화면(`kmscube -D /dev/dri/card0`, legacy KMS): 1499프레임 24.98 s, 60.0 fps(vsync).
  - 사용자 관찰: 회전하는 색상 입방체가 보였다. 종료 뒤 텍스트 콘솔로 돌아왔다.
- 렌더링 뒤 `gpu-probe` faults 0, `GPU_PROBE_OK`. dmesg에 fault·hang·recover·underrun이 없었다.
- devfreq가 렌더링 중 주파수를 전환했다(최고 750 MHz 단계 사용).

## 참고
- 첫 화면 시도는 stdin이 `/dev/null`이라 kmscube가 첫 프레임 뒤 "user interrupted"로 끝났다. 이후 `sleep | kmscube`로 실행했다.
- `/usr/bin`은 init PATH에 없어 절대 경로로 실행한다.

## 미검증
- 장시간 부하에서의 발열·전력·DVFS.
- 복잡한 셰이더와 GLES3 적합성 테스트(dEQP 등). Vulkan(Turnip)은 빌드하지 않았다.
- Android GPU 스택과의 호환(KGSL 대신 DRM/MSM).
