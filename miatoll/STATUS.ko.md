# Linux 6.18 기반 miatoll 지원 현황

2026-10-27 KST. 하드웨어 이식 기준: **`miatoll/6.18-sm7125`**.
확인된 단독 부팅 브랜치: **`miatoll/6.18-boot1`**.
화면 표시를 실기기로 확인한 브랜치: **`miatoll/6.18-display2`**.
터치 입력을 실기기로 확인한 브랜치: **`miatoll/6.18-touch1`**(display2 기반).
UFS·SD 읽기를 실기기로 확인한 브랜치: **`miatoll/6.18-storage1`**(touch1 기반).
USB-C 역할 전환·host를 실기기로 확인한 브랜치: **`miatoll/6.18-usb2`**(storage1 기반).
Wi-Fi firmware·검색을 실기기로 확인한 브랜치: **`miatoll/6.18-wifi1`**(usb2 기반).
공식 Linux **v6.18.58**을 기반으로, 6.14.7 포크의 Xiaomi 하드웨어 구현을 직접 선별 이식했다.
기존 로컬 커널 수정은 보존 브랜치와 백업에 남겼다.

**curtana에서 새 6.18.58 커널의 단독 RAM 부팅과 USB 진단 셸 진입을 실기기로 확인했다.**
아래 boot1 최소 프로필의 결과이며, 전체 하드웨어와 LineageOS 부팅은 미검증이다.

## 기본 하드웨어 빌드의 호스트 검증

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
| 미수행 | 이 전체 하드웨어 프로필의 실기기 부팅, Android framework/HAL 실행, DT schema 전체 검사, 장기/부하/절전 검증. 플래시는 수행하지 않음 |

Image SHA256:

`670c97d8abda747e760b5af6bbf649fd970b6462c08e8410b5b9b8753077b18b`

다른 SoC용 pinctrl/클록/interconnect 제외 항목 130개를 6.14.7 설정에서 선별했다.
CPU 수 8, NUMA/Xen/네트워크 파일시스템 제외, 1 MiB 커널 로그 버퍼 등의 설정으로
실행 영역을 최초 약 51.2 MB에서 약 31.6 MB로 줄였다. Android 핵심 인터페이스와
필수 하드웨어는 유지했다. 기존 원본 커널의 실행 영역 기준 40,615,936 bytes보다 작다.
이 기본 빌드와 아래 실기기 시험 빌드는 구분한다. boot1에서는 QUSB2 PHY를 내장하고
주변장치를 제한한 DT·RAM initramfs·중간 로더를 통합해 실제 부팅을 확인했다.

## curtana 단독 RAM 부팅: 실기기 확인

Windows PC에 연결된 기존 curtana에서 사용자가 실행하고 전달한
`20261026-232305` Fastboot/serial 로그를 검토했다.
원본과 해시·판정 근거는 [실기기 기록](reports/device-tests/20261026-232305-boot1/README.ko.md)에 있다.
후속 `20261026-233342` serial 로그에서 BusyBox dmesg 수집까지 확인했다.
[상세 커널 로그 분석](reports/device-tests/20261026-233342-boot1-kernel-log/README.ko.md)에 원본·분류·코드 근거를 보존했다.

| 확인 항목 | 로그에서 확인한 내용 |
| --- | --- |
| 실제 커널/프로필 | `6.18.58-miatoll-boot1+`, `boot1-ram-only` |
| RAM 사용자 공간 | 대화형 셸에서 `uname -r`와 `boot-probe` 실행, `BOOT1_PROBE_END` 도달 |
| CPU/RAM | CPU `0-7` online, MemTotal `5,643,080 kB` |
| USB | ACM gadget이 `a600000.usb`에 연결되고 상태 `configured`; Windows와 명령/응답 교환 |
| UFS | `sda`–`sdf` 및 파티션 열거, 6개 디스크 모두 read-only=1. 파일 읽기/성능 검증은 아님 |
| 마운트/모듈 | RAM·가상 파일시스템만 마운트, 로드된 모듈 없음 |
| 관측 시간 | 최초 probe uptime 3.34초, 후속 캡처 uptime 486.86초에서 셸 응답. 장기 안정성/부하/절전 검증은 아님 |
| 커널 상세 로그 | 후속 BusyBox dmesg 종료 코드 0. 커널 시작 메시지부터 458개 메시지 수집; 수집 범위에 panic/Oops/커널 WARN 스택 없음 |
| `/init` 실행 | 커널 시작 후 0.472615초. 전원 인가부터의 전체 시간은 아님 |

