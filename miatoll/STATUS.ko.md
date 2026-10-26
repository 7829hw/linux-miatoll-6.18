# Linux 6.18 기반 miatoll 지원 현황

2026-10-26 KST. 현재 개발 브랜치: **`miatoll/6.18-sm7125`**.
공식 Linux **v6.18.58**을 기반으로, 6.14.7 포크의 Xiaomi 하드웨어 구현을 직접 선별 이식했다.
기존 로컬 커널 수정은 보존 브랜치와 백업에 남겼다.

**확인한 단계는 소스 이식·컴파일·정적 검사다. 이 새 커널의 실기기 동작과 LineageOS 부팅은 미검증이다.**

## 검증 결과

빌드/검증 커밋: `820e88dce8314e351f3e23fb9e9362c0efb77e76`.
이후 결과 보고서만 별도 커밋했다. 빌드의 실제 값은 `reports/build-validation.json`에 있다.

| 항목 | 결과 |
| --- | --- |
| 공식 기반 | v6.18.58, `2926d88bb7fc4608fd942453d929c39e4e5ec006`의 실제 후속 커밋 |
| 릴리스 문자열 | `6.18.58-miatoll+` (`+`는 Git 기반 로컬 빌드 표기) |
| 버전 Makefile | 공식 v6.18.58과 동일 |
| ARM64 Image | 29,124,616 bytes. ARM64 magic 및 AArch64 ELF 확인 |
| Image 헤더 실행 영역 | 31,588,352 bytes. 전체 Linux RAM 사용량을 의미하지 않음 |
| 모듈 | 211개. `modules.order`와 개수 일치, 모두 AArch64 ELF 및 같은 vermagic 확인 |
| DTB | curtana/joyeuse × Huaxing/Tianma, 4개 생성 |
| DT 정적 검사 | 4개 모두 패널↔DSI endpoint, 터치→패널 연결, QUP 등 부모 활성 상태 통과 |
| Binder UAPI | 4.14와 6.18의 64-bit protocol 8, transaction 64 bytes, write/read 48 bytes와 주요 ioctl 값 일치 |
| 빌드 로그 | 최종 빌드 성공, 오류/경고 없음. 컴파일 중 발견한 API 오류와 터치 경고는 수정 |
| 미수행 | 실기기 부팅/플래시, Android framework/HAL 실행, DT schema 전체 검사, 장기/부하/절전 검증 |

Image SHA256:

`670c97d8abda747e760b5af6bbf649fd970b6462c08e8410b5b9b8753077b18b`

다른 SoC용 pinctrl/클록/interconnect 제외 항목 130개를 6.14.7 설정에서 선별했다.
CPU 수 8, NUMA/Xen/네트워크 파일시스템 제외, 1 MiB 커널 로그 버퍼 등의 설정으로
실행 영역을 최초 약 51.2 MB에서 약 31.6 MB로 줄였다. Android 핵심 인터페이스와
필수 하드웨어는 유지했다. 기존 원본 커널의 실행 영역 기준 40,615,936 bytes보다 작지만,
중간 로더·DTB·ramdisk를 포함한 새 boot.img의 실제 부팅 호환성은 아직 검증하지 않았다.

## 하드웨어별 상태

아래의 '반영'은 새 브랜치의 소스·설정·컴파일 결과다. 모든 행의 새 실기기 검증은 남아 있다.

| 기능 | upstream 6.18 재사용 | 6.14.7에서 반영한 부분 | 남은 확인 |
| --- | --- | --- | --- |
| CPU/RAM/UFS/SD/USB/버튼 | 기존 SM7125/SC7180, PMIC, UFS/MMC/GENI 드라이버 | 보드 DT와 추가 주변장치 연결 | 새 부팅, UFS 읽기, SD CMD48 재발 여부, USB role, 입력 |
| 디스플레이 | DRM/MSM DPU/DSI, PHY, WLED | Huaxing FT8756 및 Tianma NT36675 패널, DT, WLED 수정. DSI API 변환 | 부트로더 화면 인계, 실제 표시/밝기/절전. 이전 로컬 DPU 우회는 포함하지 않음 |
| 터치 | SPI/GENI/input | FT8756 및 NT36xxx SPI 드라이버, 패널 연동과 firmware 이름 | RAM firmware 제공, IRQ/좌표/멀티터치, suspend/resume |
| GPU | Adreno A618/GMU/DRM | ZAP 이름, HWCG, fuse 0x9f/bin 3. OPP는 SM7125에 한정 | firmware, GMU/GPU 초기화, 렌더링/Android GPU userspace |
| 카메라 | CAMSS 공통 코드, OV8856/DW9714 | SC7180 CAMSS/CCI/PHY/DT, S5KGM2/S5K5E9/OV16A1Q/DW9800, 기존 센서/VCM 확장 | ID/전원/스트림/초점/영상 품질. DW9800은 원본도 WIP. joyeuse DT에는 S5K5E9/OV16A1Q만 있고 주카메라 경로가 완성되지 않음 |
| 오디오 | QDSP6/APR, sm8250 machine, TAS2562, WCD937x, SoundWire/LPASS | ADSP 및 스피커/헤드폰/마이크 DT 경로, 드라이버 설정 | ALSA 열거, 스피커 소리, 녹음/마이크/통화, 기존 ACDB/HAL 대응 |
| LTE 모뎀 | MPSS remoteproc, QRTR/QMI, IPA/RMNET | 보드 firmware/메모리/IPA DT, SM7125 PD mapper | MPSS/QMI/SIM/망 등록, 데이터, RIL/IMS/음성 호환성 |
| Wi-Fi/Bluetooth | ath10k SNOC, QCA UART/HCI | 전원/버스/펌웨어 DT | BDF·RFSA/RMTFS 등의 서비스, 연결/전송/공존/주소 처리. 기존 로컬 PMF 패치는 포함하지 않음 |
| 배터리/충전 | ADC5, SPMI SDAM, regulator, Type-C | 실험적 QGauge와 PM6150 DT. 6.18 fwnode API 변환 | QGauge 잔량은 선형 전압 추정이며 STATUS_UNKNOWN. 충전 제어·정확한 SOC·건강 HAL은 미완성. SM5714는 Samsung용이므로 제외 |
| 전력 관리 | RPMh/CPUfreq/thermal/PSCI | 보드 전원 DT와 Android wakelock/autosleep 설정 | 실제 idle/suspend/resume/열 보호/소비 전류/USB 전력 역할 |
| 추가 기능 | Venus/IR SPI | 기존 드라이버 모듈 설정, 보드 DT; AW8695/DRV2624 진동 드라이버 | 영상 가속/IR/진동은 실행 미검증. DRV2624 GPIO API 변환 |

