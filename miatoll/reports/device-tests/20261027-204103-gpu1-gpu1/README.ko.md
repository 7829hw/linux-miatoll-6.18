# gpu1 실기기 결과 — Adreno A618 초기화와 명령 실행 확인

2026-10-27 KST. audio12(TX SoundWire 유지·2.7 V MBHC 임계값) 위에 GPU·GMU를 켰다. 같은 부팅에서 시험했다.

추가한 firmware(모두 고정된 입력):
- `qcom/a630_sqe.fw`(34188 B): Alpine linux-firmware-qcom 20250509-r0.
- `qcom/a630_gmu.bin`(32768 B): 같은 패키지. APK SHA-256·control checksum·datahash를 확인했고, LICENSE.qcom은 linux-firmware 20250509 태그로 고정했다.
- `qcom/sm7125/miatoll/a615_zap.mbn`(14272 B): firmware-xiaomi-miatoll a7073ad1, Git blob SHA-1 확인.
출처 기록: `miatoll/reference/gpu1/firmware-sources.json`.

## 결과 (장치 런타임)
- `adreno_bind Found GPU: 6.1.8.0`, `fast_rate=750000000`. SQE/GMU firmware를 로드했고 `/dev/dri/renderD128`이 생겼다.
- zap shader: 로드 오류도, `Zap shader not enabled - using SECVID_TRUST_CNTL` 경고도 없다. GPU 하드웨어 초기화가 성공했으므로 secure world 로드가 성공한 것으로 판단한다.
- devfreq `5000000.gpu`: 180/267/355/430/565/650/750 MHz(speed bin 3), governor simple_ondemand.
- 유휴 상태에서 GPU·GMU runtime PM은 `suspended`였다.
- `gpu-probe`: 3D 파이프에 `CP_MEM_WRITE` 1개를 제출했다.
  - gpu_id 618, chip_id 0x06010800, GMEM 512 KiB, max_freq 750 MHz, VA 0x1_0000_0000 + 4 GiB, faults 0.
  - 쓰인 값 `0xc0ffee18`이 일치했다. 첫 실행은 전원 투입 포함 4.8 ms.
- 반복: 연속 30/30(약 1.4 ms). suspend 뒤 재개 10/10(약 4.5–5.5 ms). 반복 뒤 faults 0, hang/recover 로그 없음.
- 사용자 관찰: 화면(텍스트 배너/콘솔)이 정상 표시됐다. GPU를 켜도 디스플레이에 영향이 없었다.

## 미검증
- 실제 렌더링(Mesa freedreno/Turnip 등 userspace 드라이버)과 셰이더 실행.
- 부하 상태의 DVFS·발열·전력.
- Android GPU HAL(KGSL ABI)과의 호환. 6.18 DRM/MSM은 `/dev/kgsl-3d0`을 제공하지 않는다.