시험 boot.img SHA256:
`ca100f9ebb5cba93608ff755e79ec2e9f7ffcc34e024eba8b5100671e3c9ff75`.
Fastboot의 `Booting OKAY`와 별도로 실제 USB 셸의 버전·프로필·probe 완료를 확인했다.
패키지 생성 당시 `boot1-host-validation.json`의 `device_boot_confirmed=false`는
과거 호스트 검증 기록으로 유지하며, 이후 실기기 판정은 위 기록의 `result.json`에 있다.

디스플레이/터치/GPU/카메라/오디오/모뎀/무선/충전·절전과 Android는 이번 시험 대상이 아니다.
화면 출력은 serial 로그만으로 검증할 수 없다. 모뎀·ADSP·GPU 등은 시험 DT에서 비활성화했다.
RAMdisk 생성기에 `dmesg` 링크를 추가하고 캡처 스크립트가 BusyBox applet을 직접 호출하도록
수정했다. 시험에 사용한 기존 이미지/ZIP은 결과 추적을 위해 그대로 보존했다.

상세 로그의 PSCI PC mode 전환 경고 뒤 OSI topology 초기화는 성공했다. 실제 절전은 미검증이다.
`sync_state()` 대기 8건은 드라이버가 꺼진 BWMON 두 노드와 모듈을 공급하지 않은 Venus
노드가 최소 DT에 남은 것과 대응한다. 후속 시험에서 해당 consumer 구성을 정리해야 한다.
`regulatory.db` 누락은 firmware 없는 구성과 대응하며, UFS 공급 전원 두 항목은
드라이버가 이미 켜진 것으로 가정하고 열거를 계속한다. 임의 전원 배선 패치는 적용하지 않았다.
또한 ICE의 raw key 전용 경로와 QSEE allowlist 제외가 실기기에서도 확인돼, 기존
`wrappedkey_v0` 데이터·TEE 서비스와의 Android 호환성은 계속 미해결이다.

## display1 실기기 결과와 다음 display2 후보

사용자가 boot1에서 **화면이 검고 백라이트만 켜짐**을 보고했다. boot1의 MDSS/DSI/WLED는
비활성 상태였으며 native framebuffer 등록도 없었다. 화면 표시 성공으로 기록하지 않는다.
새 `sm7125-xiaomi-curtana-display1.dts`는 boot1에서 화면 경로만 켜고 WLED 기본 밝기 256,
불필요한 BWMON/Venus 비활성화를 지정한다. 터치는 계속 비활성화한다.
커널/패널 C 코드는 현재 6.18+6.14 선별 이식 그대로이며, 별도 실행 버전은
`6.18.58-miatoll-display1+`다. 시험 문구를 VT에 쓰고 DRM/DSI/fb/WLED/IRQ/dmesg를 수집한다.
`20261027-000237` 첨부 로그에서 새 커널 부팅·USB 셸·probe 완료와 msmdrmfb/1080×2400
모드 등록은 확인했다. **실제 화면 출력은 실패했고 사용자는 백라이트도 꺼졌다고 보고했다.**
SID 0x800이 부트로더 화면 버퍼 0x9c000000 영역에 접근하며 SMMU fault가 발생했고,
관련 IRQ는 probe 시점에 7,796회였다. pixel RCG WARN 및 `FBINFO_VIRTFB` 누락 경고도 있다.
밝기 읽기값 256은 실제 광량이 아니다. 원본과 해석은
[display1 실기기 기록](reports/device-tests/20261027-000237-display1/README.ko.md)에 있다.
실행 절차와 범위는 [DISPLAY1.ko.md](boot/DISPLAY1.ko.md)를 참고한다.
Image/DTB와 211개 모듈 빌드, 내장 의존성·DT graph·ARM64 로더·RAMdisk·AVB·재추출 및
Windows ZIP의 CRC/파일 해시 검사는 통과했다. 로더 포함 실행 영역은 33,550,336 bytes다.
정확한 이미지/ZIP 해시와 소스 커밋은 [호스트 검증 기록](reports/display1-host-validation.json)에 있다.

