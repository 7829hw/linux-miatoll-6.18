# Linux 6.18 기반 miatoll 지원 현황

2026-10-27 KST. 하드웨어 이식 기준: **`miatoll/6.18-sm7125`**.
확인된 단독 부팅 브랜치: **`miatoll/6.18-boot1`**.
화면 표시를 실기기로 확인한 브랜치: **`miatoll/6.18-display2`**.
터치 입력을 실기기로 확인한 브랜치: **`miatoll/6.18-touch1`**(display2 기반).
UFS·SD 읽기를 실기기로 확인한 브랜치: **`miatoll/6.18-storage1`**(touch1 기반).
USB-C 역할 전환·host를 실기기로 확인한 브랜치: **`miatoll/6.18-usb2`**(storage1 기반).
Wi-Fi firmware·검색을 실기기로 확인한 브랜치: **`miatoll/6.18-wifi1`**(usb2 기반).
WPA3 연결·IPv4 통신을 실기기로 확인한 브랜치: **`miatoll/6.18-wifi2`**(wifi1과 같은 커널).
Wi-Fi 지연을 개선한 브랜치: **`miatoll/6.18-wifi3`**(wifi2 + ath10k WCN3990 PMF peer 비트 backport).
Bluetooth 초기화·검색을 실기기로 확인한 브랜치: **`miatoll/6.18-bt1`**(wifi3 기반).
배터리 계측을 실기기로 확인한 브랜치: **`miatoll/6.18-battery2`**(battery1 + QG 전류 배율·부호 수정).
셸 명령 Fastboot 재부팅을 실기기로 확인한 브랜치: **`miatoll/6.18-reboot1`**(battery2 + `reboot-mode`).
내장 스피커 재생을 실기기로 확인한 브랜치: **`miatoll/6.18-audio2`**(reboot1 + ADSP 스피커 전용 카드).
전체 오디오 카드·이어폰·내장 마이크를 실기기로 확인한 브랜치: **`miatoll/6.18-audio3`**(q6afe vote 재시도).
유선 헤드셋 감지(삽입·제거)와 이어폰 마이크 녹음을 실기기로 확인한 브랜치: **`miatoll/6.18-audio12`**(TX SoundWire 유지 + 2.7 V MBHC 임계값).
Adreno A618 초기화·명령 실행을 실기기로 확인한 브랜치: **`miatoll/6.18-gpu1`**(audio12 + GPU/GMU, SQE/GMU/zap firmware).
Mesa freedreno GLES 렌더링(kmscube 화면 표시)을 실기기로 확인한 브랜치: **`miatoll/6.18-gpu2`**(gpu1 + Mesa 25.1.9/kmscube RAM 디스크).
Turnip Vulkan 렌더링(셰이더, VK_KHR_display 표시)을 실기기로 확인한 브랜치: **`miatoll/6.18-vulkan1`**(gpu2 + Turnip, Vulkan loader, 점검 도구).
모뎀 MPSS 기동과 읽기 전용 QMI 조회를 실기기로 확인한 브랜치: **`miatoll/6.18-modem1`**(vulkan1 + qmicli, `modem-query`).
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

## wifi2 실기기 결과: WPA3 연결·IPv4 통신 확인

`20261027-032045` 회차에서 사용자가 USB 키보드로 폰 화면에 SSID와 비밀번호를 직접 입력했다.
비밀번호는 serial과 Git에 남지 않는다. 5 GHz WPA3-SAE(group 19)·PMF=2·CCMP 연결, DHCPv4,
공유기와 1.1.1.1 ICMP(손실 0%)를 확인했다. 공유기 왕복 지연은 평균 225 ms로 높다.
RAMdisk에 `/tmp`가 없어 스크립트가 연결 완료를 읽지 못했고, 이를 저장소에서 고쳤다(고친 이미지는 미시험).
지연 개선 후보는 WCN3990 PMF peer 비트 보완이다(이전 bring-up 근거, 이 커널에서는 미검증).
[wifi2 실기기 기록](reports/device-tests/20261027-032045-wifi2/README.ko.md)

