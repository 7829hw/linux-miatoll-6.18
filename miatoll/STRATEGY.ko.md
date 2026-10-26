# miatoll Linux 6.18 LTS 개발 전략

기준일: 2026-10-26 KST. 이후 개발은 `/data/hwkim/kernel/miatoll-6.18`의
`miatoll/6.18-sm7125`와 그 기반 기능 브랜치에서 진행한다.
현재 단독 RAM 부팅 시험은 `miatoll/6.18-boot1`에서 진행한다.
단독 부팅 확인 이후의 화면 RAM 시험은 그 위의 `miatoll/6.18-display1`에서 진행한다.
display1의 실제 화면 실패 로그를 보존하고 수정 후보는 `miatoll/6.18-display2`에서 진행한다.

## 기준과 보존

최종 커널 기반은 공식 Linux 6.18 LTS다. 이번 작업은 공식 stable Git 태그
`v6.18.58`의 커밋 `2926d88bb7fc4608fd942453d929c39e4e5ec006`에서 시작했다.
버전 Makefile의 숫자를 바꾸는 방식은 사용하지 않았다. 6.18은
[kernel.org의 LTS 목록](https://www.kernel.org/category/releases.html)에 포함된다.

기존 작업 공간은 Git 저장소가 아니었다. 변경 전에 전체를 다음 위치에 독립 복사했다.

`/data/hwkim/kernel/backups/pre-sm7125-strategy-20261026-210144/workspace`

`verification.json`에 일반 파일 130,895개, 14,633,214,123 bytes의 SHA256 대조 성공을
기록했다. `manifest.jsonl`에는 파일별 해시와 심볼릭 링크가 있다. 기존 소스·패치·도구·
사용자 공간 코드·로그·펌웨어·산출물을 보존했고 원래 `linux-6.18` 트리를 수정하지 않았다.

새 Git 저장소의 보존 이력:

| 브랜치 | 용도 |
| --- | --- |
| `archive/curtana-6.18-20261026` | 공식 v6.18 위에 기존 커널 수정과 개발 기록을 보존한 `43873884c813aba83020e5dca8d72220d775ef02` |
| `miatoll/6.18-lts` | 기존 로컬 수정을 6.18.58에 이어 붙여 본 이전 이식 시도. 보존만 한다 |
| `miatoll/6.18-sm7125` | 공식 6.18.58에서 새로 시작한 현재 개발 |
| `miatoll/6.18-boot1` | 위 브랜치에서 분기한 최소 RAM 부팅·실기기 증거 및 진단 도구 |
| `miatoll/6.18-display1` | 확인된 boot1을 보존하고 네이티브 화면 경로를 활성화한 RAM 시험 후보 |
| `miatoll/6.18-display2` | display1의 SMMU/화면 실패를 보존하고 기존 upstream MDSS reset 연결과 fbdev 플래그를 수정한 후보 |
| `miatoll/6.18-touch1` | 화면이 확인된 display2에 QUP1/SPI11과 FT8756 RAM firmware를 더한 터치 시험 |
| `miatoll/6.18-storage1` | touch1에 SD 컨트롤러를 더한 UFS/SD 읽기 전용 시험 |
| `miatoll/6.18-usb2` | storage1에 PM6150 Type-C·VBUS·DWC3 dual-role을 복구한 USB 역할 전환·host 시험 |

최초 Git 보존 bundle은 백업 디렉터리의 `legacy-kernel.bundle`이다.
공식 태그는 shallow fetch로 고정했으므로 모든 과거 upstream 이력을 보유한 전체 clone은 아니다.

## 하드웨어 소스 선택

사용자의 후속 지시에 따라 **6.14.7 포크를 하드웨어 구현의 주 공급원**으로 선택했다.
기존 로컬 진단 패치들을 새 구현의 기반으로 삼지 않는다. 이전 실기기 로그는 회귀 비교 자료다.

| 소스 | 고정 커밋 | 확인한 성격 |
| --- | --- | --- |
| [linux-6.14.7](https://github.com/sm7125-mainline/linux/tree/d7ab6144bdf26837785ee51d6148664471afdf1b) | `d7ab6144bdf26837785ee51d6148664471afdf1b` | 실제 6.14.7 기반. 최신 추가분에는 Samsung 지원과 오디오 변경도 포함 |
| [linux-6.16](https://github.com/sm7125-mainline/linux/tree/acf91115c735a97fdacf67bcbb314cc917a1a38c) | `acf91115c735a97fdacf67bcbb314cc917a1a38c` | 실제 기반은 6.16-rc7. 브랜치 이름만으로 더 최신/완성된 miatoll 구현으로 판단하지 않음 |
| [lineage-22.2](https://github.com/sm7125-mainline/linux/tree/25247964cdd6083c7fd0188d0c13e60e94cf9937) | `25247964cdd6083c7fd0188d0c13e60e94cf9937` | linux-6.16에서 Android 관련 4개 커밋 추가 |
| [Xiaomi vendor 4.14](https://github.com/LineageOS/android_kernel_xiaomi_sm6250/tree/803b55865869df8558ef07f51bfb8182d95d08ed) | `803b55865869df8558ef07f51bfb8182d95d08ed` | Makefile 4.14.336. 기존 Qualcomm 장치 ABI의 근거 |
| [LineageOS 기기 설정](https://github.com/LineageOS/android_device_xiaomi_sm6250-common/tree/45b3b7dab47ac792be975fb7623f03268c4a6dc2) | `45b3b7dab47ac792be975fb7623f03268c4a6dc2` | init/ueventd/fstab/boot header와 vendor 서비스 구성의 근거 |

분석용 Git 이력은 `/data/hwkim/kernel/reference/strategy/sm7125.git`에 있다.
원본 파일과 Git blob ID는 `reference/sources.json`, 포크 변경 목록은 `reports/`에 보존했다.

## 리베이스와 선별 이식의 사전 비교

각 포크의 공식 기준점에서 포크 tip까지의 전체 차이를, 실제 6.18.58 트리에
`git merge-tree --write-tree --merge-base=<공식 기준점>`으로 적용했다.
작업 브랜치를 변경하지 않는 3-way 충돌 측정이다.

| 후보 | 공식 기준점 | 포크 커밋 | 변경 파일 | 3-way 충돌 파일 |
| --- | --- | ---: | ---: | ---: |
| 6.14.7 전체 패치 | `134876e3415694dfe94fa44678cf853434ea480f` | 73 | 60 | 14 |
| 6.16 전체 패치 | `89be9a83ccf1f88522317ce02f854f30d6115c41` | 58 | 52 | 10 |
| 6.14.7 중 Xiaomi 하드웨어만 선별 | 위와 같음 | 파일/기능 단위 선택 | `port-scope.json` 참고 | 14, 모두 수동 해결 |
| lineage-22.2의 USB/ashmem만 선별 | linux-6.16 | 2개 커밋에 해당 | 17 | 0 |

이는 전체 커밋을 순서대로 리베이스했을 때의 최종 충돌 횟수나 컴파일 오류 수가 아니다.
직렬 rebase를 완료했다고 주장하지 않는다. 원시 로그는 `reports/merge-614.txt`,
`reports/merge-616.txt`다. 선별 이식에서도 카메라/공유 Kconfig 충돌이 남았다.
선별의 목적은 충돌 수를 과장해 줄이는 것이 아니라 불필요한 기기·정책·되돌리기를 배제하는 것이다.

공식 6.18.58을 유지하면서 Xiaomi 하드웨어 차이만 이식하는 방식을 선택했다.
Samsung A52/A72 DT, Samsung 패널/터치, SM5714 충전/연료계 드라이버, 무관한 빈 파일,
범용 GKI 설정 전체는 포함하지 않았다. 기존 upstream curtana/joyeuse 진입 DTS도 삭제하지 않았다.

## 중복 이식 방지와 API 변환

- 기존 upstream SM7125 CPUfreq blocklist는 유지했다. 같은 항목을 다시 추가하지 않았다.
- DRM/MSM, DPU/DSI, Adreno A618, ath10k SNOC, Bluetooth QCA, QDSP6, TAS2562,
  WCD937x, IPA/RMNET, Binder/binderfs는 6.18 드라이버를 사용한다.
- A618에는 빠진 fuse `0x9f`/bin 3, ZAP firmware 이름, HWCG만 추가했다.
  추가 OPP는 `sm7125.dtsi`에 두어 다른 SC7180 기기의 OPP를 바꾸지 않았다.
- 6.14.7 오디오의 S16_LE 고정은 이미 upstream에 있다. quinary MI2S 및 Left/Right
  stereo prefix 변경은 현재 miatoll의 tertiary MI2S/단일 TAS2562 경로에 필요하지 않아 제외했다.
  최종 `sound/soc/qcom/sm8250.c`는 공식 6.18.58과 같다. 새 오디오 지원은 DT 배선/경로와 설정이다.
- CAMSS는 6.18 자원 구조와 공통 entity 연결 코드를 유지했다. SC7180 PHY 표를
  6.18의 평탄화된 레지스터 배열과 PHY 초기화 방식으로 변환했다.
- DW9714는 6.18의 powerdown GPIO/PM 코드를 유지하고 `vin`을 선택적 전원으로 추가했다.
  OV8856에는 기존 오류 정리와 새 orientation/rotation 제어를 함께 유지했다.
- Huaxing/Tianma 패널은 DSI multi-context API로 변환했다. Huaxing 초기화 실패 시
  regulator 참조가 누수되지 않도록 정리했다.
- DRV2624는 GPIO descriptor API, QGauge는 `power_supply_config.fwnode`로 변환했다.
- 기존 MMC CMD48 우회, 로컬 DPU 인계 reset, fbdev 변경, 로컬 FT8756 재작성,
  읽기 전용 QG monitor, 로컬 ath10k PMF 수정은 새 커널에 가져오지 않았다.
  필요성은 새 기준의 재현 로그로 다시 판단한다.

## Android 변경 선별

`lineage-22.2`의 실제 추가 커밋은 다음 네 개다.

| 커밋 | 처리 |
| --- | --- |
| `cadf268709db315c2683df4d0e37eedcd0dc9ca2` USB configfs Android state/uevent | 필요한 USB 인터페이스만 이식 |
| `c98a867877f3bc4ea2a42e9f3425a555f63eed4d` ashmem 복원 | 기존 vendor 설정의 ashmem 요구를 참고해 별도 이식 |
| `2ace5956faf766eab0d20287f72d760af5a5a55c` dm 경계 복사 수정 되돌리기 | 제외 |
| `25247964cdd6083c7fd0188d0c13e60e94cf9937` dm realloc 크기 수정 되돌리기 | 제외 |

추가한 두 인터페이스는 컴파일 검증 대상으로 포함했다. 실제 mmap/purge/USB state 이벤트,
동시성·보안·Android framework 연동은 별도 실행 검증이 필요하다.
Binder/binderfs, SELinux, seccomp, cgroups, BPF, dm-verity, ext4/f2fs, fscrypt,
DMA-BUF heaps 등은 6.18 설정을 켜서 사용한다. Android 부팅 성공을 의미하지 않는다.

## Qualcomm vendor ABI와 Android 부팅의 남은 차이

| 항목 | 확인한 근거와 영향 |
| --- | --- |
| Binder | 4.14와 6.18의 64-bit protocol 8, 주요 구조 크기와 ioctl 번호 일치. 검사 결과는 `reports/binder-abi.json`. 서비스 실행·SELinux 정책·32-bit 전체 ioctl은 별도 검증 |
| GPU/메모리 HAL | vendor ueventd는 `/dev/kgsl-3d0`와 `/dev/ion`을 요구한다. 6.18 DRM/MSM 및 DMA heaps는 해당 ABI를 제공하지 않는다. GPU userspace/allocator/HWC 통합 또는 제한적 호환층 설계 필요 |
| Camera HAL | 기존 `camera.qcom.so`/CHI 및 vendor 카메라 장치 ABI와 CAMSS/V4L2가 다르다. 센서 컴파일이 기존 HAL 호환을 뜻하지 않는다 |
| Audio HAL | 기존 ACDB/Qualcomm mixer/PCM/ADSP 서비스와 새 ALSA 카드를 대조해야 한다. 카드 열거·재생·녹음·마이크·통화는 각각 검증 |
| RIL/IPA/RMNET | vendor는 `/dev/ipa`, `IPA_IOC_MAGIC=0xCF`, `/dev/rmnet_ctrl`, `/dev/smd*` 등을 참조한다. upstream IPA/RMNET·QRTR는 이 제어 ABI의 대체품이 아니다. MPSS 시작, QMI 열거, SIM/망 등록, 데이터, 음성/IMS를 따로 진행 |
| TEE/FastRPC | `/dev/qseecom`, `/dev/adsprpc-smd*` 등 vendor 경로 차이도 남는다. DRM/키 관리/카메라/오디오에 영향 가능 |
| boot.img/init | 제공된 Lineage 기기 설정은 boot header v2와 128 MiB boot 파티션을 사용한다. raw Image/DTB를 기존 boot.img와 교체하는 것만으로 부팅을 보장하지 못한다. DTBO·reserved-memory·cmdline·ramdisk·모듈 조기 로드를 검토해야 함 |
| 암호화된 userdata | 원래 fstab은 `wrappedkey_v0`, metadata encryption과 vendor UFS 경로를 사용한다. upstream fscrypt/ICE 활성화만으로 기존 암호화 데이터를 열 수 있다고 가정하지 않는다. 원본 데이터에 쓰거나 초기화하지 않음 |

위 차이는 공개 소스에서 확인한 인터페이스 요구와 구현의 비교다. 제공되지 않은 모든 vendor
바이너리를 실행 추적하거나 전체 의존성을 증명한 결과는 아니다.

## 이후 순서

2026-10-26의 사용자 승인 RAM 시험에서 새 커널 버전·최소 DT 프로필·USB 셸을 확인했다.
CPU 8개 online과 UFS 열거도 확인했다. 이는 주변장치를 제한한 boot1의 결과다.
로그와 한계는 `reports/device-tests/20261026-232305-boot1/`에 보존했다.
후속 `20261026-233342-boot1-kernel-log/` 기록으로 상세 dmesg 수집도 확인했다.
PSCI PC mode 경고 뒤 OSI topology 초기화 성공, BWMON/Venus consumer 대기,
ICE raw key 전용 경로와 QSEE allowlist 제외를 구분해 기록했다.
display1 실기기에서는 새 커널/USB 셸과 DRM 모드가 확인됐지만 물리 화면·백라이트는 실패했다.
기존 scanout 주소의 SID 0x800 fault와 fbdev 플래그 경고를 근거로 display2를 준비한다.
6.18에 이미 있는 MDSS reset을 DT에 연결하므로 기존 로컬 DPU reset helper는 새로 이식하지 않는다.
로그와 소스 근거는 `reports/device-tests/20261027-000237-display1/`에 있다.

1. boot1의 단독 부팅·상세 로그 수집은 확인했다. 화면 시험 DT의 BWMON/Venus는 비활성화했다.
   display2의 표준 MDSS reset·fbdev 수정으로 화면 인계를 재시험하고 반복 부팅·부하·절전 상태를 검증한다.
   메시지를 숨기는 공통 드라이버 우회는 적용하지 않는다.
2. RAM 시험에서 패널/터치/SD부터 재검증하고 firmware·모듈 공급 경로를 맞춘다.
   이전 SD CMD48·DPU 인계·Wi-Fi PMF 문제가 재현될 때만 기존 수정의 필요한 부분을 검토한다.
3. GPU/카메라/오디오/무선/충전/절전은 기능별 probe→최소 동작→반복/부하 순서로 검증한다.
   QGauge의 선형 전압 잔량을 검증된 SOC/충전 제어로 취급하지 않는다.
4. Android용 ramdisk·모듈 로드·device configuration을 별도로 만들고 vendor ABI 교체/호환
   범위를 결정한다. 새 기준으로 SELinux 정책과 VINTF/HAL 의존성을 검증한다.
5. Android init 진입→adb→framework→화면/입력→오디오/무선→RIL/카메라 순서로 진행한다.
   통화/IMS, 보안 키, 암호화 userdata와 완전한 전력 관리는 별도 완료 조건이다.

실기기 시험은 사용자가 Windows에서 수행한 `fastboot boot` RAM 부팅이다.
실기기 플래시와 모뎀 보정/파티션 쓰기는 계속 금지한다.
