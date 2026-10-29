# lineage1 진동 타격감과 세기 단계 (SD 카드 LineageOS 22.2)

2026-10-29 KST. 커널 `0b082ec93905`, 기기 트리 `bd6e8ca`(외부 저장소).
이전 결과: [lineage27 진동 기록](../20261029-181230-lineage1-lineage27-vibrator/README.ko.md)는 ff-memless 사인파 반복 재생이었고, 사용자는 4.14 LineageOS보다 타격감이 부족하다고 보고했다.

## 원인 (장치 레지스터 확인)
- 6.14.7 포크 드라이버는 `awinic,aw8624`도 AW8695 레지스터 맵으로 다뤘다. AW8624에는 부스트가 없고 0x31-0x3c, 0x46/0x47의 의미가 다르다.
- regmap debugfs 덤프(이전 커널):
  - WAVECTRL 0x13, BRAKE0/1 0x1b/0x16: boost-debug 값이 브레이크 레지스터에 들어감.
  - SW_BRAKE(0x39) 0x08: RAM 모드 브레이크가 꺼져 있음.
  - 정지 확인은 GLB_STATE(0x47)이 아니라 0x46(BEMF_BRA_FAC)을 읽었다.
  - f0 측정의 LRA_SRC 비트가 ANACTRL(0x38)이 아닌 0x36에 쓰였다.
- 다운스트림 비교 대상: LineageOS android_kernel_xiaomi_sm6250 lineage-22.2 `803b5586`, `drivers/misc/aw8624_haptic/aw8624.c`, `cust-atoll-idp.dtsi`.

## 커널 변경 (`0b082ec93905`)
- 칩 ID로 레지스터 배치를 고른다. AW8624는 부스트 설정을 건너뛰고 R_SPARE bit 7을 세운다.
- f0 보정 뒤 벤더 설정을 적용한다: SW_BRAKE = `awinic,sw-brake`(curtana 0x2c), THRS_BRA_END 0, NUM_OV_DRIVER 0.
- 벤더 파형 라이브러리 `aw8624_haptic.bin`(sha256 51dff3f7…, TheMuppets sm6250-common `b93a6532`)을 probe에서 SRAM에 쓴다.
  - 체크섬, base 0x800, FIFO 임계값을 벤더 방식대로 검사·설정한다. 없으면 기존 사인파로 돌아간다.
  - `package_boot1.py`가 lineage1 램디스크 `/lib/firmware`에 넣는다. probe가 `/vendor` 마운트보다 먼저다.
- ff-memless 대신 FF 장치:
  - FF_PERIODIC/FF_CUSTOM `custom_data[0] = n`이면 라이브러리 파형 n+1을 한 번 재생한다(QTI vibrator HAL 규약).
  - 게인(DATDBG 0x3b)은 magnitude에서 정한다.
  - FF_CONSTANT/FF_RUMBLE은 마지막 파형(11번, f0 한 주기)을 길이만큼 반복한다.

## Android 쪽 (기기 트리, 저장소 밖)
- HAL perform()이 Effect 값을 FF_CUSTOM으로 보낸다. 지원 효과는 클릭, 더블클릭, 틱, 썸프, 팝, 헤비클릭이다.
- 라이브러리의 2, 3, 5번 파형은 비어 있어 더블클릭·틱·팝은 4.14와 같이 사실상 진동이 없다.
- Settings 오버레이 `config_vibration_supported_intensity_levels = 3`로 세기 단계를 보인다.
- 세기 배율: 약 0.25, 중간 0.5, 강 1.0. 이전 0.5/0.75/1.0은 단계 차이가 거의 없었다(사용자).

## 장치 런타임 결과
- 부팅 로그 `Loaded 11 waveforms from aw8624_haptic.bin`, 입력 장치 `aw8695-haptics`.
- 칩 레지스터: SW_BRAKE 0x2c, WAVECTRL 0x01, ANACTRL 0x29, BRAKE0-2 기본값(0x7f/0x9f/0x87).
- `cmd vibrator_manager feedback 3`에서 터치 세기 1/2/3단계의 DATDBG를 읽었다: 0x20/0x40/0x80.
- 사용자 확인:
  - lineage25: 전체 게인 재생에서 "진동이 너무 강하다".
  - lineage28: "단계별 차이가 확실히 느껴진다". 0단계(끄기)는 진동 없음.
- 미확인: 알림·벨소리 진동의 세기 단계(`oneshot`은 터치 단계와 무관하게 0x80), DRV2624 변형, 장시간 사용.
- 파형 쓰기로 probe가 0.68 s에서 약 3.4 s로 늦어졌다(동기 probe).
- 새 sdexport1 직렬 로그의 `androidboot.serialno`는 지웠다.
