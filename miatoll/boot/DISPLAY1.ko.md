# curtana Huaxing 네이티브 화면 RAM 시험: display1

커널은 공식 Linux 6.18.58과 6.14.7 포크에서 선별 이식한 하드웨어 구현을 사용한다.
시험 브랜치는 `miatoll/6.18-display1`, 실행 버전은 `6.18.58-miatoll-display1+`다.
검증된 boot1 브랜치·이미지·ZIP과 원본 로그는 그대로 보존한다.

## 시험 배경과 범위

사용자는 boot1 실행 중 화면이 보이지 않고 백라이트만 켜져 있다고 보고했다.
boot1은 MDSS/DSI/PHY/WLED를 비활성화했고, dmesg에도 native DRM/framebuffer 등록이 없었다.
부트로더가 남긴 백라이트 상태는 새 커널의 화면 구동 검증과 구분한다.

display1은 boot1 DT를 포함하고 다음만 변경한다.

- 6.14.7에서 가져온 Huaxing FT8756 패널 경로의 MDSS/DPU/DSI0/10nm PHY/WLED를 활성화한다.
  패널 명령·전원·reset GPIO·DSI 타이밍 및 정상 IOMMU 경로는 현재 이식 코드 그대로다.
- WLED 초기 밝기를 256으로 지정한다. 밝기 자동 변경/반복 시험은 하지 않는다.
- 드라이버가 없던 BWMON 두 노드와 모듈을 공급하지 않는 Venus 노드를 비활성화한다.
- GPU/터치/모뎀/ADSP/CDSP/IPA/무선/카메라/오디오/SD 등 boot1의 비활성 상태를 유지한다.

DRM fbdev와 VT 콘솔을 사용한다. native `msmdrmfb`가 생성되면 tty1에
`MIATOLL LINUX DISPLAY TEST 1`, 커널 버전과 빨강·초록·파랑 문구를 쓴다.
화면에 실제로 보이는지 사용자가 확인해야 한다. banner 쓰기 완료나 DRM 등록만으로
물리 화면 표시 성공을 판정하지 않는다.

USB ACM은 검증된 VID/PID·serial 설정을 유지한다. RAMdisk에는 firmware와 모듈이 없고
Android 파일시스템을 마운트하지 않는다. UFS 디스크는 소프트웨어 읽기 전용으로 설정한다.
새 후보는 설치된 파티션에 기록하지 않고 `fastboot boot`로 RAM에서 실행한다.

## Windows 실행

1. `miatoll-display1-windows.zip`을 새 폴더에 압축 해제한다. 기존 boot1 폴더와 구분한다.
2. 휴대폰의 **전원 + 볼륨 아래**를 길게 눌러 Fastboot에 진입하고 Windows PC에 연결한다.
3. 압축 해제 폴더의 PowerShell에서 실행한다. 기존 fastboot가 PATH에 있어야 한다.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Test-Display1.ps1
```

경로를 직접 지정하려면 `-Fastboot 'C:\platform-tools\fastboot.exe'`를 추가한다.
스크립트는 이미지 SHA256과 `curtana` 제품명을 확인하고 bootloader 새 세션에서 RAM 부팅을
한 번만 요청한다. 이후 USB COM 포트로 `display-probe`와 BusyBox dmesg를 수집한다.
flash/erase/format/unlock/파티션 변경 명령은 없다.

보낼 결과:

- `display1-fastboot-날짜시간.txt`
- `display1-serial-날짜시간.txt`
- 화면에 시험 문구와 색상이 보이는지, 계속 검은지, 백라이트가 켜져 있는지에 대한 관찰

`DISPLAY1_LOG_CAPTURED`는 USB 진단 수집의 판정이며 화면 성공을 뜻하지 않는다.
USB가 연결되지 않으면 같은 bootloader 세션에서 이미지를 반복 전송하지 말고 Fastboot 로그와
화면 상태를 남긴다. 전원 버튼을 길게 눌러 RAM 시험을 종료할 수 있다.

현재 display1이 실행 중일 때 COM 로그만 다시 수집하려면 다음처럼 실행한다.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Test-Display1.ps1 -CaptureOnly
```

자동 검색이 안 되면 실제 포트 번호로 `-Port COM5` 등을 추가한다.

## 진단 및 검증 범위

수집 항목은 커널/DT 프로필·읽기 전용 UFS·USB, framebuffer 이름/크기/bpp,
DSI connector status/modes, DRM atomic state, WLED 밝기, IRQ, regulator 상태와 dmesg다.
실제 framebuffer scanout, DSI/패널 초기화 오류, SMMU 인계 및 backlight 상태를 함께 판정한다.

호스트에서는 ARM64 Image/DTB/모듈 빌드, 필수 display/USB 내장 설정,
compiled DT의 DPU↔DSI↔패널 graph·부모 활성·reset/WLED 연결·IOMMU 보존,
ARM64 shim 인계와 잘못된 firmware 입력 거부, 정적 BusyBox/셸 문법,
실행 영역 크기·boot header v2·AVB 해시·AOSP 재추출을 검증한다.
이 검사는 실기기 화면 성공을 보장하지 않는다. Windows의 새 display1 캡처 분기는 아직 미검증이다.

기존 로컬 6.18.0 화면 시험의 DPU reset/fbdev 변경은 이 후보에 추가하지 않았다.
현재 드라이버의 실기기 로그로 문제가 재현될 때만 필요한 수정을 판단한다.

## 재현

```sh
cd /data/hwkim/kernel/miatoll-6.18
OUT_DIR=/data/hwkim/kernel/out-miatoll-display1 \
DIST_DIR=/data/hwkim/kernel/dist/miatoll-display1/kernel \
JOBS=48 bash miatoll/build.sh miatoll/configs/display1.config
PATH=/data/hwkim/kernel/tools/llvm18/usr/lib/llvm-18/bin:$PATH \
make O=/data/hwkim/kernel/out-miatoll-display1 ARCH=arm64 LLVM=1 qcom/sm7125-xiaomi-curtana-display1.dtb
python3 miatoll/boot/test_shim.py \
  --dtb /data/hwkim/kernel/out-miatoll-display1/arch/arm64/boot/dts/qcom/sm7125-xiaomi-curtana-display1.dtb \
  --output-dir /data/hwkim/kernel/out-miatoll-display1-shim-test
python3 miatoll/boot/package_boot1.py --profile display1
```