`curtana`와 `joyeuse`의 두 패널 변형이 현재 DTB 빌드 대상이다.
miatoll 전체 명칭만으로 `gram`/`excalibur`의 보드 ID·패널·센서 구성을 지원한다고 가정하지 않는다.

기존 curtana 로컬 빌드에서 확보한 USB/CPU/UFS/화면/터치/Wi-Fi/Bluetooth/ALSA 등록 로그는
원래 작업 공간의 `STATUS.md`와 `reference/device-tests/`에 그대로 남아 있다.
그 성공을 새 6.14 기반 이식 브랜치의 실기기 성공으로 옮겨 적지 않았다.

## 적용 패치와 결정

1. `2f664eee3`: 기존 6.18 A618 구현에 빠진 ZAP/HWCG/fuse bin만 추가.
2. `31aac44d4`: 고정된 6.14.7 포크에서 Xiaomi 하드웨어 파일만 선별 이식하고 14개 충돌 해결.
3. `22e62ea7c`: lineage-22.2의 Android USB state/uevent와 ashmem만 이식.
   두 device-mapper 되돌리기와 GKI defconfig 전체는 제외.
4. `820e88dce`: 6.18 API·전원 오류 정리·설정 의존성·크기·검증 도구를 정리.
   6.18에 이미 있는 CPUfreq/S16_LE 코드와 miatoll에 불필요한 Samsung 오디오 변경은 재사용/제외.

전체 포크 사전 3-way 충돌은 6.14.7 14개 파일, 6.16 10개 파일이었다.
선별 이식에도 14개 파일 충돌이 있었고 수동 해결했다. 직렬 rebase의 최종 충돌 횟수를 뜻하지 않는다.
상세 출처·파일 목록·제외 이유·ABI 비교는 [STRATEGY.ko.md](STRATEGY.ko.md)와 `reports/`를 참고한다.

## 산출물과 재현

기본 산출물 디렉터리: `/data/hwkim/kernel/dist/miatoll-6.18/`.

- `Image`, `.config`, `System.map`, `Module.symvers`, `kernelrelease.txt`
- `dtbs/sm7125-xiaomi-{curtana,joyeuse}-{huaxing,tianma}.dtb`
- `modules/lib/modules/6.18.58-miatoll+/` 및 depmod 결과
- `source-commit.txt`, `source-changes.patch`, `SHA256SUMS`, 빌드 로그/검증 JSON
- `patches/`: 공식 6.18.58 이후 커밋을 내보낸 패치 묶음

묶음 파일: `/data/hwkim/kernel/dist/miatoll-linux-6.18.58-build.tar.gz`.
이는 raw 빌드 산출물 묶음이며 Android boot.img나 firmware/ramdisk 패키지가 아니다.
DT가 참조하는 modem/adsp/cdsp/IPA/Venus/GPU 및 터치/무선 firmware의 공급 경로를 별도로 맞춰야 한다.

```sh
cd /data/hwkim/kernel/miatoll-6.18
JOBS=48 bash miatoll/build.sh
python3 miatoll/check-binder-abi.py
python3 miatoll/check-dtbs.py
python3 miatoll/verify-artifacts.py
```

Clang/LLD 18.1.3과 호스트 도구는 작업 공간의 `tools/`에만 준비했다.
시스템 패키지를 설치/교체하지 않았다. 패키지 출처와 해시는 `reports/toolchain.json`에 기록했다.

## 우선 남은 작업

1. 새 DT/모듈/firmware와 boot header v2·메모리 인계를 통합한 Android 부팅 구성을 준비한다.
2. 별도 허용된 실기기 시험에서 새 기준의 부팅·화면·터치·SD·무선을 재검증한다.
3. 카메라/오디오/모뎀/충전·절전은 기능별로 probe와 실제 동작을 분리해 검증한다.
4. KGSL/ION/vendor IPA ioctl·카메라/오디오·TEE/RIL의 실제 바이너리 의존성을 추적하고
   mainline용 HAL 교체와 호환층의 범위를 결정한다. Binder 검사만으로 해결되지 않는다.
5. 기존 `wrappedkey_v0` userdata의 복호화/키 관리, SELinux/VINTF, framework/앱/통화/IMS와
   장기 안정성까지 확인해야 LineageOS 구동 목표가 완료된다.

원본 작업·모뎀 보정 데이터·파티션은 변경하지 않았고 실기기 플래시/부팅 명령을 실행하지 않았다.