첨부 Fastboot 로그는 bootloader 재시작 1회 뒤 `fastboot boot` 1회이며 flash/erase 명령은 없다.
이는 시험 전 세션 갱신과 RAM 전송이다. 로그 수집 이후의 추가 자동 재부팅 여부는 판단하지 않는다.

다음 후보 `6.18.58-miatoll-display2+`는 별도 DT에 MDSS_CORE reset을 연결해 기존
upstream `msm_mdss_reset()`을 사용한다. framebuffer 시스템 RAM에는 `FBINFO_VIRTFB`를
지정하고 VT 표시 전 표준 `blank=0` unblank를 한 번 요청한다. DPU/MDSS·클록·WLED
드라이버와 IOMMU 보호는 display1 기준을 유지한다. 실행 절차는 [DISPLAY2.ko.md](boot/DISPLAY2.ko.md)에 있다.

## display2 실기기 결과: 화면 표시 확인

2026-10-27 `20261027-015228` 회차(WSL 실행기, `fastboot boot` 1회)에서 사용자가
**시험 문구와 RED/GREEN/BLUE 색상 표시, 백라이트 켜짐**을 직접 확인했다.
같은 로그에서 SMMU context fault 0회(display1: IRQ 7,796회), pixel RCG WARN·`FBINFO_VIRTFB`
경고·커널 WARNING 0건, fb0 `blank=0`이다. 세 변경은 함께 시험해 개별 기여는 분리하지 않았다.
확인 범위는 부팅 직후 정지 화면 1회이며 밝기 조절·blank 반복·장시간·절전·Tianma 패널은 미검증이다.
[display2 실기기 기록](reports/device-tests/20261027-015228-display2/README.ko.md)

이어진 display3 시험(`20261027-015644`, 같은 display2 이미지, 커널 수정 없음)에서
WLED 밝기 4095/200/0 반복, `fb0/blank` 4↔0 3회(CRTC·DSI·패널 재활성화), 2분 연속 갱신을
사용자가 모두 확인했다. 그동안 SMMU/WLED fault IRQ는 0이었고 MDSS IRQ는 약 60/s였다.
suspend/resume, 장시간 표시, Tianma 패널은 미검증이다.
[display3 시험 기록](reports/device-tests/20261027-015644-display2-display3-cycle/README.ko.md)

## touch1 실기기 결과: FT8756 터치 입력 확인

`20261027-021331` 회차에서 display2 DT에 QUP1·GPI DMA1·SPI11만 추가 활성화하고,
고정한 Huaxing RAM firmware(`sm7125-mainline/firmware-xiaomi-miatoll` blob `e4fb163b`)를 RAMdisk로 공급했다.
6.14.7 포크 FT8756 드라이버를 수정 없이 사용했다. SPI bind, firmware 전송·ECC·앱 시작이 확인됐다.
evdev 원본에서 x 30–1071, y 0–2396 좌표, 최대 5개 동시 접촉, 모서리 탭과 드래그를 확인했다.
사용자도 실제 동작과 로그가 일치하고 화면이 정상임을 확인했다.
앱 시작 직후 1회의 읽기 실패(status 0xC3)와 창 끝의 미해제 접촉 2개는 원인을 확정하지 않았다.
suspend/blank 중 터치 전원 처리와 Tianma 터치는 미검증이다.
[touch1 실기기 기록](reports/device-tests/20261027-021331-touch1/README.ko.md)

## storage1 실기기 결과: UFS·SD 읽기 전용 확인

