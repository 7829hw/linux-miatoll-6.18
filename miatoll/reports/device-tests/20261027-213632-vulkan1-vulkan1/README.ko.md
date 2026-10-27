# vulkan1 첫 부팅 — Turnip 인식, Alpine vkcube는 segfault

2026-10-27 KST. gpu2 위에 다음을 RAM 디스크에 추가했다.
- Turnip: Mesa 25.1.9 `-Dvulkan-drivers=freedreno`. host glslangValidator는 Ubuntu glslang-tools 16.2.0-2.
- Alpine vulkan-loader 1.4.313과 vulkan-tools(vkcube, vulkaninfo).

## 결과 (장치 런타임)
- `vulkaninfo --summary`:
  - Vulkan Instance 1.4.313. 인스턴스 확장에 `VK_KHR_display`, `VK_EXT_acquire_drm_display`가 있다.
  - GPU0 `Turnip Adreno (TM) 618`, apiVersion 1.3.311, driver Mesa 25.1.9(DRIVER_ID_MESA_TURNIP), conformanceVersion 1.2.7.1.
- `vkcube --wsi display`: `Selected GPU 0` 출력 직후 Segmentation fault(종료 139). 화면은 바뀌지 않았다(사용자 관찰).
  - 다음 라운드의 `vk-display-probe`에서 Turnip의 display WSI는 정상이었다. 따라서 crash는 Alpine vkcube 바이너리 쪽 문제로 판단하며, 원인은 분석하지 않았다.
