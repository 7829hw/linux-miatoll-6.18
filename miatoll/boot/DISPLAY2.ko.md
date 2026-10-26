# curtana Huaxing 화면 인계 RAM 시험: display2

브랜치 `miatoll/6.18-display2`, 커널 `6.18.58-miatoll-display2+`.
display1의 부팅은 성공했지만 실제 화면·백라이트가 꺼지고, 부트로더 화면 주소에 대한
SMMU fault와 framebuffer 플래그 경고가 확인돼 수정 후보를 준비했다.
2026-10-27 `20261027-015228` 회차에서 사용자가 시험 문구·색상과 백라이트 켜짐을 확인했다.
SMMU fault와 클록/fbdev 경고는 사라졌다. [실기기 기록](../reports/device-tests/20261027-015228-display2/README.ko.md)

## 변경과 검증 범위

1. 별도 display2 DT에서 MDSS `resets = <&dispcc DISP_CC_MDSS_CORE_BCR>`를 연결한다.
   기존 upstream `msm_mdss_reset()`이 장치 초기화 때 reset을 요청한다.
   SC7180 DISPCC의 reset map과 공통 MDSS 바인딩에 이미 있는 기능을 사용한다.
2. `msm_gem_get_vaddr()`로 매핑한 MSM fbdev 시스템 RAM에 `FBINFO_VIRTFB`를 지정한다.
3. RAM 사용자 공간에서 native framebuffer가 생기면 표준 `fb0/blank=0`을 한 번 요청하고,
   `MIATOLL LINUX DISPLAY TEST 2` 및 색상 문구를 VT에 쓴다.
4. 기존 진단에 디스플레이 clock summary를 추가한다. IRQ·DRM state·WLED 읽기값·dmesg와
   실제 화면 관찰을 함께 확인한다. 밝기 자동 변경 시험은 하지 않는다.

IOMMU 주소 변환과 fault 보고, DPU/MDSS·클록·WLED 드라이버 구현, 패널 명령·타이밍은
display1 기준을 유지한다. 공통 reset helper를 새로 이식하거나 오류를 숨기는 우회는 하지 않았다.
host의 reset 연결 검증은 실제 하드웨어 reset 성공의 검증이 아니다.

모뎀·GPU·터치·오디오 등은 계속 비활성화하고 firmware/모듈이 없는 RAM initramfs를 사용한다.
Android 파일시스템은 마운트하지 않으며 UFS 디스크는 읽기 전용으로 설정한다.
기존 boot1/display1 이미지·ZIP·로그는 보존한다.

## WSL 실행

Windows 관리자 PowerShell에서 한 번 `usbipd bind --hardware-id 18d1:d00d`와
`usbipd policy add --effect Allow --operation AutoBind --hardware-id 1d6b:0104`를 실행하고,
WSL에 `wsl/51-curtana-ramtest.rules`를 `/etc/udev/rules.d/`로 설치한다. 그 뒤 Fastboot 상태에서:

```sh
python3 miatoll/boot/ram_boot_test.py boot ../dist/miatoll-display2/display2-report.json
python3 miatoll/boot/ram_boot_test.py observe miatoll/reports/device-tests/<회차> \
  --screen '<사용자 관찰>' --backlight on|off [--confirmed]
```

실행기는 장치를 `usbipd.exe attach`로 WSL에 붙이고 Windows 절차와 같은 순서·명령 범위로 동작한다.

## Windows 실행

1. `miatoll-display2-windows.zip`을 **새 폴더**에 압축 해제한다.
2. 휴대폰을 전원 + 볼륨 아래로 Fastboot에 진입시키고 PC에 연결한다.
3. 새 폴더에서 PowerShell을 열어 실행한다.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Test-Display2.ps1
```

fastboot가 PATH에 없으면 `-Fastboot 'C:\platform-tools\fastboot.exe'`를 추가한다.
실행 순서는 해시 확인→제품명 확인→`reboot bootloader`→RAM 부팅이다.
bootloader 재시작은 **시험 전 Fastboot 세션을 한 번 새로 시작**하는 단계다.
그 뒤 `fastboot boot`로 이미지를 RAM에 한 번 전송한다.
`Sending 'boot.img'`는 RAM 전송이며, `flash`/`erase`/파티션 쓰기 명령은 없다.
스크립트는 bootloader 재시작과 RAM 전송 전에 각각 설명을 출력한다.

시험 후 다음을 보낸다.

- `display2-fastboot-날짜시간.txt`
- `display2-serial-날짜시간.txt`
- 화면의 시험 문구/색상 표시 여부와 백라이트 상태

로그 수집이 끝난 뒤 기기가 스스로 Fastboot로 돌아오면 그 시점과 마지막 화면도 기록한다.
같은 세션에서 이미지를 반복 전송하지 않는다. 전원 버튼을 길게 눌러 RAM 시험을 종료할 수 있다.

이미 display2가 실행 중일 때 USB 로그만 수집하려면 다음처럼 실행한다.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Test-Display2.ps1 -CaptureOnly
```

필요하면 실제 COM 포트 번호로 `-Port COM5` 등을 추가한다.
`DISPLAY2_LOG_CAPTURED`는 USB 진단 수집 판정이며 물리 화면 성공을 뜻하지 않는다.

## 호스트 검증과 재현

ARM64 Image/DTB/모듈 빌드, display/USB 내장 설정, compiled DT reset phandle 및
DPU↔DSI↔패널 graph·부모 활성·IOMMU 보존, ARM64 shim 인계와 invalid FDT/initrd 입력 거부,
정적 BusyBox와 셸 문법, boot header v2/AVB 해시/AOSP 재추출을 확인한다.
Windows의 새 display2 분기와 실제 화면/절전/안정성은 별도 실기기 검증이다.

```sh
cd <workspace>/miatoll-6.18
OUT_DIR=/data/hwkim/kernel/out-miatoll-display2 \
DIST_DIR=/data/hwkim/kernel/dist/miatoll-display2/kernel \
JOBS=48 bash miatoll/build.sh miatoll/configs/display2.config
PATH=/data/hwkim/kernel/tools/llvm18/usr/lib/llvm-18/bin:$PATH \
make O=/data/hwkim/kernel/out-miatoll-display2 ARCH=arm64 LLVM=1 qcom/sm7125-xiaomi-curtana-display2.dtb
python3 miatoll/boot/test_shim.py \
  --dtb /data/hwkim/kernel/out-miatoll-display2/arch/arm64/boot/dts/qcom/sm7125-xiaomi-curtana-display2.dtb \
  --output-dir /data/hwkim/kernel/out-miatoll-display2-shim-test
python3 miatoll/boot/package_boot1.py --profile display2
```
