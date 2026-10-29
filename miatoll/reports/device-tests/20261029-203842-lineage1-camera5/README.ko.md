# lineage1 카메라 CCI0 master 1 안정화

2026-10-29 KST. 이전 결과: [RAW 캡처 기록](../20261029-201216-lineage1-camera3/README.ko.md).

## 증상
CCI0 master 1(S5K5E9, OV8856, DW9714)에서 첫 쓰기가 간헐적으로 타임아웃됐다.
- 예: `master 1 queue 0 timeout`, `ov8856: failed to write reg 0x0103`.
- 그 뒤 STREAMON이 EIO로 실패하면 VFE는 재부팅 전까지 프레임을 내지 않았다.

## 원인 확인
- 같은 부팅에서 세션 사이에 4초 이상 쉬면 I2C 오류가 없었다. 이때 CCI는 `suspended`였다.
- 직전 세션 직후 CCI가 `active`인 상태에서 시작하면 두 번 모두 타임아웃됐다.
- 대기 중 `ldo13`(L13A, 센서·VCM I/O와 CCI 풀업 전원)은 `disabled`, 사용자 0이었다.
- 마지막 센서가 꺼질 때 L13A도 꺼진다. 그 뒤 CCI 전원 도메인이 꺼졌다 켜지기 전까지 master 1이 멈춘다.

## 수정과 결과
`c2980e25a195`: curtana DT에서 `vreg_l13a_1p8`을 `regulator-always-on`으로 둔다.

| 시행 | 커널 | 결과 |
| --- | --- | --- |
| camera4-l13a | 실험 커밋(같은 내용, lineage1 DT) | 연속 8회 성공, 이어 네 센서 번갈아 50회 연속 50/50. CCI 타임아웃 0, DW9714 probe 실패 사라짐 |
| camera5 | `c2980e25a195` | 네 센서 번갈아 20회 연속 20/20. 타임아웃 0, DW9714 실패 0, `ldo13 enabled` |

- camera5 첫 `fastboot boot`(20261029-202511)은 부트로더 `unknown command`로 실패했다. 사용자가 USB를 다시 연결한 뒤 한 번 더 보냈다(이 디렉터리).
- 남은 일: Android 카메라 HAL(libcamera 등), 초점(DW9800/DW9714), 영상 품질, 대기 전력 영향 측정.