`20261027-022708` 회차는 touch1 DT에 SD 컨트롤러만 포크 설정 그대로 추가했다.
모든 블록 장치를 read-only로 설정한 뒤 마운트 없이 읽었다.
UFS `super` 64 MiB를 2회 읽어 해시가 일치했다(110–140 MB/s).
SD는 아카이브의 `SH64G` CMD48(ext reg) -110 초기화 실패가 upstream mmc core 그대로 재현됐다.
사용자가 실행 중 카드를 교체했다. CMD48 미지원 SU08G는 legacy 25 MHz로,
CMD48 지원 SM32G는 UHS-I SDR104 202 MHz/1.8 V로 정상 초기화됐다. 두 카드 모두 반복 읽기 해시가 일치했다.
따라서 호스트 CMD48 경로는 동작하며 SH64G 실패는 카드 고유 문제로 판단한다.
아카이브의 로컬 SD 우회는 이식하지 않았다. 쓰기·마운트·절전 중 카드 처리는 미검증이다.
[storage1 실기기 기록](reports/device-tests/20261027-022708-storage1/README.ko.md)

## usb2 실기기 결과: USB-C 역할 전환·host 확인

`20261027-025327` 회차는 boot1의 peripheral 전용 설정을 되돌렸다. PM6150 Type-C·VBUS·DWC3 role switch를
포크 공통 DT 그대로 쓰고, Type-C/VBUS 드라이버 내장과 dual-role DWC3를 사용했다.
PC(USB-A 케이블)에서는 기본 device 역할로 ACM이 동작했다. OTG 연결 시 host로 전환됐고,
64 GB USB 메모리를 read-only로 16 MiB 2회 읽어 해시가 일치했다. HID 키보드 입력도 사용자가 화면에서 확인했다.
분리 후 device 역할과 ACM이 자동 복귀했다.
첫 시도는 fastboot 전송이 120초 정지해 중단했고, 사용자 승인 후 1회 재시도했다(USB/IP 정지 추정).
충전/PD, USB-C DRP 상대, 절전은 미검증이다.
[usb2 실기기 기록](reports/device-tests/20261027-025327-usb2-retry/README.ko.md)

## wifi1 실기기 결과: MPSS·WCN3990·수동 검색 확인

`20261027-030830` 회차는 usb2에 MPSS·WLAN 노드와 ath10k 내장을 더했다.
아카이브에서 검증한 고정 firmware·정적 도구·스크립트를 해시로 확인해 사용했다.
사용자 허가에 따라 rmtfs는 EFS 파티션을 read-only로 열고 NV 쓰기는 RAM shadow에만 반영했다.
`modem` 파티션은 read-only로 잠시 마운트해 `bdwlan.bin`만 RAM에 복사했다.
MPSS running(fatal 0), WLAN.HL.3.2.2 firmware, `wlan0`, 45초 수동 검색으로 BSS 7개(2.4/5 GHz)를 확인했다.
공장 MAC은 제공하지 않아 임의 MAC이 쓰였다. AP 연결·IP 통신·절전은 미검증이다.
[wifi1 실기기 기록](reports/device-tests/20261027-030830-wifi1/README.ko.md)

## 하드웨어별 상태

아래의 '반영'은 새 브랜치의 소스·설정·컴파일 결과다. boot1에서 확인한 기본 기능 외의
실기기 검증은 남아 있다.