## wifi3 실기기 결과: PMF peer 비트 보완 후 지연 개선

`20261027-033718` 회차는 wifi2에 공개 ath-next 제안의 WCN3990 PMF peer 비트 변경 하나만 옮겼다
(병합 여부 미확인, 로컬 backport). 같은 5 GHz AP에서 공유기 RTT 평균이 225 ms(n=5)에서 22.8 ms(절전 on, n=30)로,
절전 off에서는 8.0 ms로 줄었다. 수신 속도는 6 Mbit/s에서 VHT 650 Mbit/s로 올랐다.
고친 `/tmp` RAMdisk로 `wifi-join`이 끝까지 완료됐다. 처리량·2.4 GHz·장시간·공장 MAC은 미검증이다.
[wifi3 실기기 기록](reports/device-tests/20261027-033718-wifi3/README.ko.md)

## bt1 실기기 결과: WCN3991 Bluetooth 초기화·검색 확인

`20261027-034959` 회차는 wifi3에 QUP0/UART3와 Bluetooth 내장, 고정 QCA firmware, btctl rev 4를 더했다.
firmware 초기화가 완료됐지만 공개 주소가 없어 unconfigured였다. 이번 부팅에만 쓰는 임시 진단 주소를 설정한 뒤
전원이 켜졌다. LE 검색(주소 26개)과 BR/EDR 검색(주소 3개)이 성공했다.
공장 주소, 페어링·연결, Wi-Fi 동시 동작은 미검증이다.
[bt1 실기기 기록](reports/device-tests/20261027-034959-bt1/README.ko.md)
같은 이미지로 두 번 Galaxy Buds Pro와 BR/EDR Just Works 페어링(`pairing_complete=1`)과 직후 기본 연결을 확인했다.
프로필이 없어 수 초 뒤 기본 연결은 해제됐다. 같은 부팅에서 A2DP SBC 3초 시험음을 보냈고, 사용자가 이어폰에서 들었다고 확인했다.
[페어링 재확인 기록](reports/device-tests/20261027-035503-bt1-pair-recheck/README.ko.md)

## battery1 실기기 결과: QG 계측과 전류 배율·부호 문제

`20261027-113421` 회차는 bt1에 포크의 읽기 전용 QG 드라이버와 SDAM을 내장했다.
전압·OCV·온도 읽기는 정상이었다. QG SUBTYPE이 0x04(10 A)여서 포크의 고정 5 A 배율로는 전류가 절반으로 보고된다.
USB 분리 시험에서 원시 부호가 충전 음수·방전 양수로 power_supply ABI와 반대임을 확인했다.
충전 제어 드라이버는 없다. 다음 후보 battery2에서 SUBTYPE 기반 배율과 부호를 고친다.
[battery1 실기기 기록](reports/device-tests/20261027-113421-battery1/README.ko.md)

## battery2 실기기 결과: QG 전류 배율·부호 수정 확인

`20261027-114455` 회차는 `qcom_qg`가 SUBTYPE으로 배율을 고르고 ABI 부호로 보고하도록 고친 뒤 같은 분리 시험을 했다.
충전 +144~+167 mA, 배터리 단독 약 −112 mA로 부호와 크기가 예측과 일치했다. 독립 전류계 비교는 없다.
capacity·status 계산과 충전 제어는 아직 포크 수준이다.
[battery2 실기기 기록](reports/device-tests/20261027-114455-battery2/README.ko.md)

## reboot1: USB 셸에서 Fastboot로 재부팅

BusyBox `reboot`는 재부팅 인자를 넘기지 못한다. 그래서 `reboot(RESTART2, "bootloader")`를 호출하는 정적 도구
`reboot-mode`(`fastboot-reboot`)를 추가했다. 커널은 바꾸지 않았다. upstream `qcom-pon` reboot-mode가
PON 재부팅 사유를 downstream과 같은 값(0x2, 7:1비트)으로 쓴다. 실행 중 battery2 세션과 reboot1 이미지에서
Fastboot 복귀를 확인했다. 실행기의 `boot --from-shell`과 `reboot-bootloader`로 버튼 없이 회차를 반복할 수 있다.
[셸 재부팅 확인](reports/device-tests/20261027-120000-battery2-reboot-mode/README.ko.md),
[reboot1 순환 시험](reports/device-tests/20261027-120805-reboot1-from-shell/README.ko.md)

