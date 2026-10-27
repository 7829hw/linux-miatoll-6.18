# vulkan1 vk-shader-probe — Turnip 셰이더 렌더링(오프스크린 픽셀 검증 + 화면 표시)

2026-10-27 KST. `vk-shader-probe`(miatoll/gpu/vk-shader-probe.c)를 추가했다.
- triangle.vert/triangle.frag(GLSL 450)를 빌드 때 glslangValidator로 SPIR-V로 만든다.
- 정점 위치·색은 `gl_VertexIndex`, 회전각은 push constant로 준다.

## 결과 (장치 런타임)
- 오프스크린 256×256 R8G8B8A8 렌더 → 버퍼 복사 → 픽셀 검사(모두 ok):
  - 중심 (128,128) = 84,87,85: 세 정점 색이 고르게 섞였다.
  - 모서리 (2,2), (253,253) = 0,0,0: clear 색 그대로다.
  - 빨강 정점 근처 = 234,11,9, 초록 정점 근처 = 11,230,14, 파랑 정점 근처 = 11,16,228.
- 화면(VK_KHR_display, FIFO): 회전 삼각형 20 s 동안 1199프레임, 60.0 fps. 결과 `VK_SHADER_OK`.
- 사용자 관찰: 검은 배경에 색이 섞인 삼각형이 회전했다.
- 이후 GPU faults 0, `GPU_PROBE_OK`. fault·hang·underrun 로그가 없었다.

## 미검증
- Vulkan CTS 같은 적합성 테스트, compute 셰이더, 장시간 부하.
- vkcube(Alpine) crash 원인.