| 기능 | upstream 6.18 재사용 | 6.14.7에서 반영한 부분 | 남은 확인 |
| --- | --- | --- | --- |
| CPU/RAM/UFS/SD/USB/버튼 | 기존 SM7125/SC7180, PMIC, UFS/MMC/GENI/QUSB2 드라이버 | 보드 DT와 추가 주변장치 연결 | boot1에서 CPU/RAM/USB ACM/UFS 열거 확인. storage1에서 UFS·SD(SDR104 포함) read-only 블록 읽기 확인, SH64G 카드는 CMD48 단계 실패(카드 고유). usb2에서 Type-C 역할 전환·USB host(저장장치·HID) 확인. 쓰기/마운트, 충전/PD, 버튼 입력은 미검증 |
| 디스플레이 | DRM/MSM DPU/DSI, PHY, WLED, 표준 MDSS reset | Huaxing FT8756 및 Tianma NT36675 패널, DT, WLED 수정. DSI API 변환 | display2(Huaxing)에서 VT 표시·색상, WLED 밝기 0–4095, blank/unblank 3회, 2분 유지를 실기기 확인. 절전, 장시간, Tianma 패널은 미검증 |
| 터치 | SPI/GENI/input | FT8756 및 NT36xxx SPI 드라이버, 패널 연동과 firmware 이름 | touch1(Huaxing FT8756)에서 RAM firmware·IRQ·좌표·5점 멀티터치 실기기 확인. suspend/blank 중 처리, Tianma NT36xxx 미검증 |
| GPU | Adreno A618/GMU/DRM | ZAP 이름, HWCG, fuse 0x9f/bin 3. OPP는 SM7125에 한정 | firmware, GMU/GPU 초기화, 렌더링/Android GPU userspace |
| 카메라 | CAMSS 공통 코드, OV8856/DW9714 | SC7180 CAMSS/CCI/PHY/DT, S5KGM2/S5K5E9/OV16A1Q/DW9800, 기존 센서/VCM 확장 | ID/전원/스트림/초점/영상 품질. DW9800은 원본도 WIP. joyeuse DT에는 S5K5E9/OV16A1Q만 있고 주카메라 경로가 완성되지 않음 |
| 오디오 | QDSP6/APR, sm8250 machine, TAS2562, WCD937x, SoundWire/LPASS | ADSP 및 스피커/헤드폰/마이크 DT 경로, 드라이버 설정 | ALSA 열거, 스피커 소리, 녹음/마이크/통화, 기존 ACDB/HAL 대응 |
| LTE 모뎀 | MPSS remoteproc, QRTR/QMI, IPA/RMNET | 보드 firmware/메모리/IPA DT, SM7125 PD mapper | MPSS/QMI/SIM/망 등록, 데이터, RIL/IMS/음성 호환성 |
| Wi-Fi/Bluetooth | ath10k SNOC, QCA UART/HCI | 전원/버스/펌웨어 DT | wifi1에서 MPSS·WLAN firmware·wlan0·수동 검색 실기기 확인(read-only rmtfs, 기기 BDF). 연결/전송/공존/공장 MAC, Bluetooth 미검증. 기존 로컬 PMF 패치는 포함하지 않음 |
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
2026-10-27 WSL(Ubuntu 26.04) 작업 공간에서는 복사된 LLVM에 빠진 `libllvm18`, `libclang-cpp18`
(18.1.3-1ubuntu1)과 noble `libxml2` 2.9.14, `libicu74`를 Ubuntu 인덱스 SHA256 확인 후
`tools/llvm18`에만 풀고, 로컬 `patchelf`로 두 보조 라이브러리에 `$ORIGIN` runpath를 지정했다.
실기기 USB는 usbipd-win 5.3.0과 `boot/wsl/51-curtana-ramtest.rules`로 WSL에 연결한다.

## 우선 남은 작업

1. display2 화면, touch1 터치, storage1 UFS/SD 읽기, usb2 USB 역할 전환·host, wifi1 Wi-Fi 검색은 확인했다. 다음 단계는 Wi-Fi 연결·BT·GPU·오디오·충전이며,
   반복 부팅·부하·idle/suspend/resume와 장시간 표시는 별도로 검증한다. BWMON/Venus는 화면 시험 DT에서 비활성화했다.
2. 화면·터치·SD·무선을 기능별 RAM 시험으로 재검증한다. 새 DT/모듈/firmware와
   boot header v2·메모리 인계를 Android 부팅 구성에도 연결한다.
3. 카메라/오디오/모뎀/충전·절전은 기능별로 probe와 실제 동작을 분리해 검증한다.
4. KGSL/ION/vendor IPA ioctl·카메라/오디오·TEE/RIL의 실제 바이너리 의존성을 추적하고
   mainline용 HAL 교체와 호환층의 범위를 결정한다. Binder 검사만으로 해결되지 않는다.
5. 기존 `wrappedkey_v0` userdata의 복호화/키 관리, SELinux/VINTF, framework/앱/통화/IMS와
   장기 안정성까지 확인해야 LineageOS 구동 목표가 완료된다.

원본 작업은 보존했다. 사용자에게 허용된 `fastboot boot` RAM 시험만 수행했으며,
전달된 로그에 플래시/파티션 마운트 명령은 없고 UFS 디스크는 read-only=1이다.
모뎀 보정 데이터 변경이나 파티션 쓰기 작업은 수행하지 않았다.