## audio1/audio2: ADSP 오디오와 내장 스피커

audio1(`20261027-121845`)은 포크의 전체 카드를 켰다. ADSP·Q6 APR·TAS2562는 동작했지만 ADSP가
`AFE_CMD_REMOTE_LPASS_CORE_HW_VOTE_REQUEST`를 지원하지 않았다. 그래서 VA macro가 실패하고 WCD937x 경로가 카드 전체를 막았다.
audio2(`20261027-122627`)는 스피커 전용 카드로 `Xiaomi-miatoll` 카드를 등록했다.
수정한 speaker-tone(라우팅 후 PCM 열기, q6asm의 480 frame 단위 period)으로 1 kHz 시험음을 재생했고,
사용자가 내장 스피커에서 들었다. 이어폰·마이크는 미해결이다.
[audio1 기록](reports/device-tests/20261027-121845-audio1/README.ko.md),
[audio2 기록](reports/device-tests/20261027-122627-audio2/README.ko.md)

## audio3: 전체 카드, 이어폰, 내장 마이크

audio1 이미지로 부팅 45초 뒤 VA macro probe만 다시 시도하자 전체 카드가 올라왔다. 이로써 vote가 초기에만 거부된다는 것을 확인했다.
audio3(`20261027-125236`)는 q6afe가 거부 응답을 바로 전달하고 100 ms 간격으로 재시도하도록 고쳤다.
부팅 중 1회 재시도로 전체 카드가 자동 등록됐다. sm7125-mainline miatoll UCM 순서로 유선 이어폰 출력을
사용자가 양쪽 귀에서 들었다. 하단·상단 내장 마이크는 말할 때 RMS가 약 25 dB 올라 음성 녹음을 확인했다.
이어폰 마이크는 MBHC 인식·바이어스가 켜지는데도 신호가 없어 미해결이다.
[vote 재시도 실험](reports/device-tests/20261027-124318-audio1-vote-retry/README.ko.md),
[audio3 기록](reports/device-tests/20261027-125236-audio3/README.ko.md)

## audio4–audio12: 유선 헤드셋 감지와 이어폰 마이크

- 마이크 바이어스: curtana Android DT의 2.7 V를 썼다(audio5).
  - audio4에서 downstream `swh` 값을 upstream normally-closed 속성으로 옮기면 감지가 깨진다는 것을 확인했다.
- 경로 확인(audio6): 버스를 셸에서 active로 고정하자 헤드셋이 감지됐다.
  - Android amic2 경로(ADC2 INP2, DEC0_BCS)로 말소리가 침묵보다 10–20 dB 높게 녹음됐다.
- 원인 1 — clock stop 중 알림 유실:
  - WCD937x MBHC 인터럽트는 TX SoundWire Slave 알림으로 들어온다. TX 버스가 clock stop에 들어가면 이 알림이 CPU에 오지 않았다.
  - 다음은 모두 효과가 없었다: downstream wake IRQ(SPI 555)를 GIC 직결(audio6)이나 PDC 핀 75(audio7)로 연결, Slave WakeUpEnable(audio8), LPASS macro 유지.
  - audio9: `wcd937x_codec_set_jack()`이 jack을 등록한 동안 TX Slave의 runtime PM 참조를 잡아 해결했다. downstream TX master의 always-on과 같은 취지다. 유휴 전력 비용은 아직 측정하지 않았다.
- 원인 2 — 임계값 오판(audio10 진단 로그로 확인):
  - 2.7 V 바이어스에서 헤드셋 마이크선은 1.76–2.06 V로 읽힌다. 공통 DT의 1.8 V 기준 임계값 1.7 V와 비교돼 LINEOUT(연장 케이블)으로 오판됐고, Jack Off였다.
  - audio11: DT 임계값을 2.7 V 기준(헤드셋 2550000 µV, 헤드폰 75000 µV)으로 바꿨다. downstream이 기본값을 바이어스 비율로 환산하는 방식과 같다.
