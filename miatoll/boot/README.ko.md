# curtana Linux 6.18.58 단독 RAM 부팅 시험: boot1

대상은 기존 Xiaomi curtana다. 현재 단계는 Android/LineageOS를 시작하지 않고
새 커널이 `/init`과 USB 진단 셸에 도달하는지 확인하는 것이다.

## 이번 후보

- 커널: `6.18.58-miatoll-boot1+`
- 커널 코드는 6.14.7 기반 선별 이식 그대로다. 빠졌던 upstream QUSB2 PHY를 내장했다.
- 첫 시험 DT에서 모뎀/ADSP/CDSP/IPA/Wi-Fi/Bluetooth/GPU/네이티브 디스플레이/터치/
  카메라/오디오/진동/Type-C 역할 전환/SD를 비활성화했다.
- 부트로더가 남긴 framebuffer와 USB peripheral 콘솔을 사용한다.
- RAM initramfs에는 firmware, 모듈, Android init/데몬, 파티션 마운트 코드가 없다.
  발견된 UFS 전체 디스크는 메모리상의 read-only 플래그를 설정한다.
- 부팅 경로는 기존에 확인한 stock 외부 DTB → ARM64 중간 로더 → 새 mainline DTB 방식이다.
  설치된 boot/dtbo 파티션을 수정하지 않는다.
- 업로드됐던 원본 boot.img 파일은 현재 없지만, 보존된 원본 DTB/커널 추출물 및
  SHA256을 확인한 기존 audio2 컨테이너로 주소·AVB 형식을 재현했다. 이전 커널/ramdisk는 넣지 않았다.
- AVB는 `NONE` 해시 메타데이터다. OEM 인증 서명을 확보했다는 의미는 아니다.

## Windows에서 실행

1. `miatoll-boot1-windows.zip`을 다운로드하고 새 폴더에 압축을 푼다.
2. 기존 curtana를 **전원 + 볼륨 아래**로 Fastboot에 진입시켜 Windows PC에 연결한다.
3. 압축을 푼 폴더에서 PowerShell을 열고 실행한다. 기존 fastboot가 PATH에 있어야 한다.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Test-Boot1.ps1
```

fastboot 경로를 직접 지정하려면 다음처럼 실행한다.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Test-Boot1.ps1 -Fastboot 'C:\platform-tools\fastboot.exe'
```

스크립트는 이미지 SHA256과 제품명 `curtana`를 확인하고, 새 bootloader 세션에서
`fastboot boot`를 **한 번만** 실행한다. flash/erase/format/unlock 명령은 실행하지 않는다.
새 Linux COM 포트가 나타나면 115200 baud로 열고 `uname -r`, `boot-probe`를 수집한다.
현재 Git의 스크립트는 이어서 `/bin/busybox dmesg`도 수집한다.
최초 배포 ZIP과 그 안의 스크립트는 시험 증거 보존을 위해 변경하지 않았다.

성공 출력:

```text
BOOT1_CONFIRMED: 6.18.58-miatoll-boot1+ reached a RAM userspace and USB shell.
```

같은 폴더의 `boot1-fastboot-날짜시간.txt`와 `boot1-serial-날짜시간.txt`가 결과다.
`Booting OKAY`만으로 성공으로 판단하지 않는다. 새 버전·DT 프로필·probe 끝 표시를 모두 확인한다.
화면이 검더라도 이 세 항목이 USB에서 확인되면 커널과 RAM 사용자 공간 진입은 확인된다.

## COM 포트만 다시 수집

이미 boot1이 실행 중이면 이미지를 다시 보내지 않고 다음처럼 COM 포트만 연다.
`COM5`는 장치 관리자에서 확인한 실제 포트로 바꾼다.

2026-10-26 첫 실기기 로그에서 커널/USB 셸 진입을 확인했지만 `/bin/dmesg` 링크 누락으로
커널 상세 로그 수집이 실패했다. 현재 스크립트 파일을 기존 압축 해제 폴더에 복사하고
`-CaptureOnly`로 실행하면 실행 중인 최초 이미지에서도 BusyBox applet으로 로그를 얻는다.
포트를 지정하지 않으면 기존과 같이 Linux COM 포트를 자동 검색한다.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Test-Boot1.ps1 -CaptureOnly -Port COM5
```

COM 포트가 없거나 `The system has been destroyed` 등이 나타나면 같은 세션에서
이미지를 재전송하지 말고 Fastboot 로그와 화면에 나타난 내용을 남긴다.
시험을 끝낼 때 전원 버튼을 길게 눌러 재시작하면 설치된 OS로 돌아갈 수 있다.

## 검증 범위

호스트에서 별도 boot1 Image/DTB 빌드, 필수 내장 USB 설정, 최소 DT 상태/USB 부모 노드,
ARM64 BusyBox 실행/셸 문법, 로더의 실제 ARM64 모의 entry 실행, 잘못된 FDT/initrd 입력 거부,
Image 실행 영역, AVB 해시, AOSP 독립 재추출을 확인했다.

QEMU에서 Linux 전체를 부팅한 검사는 아니다. 최초 배포 스크립트의 Windows COM 통신과
실제 curtana 부팅은 사용자가 전달한 `20261026-232305` 로그로 확인했다.
기록은 `miatoll/reports/device-tests/20261026-232305-boot1/`에 있다.
추가한 BusyBox dmesg 캡처 경로도 후속 `20261026-233342` 로그의 종료 코드 0으로 확인했다.
그 결과는 `miatoll/reports/device-tests/20261026-233342-boot1-kernel-log/`에 있다.
새 RAMdisk의 dmesg 링크 자체를 실기기로 검증한 결과는 아니다.
패키지 생성 시점의 `device_boot_confirmed=false` 기록은 보존한다.

## 재현

```sh
cd /data/hwkim/kernel/miatoll-6.18
OUT_DIR=/data/hwkim/kernel/out-miatoll-boot1 \
DIST_DIR=/data/hwkim/kernel/dist/miatoll-boot1/kernel \
JOBS=48 bash miatoll/build.sh miatoll/configs/boot1.config
PATH=/data/hwkim/kernel/tools/llvm18/usr/lib/llvm-18/bin:$PATH \
make O=/data/hwkim/kernel/out-miatoll-boot1 ARCH=arm64 LLVM=1 qcom/sm7125-xiaomi-curtana-boot1.dtb
python3 miatoll/boot/test_shim.py
python3 miatoll/boot/package_boot1.py
```

원본 6.18.58 산출물과 기존 6.18.0 실기기 시험 파일은 보존했다.
