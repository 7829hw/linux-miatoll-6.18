# vulkan1 vk-display-probe — Turnip 전송 명령과 VK_KHR_display 표시 확인

2026-10-27 KST. 단계별 Vulkan 점검 도구 `vk-display-probe`(miatoll/gpu/vk-display-probe.c)를 추가했다.

## 결과 (장치 런타임)
- `vkCmdFillBuffer` 64 KiB: 16384 word 중 불일치 0.
- display: `monitor` 1080×2400, mode 1080x2400@60, plane 1개. display plane surface 지원, 형식 50(B8G8R8A8_SRGB), swapchain 이미지 2개.
- 빨강·초록·파랑 clear 프레임을 FIFO로 15 s 동안 900프레임(60.0 fps) 표시했다. 결과 `VK_PROBE_OK`.
- 사용자 관찰: 화면 전체가 1초마다 빨강→초록→파랑으로 바뀌었다.
- 이후 GPU faults 0.