- audio11/audio12 실기기 결과:
  - 꽂은 채 부팅, 제거, 재삽입 모두 HEADSET으로 보고됐다(z ≈ 48–50 Ω). Headphone/Mic Jack 상태가 따라 바뀌었다.
  - 정상 runtime PM 경로에서 이어폰 마이크 말소리 RMS가 침묵보다 최대 약 20 dB 높았다.
  - 삽입 직후 일시적인 `cross connection` 로그가 나오지만 3초 보정 뒤 헤드셋으로 정정된다.
- 이어폰 3버튼(audio12·audio13): `event4 "Xiaomi-miatoll Headset Jack"`에서 확인했다.
  - 짧게 누름: 가운데 KEY_MEDIA, 볼륨 + KEY_VOLUMEUP, 볼륨 − KEY_VOLUMEDOWN이 각 5/5였다.
  - 길게 누름도 down/up이 정상이었다.
  - 볼륨 −는 225–400 mV 구간으로 측정돼 audio12 임계값 안에 있다.
- 이어폰 마이크 녹음 청취: 10초 녹음을 PC로 옮겨 사용자가 들었고, 숫자 세는 소리가 또렷하다고 확인했다(audio13).
- 유휴 전력(QG 계측, 화면 blank, 이어폰 제거, USB 분리):
  - TX 유지 없음(audio14) −37.7 mA, 같은 부팅에서 TX active −37.2 mA, audio12 −38.8 mA.
  - TX SoundWire 유지 비용은 측정 분해능(약 1–2 mA) 안이다.
  - 오디오 시험을 오래 한 audio13 세션에서 한 번 −94.5 mA가 나왔지만 재현되지 않았고, 원인은 미확인이다.
- 미검증: system suspend 중 감지·전력, 외부 계측기 검증.
- audio13 첫 RAM 부팅은 Linux 시리얼 없이 Android로 넘어갔고, 재부팅 후 같은 이미지가 정상 부팅됐다. 원인은 미확인이다.
- 기록: [audio6](reports/device-tests/20261027-135906-audio6/README.ko.md), [audio7](reports/device-tests/20261027-141835-audio7-audio7/README.ko.md),
  [audio8](reports/device-tests/20261027-143024-audio8-audio8/README.ko.md), [audio9](reports/device-tests/20261027-144600-audio9-audio9/README.ko.md),
  [audio10](reports/device-tests/20261027-182529-audio10-audio10/README.ko.md), [audio11](reports/device-tests/20261027-183513-audio11-audio11/README.ko.md),
  [audio12](reports/device-tests/20261027-190614-audio12-audio12/README.ko.md), [audio13](reports/device-tests/20261027-192323-audio13-audio13-retry/README.ko.md)

## gpu1: Adreno A618

audio12 위에 GPU·GMU를 켜고 a630_sqe.fw·a630_gmu.bin(Alpine linux-firmware-qcom 20250509-r0)과 curtana a615_zap.mbn(firmware-xiaomi-miatoll a7073ad1)을 넣었다.
- GPU 6.1.8.0, speed bin 3(180–750 MHz)으로 동작했다. zap 로드는 오류 없이 성공했다.
- 정적 `gpu-probe`가 3D 파이프에 `CP_MEM_WRITE`를 제출해 결과값이 일치했다(연속 30/30, runtime suspend 뒤 재개 10/10, faults 0).
- 화면 표시는 정상이었다(사용자 관찰).
[gpu1 기록](reports/device-tests/20261027-204103-gpu1-gpu1/README.ko.md)

