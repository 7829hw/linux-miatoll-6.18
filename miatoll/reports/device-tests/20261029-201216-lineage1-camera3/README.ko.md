# lineage1 카메라 RAW 캡처 (커널 경로)

2026-10-29 KST. Android(SD 카드 LineageOS 22.2) root 셸에서 `miatoll/boot/cam-capture.c`(NDK r30, 정적)로 시험했다.
Android 카메라 HAL은 아직 없다. 이 기록은 센서 → CSIPHY → CSID → VFE RDI → 비디오 노드의 RAW Bayer 수신만 다룬다(ISP 없음).

## 커널 변경
- `3cdf3fd4487f`: asidko/qcom-camss-mainline `cd6cd249` 패치 3개를 6.18 구조로 옮겼다.
  - v1.2.2 2PH 레인 표.
  - CTRL0 0x02와 CTRL33 0x01 쓰기. 6.18의 공용 함수라 CAMSS_7180에서만 쓴다.
  - `vfe_flush_buffers()`의 buf 정리.
- `9a13f9f76cb1`: lineage1에서 CAMSS·CCI0/1을 켜고 CAMSS, CCI, 센서, VCM 드라이버를 내장으로 만들었다.
- `2975e5acc7cf`: 포크에서 가져온 SC7180 CSIPHY 리소스에 `.id`가 없어 네 개가 모두 `msm_csiphy0`였다.
  - 6.18은 이 id로 이름, 클럭, CSID의 PHY 선택을 정한다.
  - 수정 전 camera1에서 OV16A1Q(CSIPHY3)는 STREAMON 뒤 프레임이 오지 않았다.

## probe (camera1)
- 칩 ID 확인: S5KGM2 12-0010(메인), S5K5E9 13-002d(매크로), OV16A1Q 14-0010(전면).
- OV8856 13-0036(초광각)도 드라이버에 붙었다.
- 렌즈: DW9800 12-000c 바인드. DW9714 13-000c는 probe 중 CCI0 master 1 타임아웃으로 쓰기에 실패했다.

## RAW 수신 (camera2, camera3)
| 센서 | 경로 | 형식 | 결과 |
| --- | --- | --- | --- |
| OV16A1Q | CSIPHY3 → CSID0/VFE0, CSID1/VFE1 | 2304x1728 SBGGR10P | 약 30 fps, 매 프레임 평균 58 |
| S5KGM2 | CSIPHY1 → CSID1/VFE1, CSID0/VFE0 | 2000x1500 SGRBG10P | 약 60 fps |
| S5K5E9 | CSIPHY2 → CSID2/VFE-lite | 2592x1944 SGRBG10P | 프레임 수신 |
| OV8856 | CSIPHY0 → CSID0/VFE0, CSID1/VFE1 | 1640x1232 SGRBG10P | 성공과 실패가 섞임 |

- 단순 디베이어로 본 OV16A1Q 프레임은 실내 천장·벽의 실제 영상이었다. 영상 파일은 Git에 넣지 않았다.
- S5KGM2는 폰이 놓인 상태라 어둡고 흐렸다. 초점(DW9800)과 화질은 미확인이다.

## 문제
- CCI0 master 1(S5K5E9, OV8856, DW9714)의 첫 쓰기가 간헐적으로 타임아웃된다.
  - 예: `ov8856 13-0036: failed to write reg 0x0103`.
  - 그 뒤 STREAMON이 EIO로 실패하면 해당 VFE는 재부팅 전까지 프레임을 내지 않는다.
  - camera2에서는 VFE0이 0으로 채워진 프레임만 냈다.
- CCI 런타임 suspend에서 `cam_cc_camnoc_axi_clk status stuck at 'on'` 경고가 난다.
- 미시험: Android 카메라 HAL, ISP/3A, 초점, 장시간 스트리밍.