gpu2: Mesa 25.1.9를 freedreno만으로 교차 빌드했다(EGL/GBM/GLES2, LLVM·X11 없음, 고정 입력, Alpine v3.22 sysroot). kmscube와 함께 RAM 디스크에 넣었다.
- `FD618`, `OpenGL ES 3.2 Mesa 25.1.9`로 오프스크린 1080×2400 약 890 fps를 기록했다.
- 화면 KMS로 60.0 fps 회전 입방체를 렌더링했고, 사용자가 화면에서 확인했다. 종료 뒤 콘솔로 복귀했다.
- fault/hang은 없었다.
[gpu2 기록](reports/device-tests/20261027-211715-gpu2-gpu2/README.ko.md)

vulkan1: 같은 Mesa 25.1.9를 Turnip 포함으로 다시 빌드했고, Alpine Vulkan loader 1.4.313을 넣었다.
- `vulkaninfo`는 `Turnip Adreno (TM) 618`, Vulkan 1.3.311을 보고했다.
- Alpine `vkcube --wsi display`는 GPU 선택 직후 segfault했다.
- 자체 점검 도구로 확인한 것:
  - `vkCmdFillBuffer` 정확.
  - VK_KHR_display로 색 전환 화면 60 fps.
  - GLSL→SPIR-V 삼각형 오프스크린 픽셀 검증 통과, 화면 회전 삼각형 60 fps.
- 사용자가 화면으로 확인했고, fault는 없었다.
[vulkan1 셰이더 기록](reports/device-tests/20261027-230340-vulkan1-vulkan1-shader/README.ko.md)

## modem1: MPSS와 읽기 전용 QMI

qmicli(libqmi 1.36.0, QRTR)와 읽기 전용 래퍼 `modem-query`(식별자·위치 가림)를 넣었다. Alpine main/community 인덱스 서명을 확인했다.
- MPSS는 RAM-shadow rmtfs로 기동해 QRTR에 DMS/NAS/WDS/UIM/Voice/WMS/IPA 등 서비스를 노출했다.
- 펌웨어 `MPSS.AT.4.4.c6-00071-RENNELL_GEN_PACK-3`, GSM/UMTS/LTE.
- SIM 없음: UIM `no-atr-received`, NAS `not-registered-searching`, 수신 IO -106 dBm.
- 운영 모드가 `shutting-down`으로 보고된다(원인 미확인, 모드 변경은 보내지 않았다).
- 망 등록·데이터·통화·SMS는 미시험이다.
[modem1 기록](reports/device-tests/20261027-232006-modem1-modem1/README.ko.md)

## 하드웨어별 상태

아래의 '반영'은 새 브랜치의 소스·설정·컴파일 결과다. boot1에서 확인한 기본 기능 외의
실기기 검증은 남아 있다.

| 기능 | upstream 6.18 재사용 | 6.14.7에서 반영한 부분 | 남은 확인 |
| --- | --- | --- | --- |
| CPU/RAM/UFS/SD/USB/버튼 | 기존 SM7125/SC7180, PMIC, UFS/MMC/GENI/QUSB2 드라이버 | 보드 DT와 추가 주변장치 연결 | boot1에서 CPU/RAM/USB ACM/UFS 열거 확인. storage1에서 UFS·SD(SDR104 포함) read-only 블록 읽기 확인, SH64G 카드는 CMD48 단계 실패(카드 고유). usb2에서 Type-C 역할 전환·USB host(저장장치·HID) 확인. 쓰기/마운트, 충전/PD, 버튼 입력은 미검증 |
| 디스플레이 | DRM/MSM DPU/DSI, PHY, WLED, 표준 MDSS reset | Huaxing FT8756 및 Tianma NT36675 패널, DT, WLED 수정. DSI API 변환 | display2(Huaxing)에서 VT 표시·색상, WLED 밝기 0–4095, blank/unblank 3회, 2분 유지를 실기기 확인. 절전, 장시간, Tianma 패널은 미검증 |
| 터치 | SPI/GENI/input | FT8756 및 NT36xxx SPI 드라이버, 패널 연동과 firmware 이름 | touch1(Huaxing FT8756)에서 RAM firmware·IRQ·좌표·5점 멀티터치 실기기 확인. suspend/blank 중 처리, Tianma NT36xxx 미검증 |
| GPU | Adreno A618/GMU/DRM | ZAP 이름, HWCG, fuse 0x9f/bin 3. OPP는 SM7125에 한정. gpu1에서 GPU/GMU 활성화와 firmware 공급 | gpu1에서 GMU 전원·SQE/GMU firmware·zap 로드, `CP_MEM_WRITE` 제출 실행(연속 30/30, 재개 10/10), devfreq 180–750 MHz, runtime suspend 실기기 확인. gpu2에서 Mesa 25.1.9 freedreno(FD618, GLES 3.2)로 kmscube 오프스크린 약 890 fps, 화면 60 fps 렌더링 실기기 확인(사용자 관찰). vulkan1에서 Turnip(Vulkan 1.3.311) 전송 명령·셰이더 렌더링(오프스크린 픽셀 검증, 화면 60 fps) 실기기 확인(사용자 관찰). 장시간 부하 DVFS·발열, GLES/Vulkan 적합성 테스트, Android GPU userspace(KGSL ABI) 미검증 |
| 카메라 | CAMSS 공통 코드, OV8856/DW9714 | SC7180 CAMSS/CCI/PHY/DT, S5KGM2/S5K5E9/OV16A1Q/DW9800, 기존 센서/VCM 확장 | ID/전원/스트림/초점/영상 품질. DW9800은 원본도 WIP. joyeuse DT에는 S5K5E9/OV16A1Q만 있고 주카메라 경로가 완성되지 않음 |
| 오디오 | QDSP6/APR, sm8250 machine, TAS2562, WCD937x, SoundWire/LPASS | ADSP 및 스피커/헤드폰/마이크 DT 경로, 드라이버 설정. q6afe LPASS HW vote 재시도(audio3), WCD937x jack 등록 중 TX Slave 유지(audio9), 2.7 V MBHC 임계값 DT(audio11) | 스피커·유선 이어폰 출력 청취, 내장 마이크 2개 녹음, 헤드셋 삽입·제거 감지, 이어폰 마이크 녹음, 이어폰 3버튼(audio12/13), TX 유지 유휴 전력 영향(audio14 비교, 측정 오차 안) 실기기 확인. 통화, 음량 곡선, ACDB/HAL 대응 미검증 |
| LTE 모뎀 | MPSS remoteproc, QRTR/QMI, IPA/RMNET | 보드 firmware/메모리/IPA DT, SM7125 PD mapper | MPSS/QMI/SIM/망 등록, 데이터, RIL/IMS/음성 호환성 |
| Wi-Fi/Bluetooth | ath10k SNOC, QCA UART/HCI | 전원/버스/펌웨어 DT | wifi1에서 MPSS·WLAN firmware·wlan0·수동 검색, wifi2에서 WPA3-SAE 연결·DHCPv4·ICMP, wifi3에서 PMF peer 비트 backport 후 지연 개선(평균 23 ms) 실기기 확인(read-only rmtfs, 기기 BDF). bt1에서 Bluetooth firmware·임시 주소 전원·LE/BR 검색 확인. Galaxy Buds Pro 페어링과 A2DP SBC 시험음 청취 확인. 공장 MAC/BD 주소, 처리량, 공존, 장시간 오디오·통화 미검증. PMF 패치는 wifi3 브랜치에만 포함 |
| 배터리/충전 | ADC5, SPMI SDAM, regulator, Type-C | 실험적 QGauge와 PM6150 DT. 6.18 fwnode API 변환. QG SUBTYPE 배율·ABI 부호 수정(battery2) | battery2에서 전압·OCV·온도·충전/방전 전류 부호와 크기 실기기 확인. 잔량은 선형 전압 추정이며 STATUS_UNKNOWN. 충전 제어·정확한 SOC·건강 HAL은 미완성. SM5714는 Samsung용이므로 제외 |
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

1. display2 화면, touch1 터치, storage1 UFS/SD 읽기, usb2 USB 역할 전환·host, wifi1–3 Wi-Fi와 bt1 Bluetooth 검색은 확인했다. 다음 단계는 BT 페어링·공존, GPU·오디오·충전이며,
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
