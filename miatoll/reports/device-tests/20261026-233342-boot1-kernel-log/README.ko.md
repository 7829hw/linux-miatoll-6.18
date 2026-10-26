# curtana boot1 상세 커널 로그 — 2026-10-26 KST

사용자가 전달한 `boot1-serial-20261026-233342.txt`를 원본 바이트 그대로 보존했다.
SHA256·관측 수치·로그 행 번호·코드 대조 근거는 `result.json`에 있다.
앞선 `20261026-232305-boot1` 기록을 수정하거나 대체하지 않는다.

## 확인한 결과

- 커널 `6.18.58-miatoll-boot1+`, DT 프로필 `boot1-ram-only`와 USB 진단 셸 재확인.
- probe 시점 uptime **486.86초**에서 응답. 장기 안정성·부하·절전 검증은 아니다.
- 커널 시작 후 **0.472615초**에 `/init` 실행. 전원 인가부터 걸린 전체 시간은 아니다.
- CPU `0-7` online, MemTotal `5,643,080 kB`, UFS `sda`–`sdf` 모두 read-only=1.
- RAM/가상 파일시스템만 마운트, 로드한 모듈 및 해당 시점 deferred probe 목록은 비어 있다.
- `/bin/busybox dmesg`가 실행되고 **`BOOT1_KERNELLOG_EXIT=0`**에 도달했다.
  커널 시작 메시지부터 타임스탬프가 있는 메시지 458개를 수집했다.
- 수집된 dmesg에 Kernel panic/Oops/BUG/WARNING 스택·Call trace·RCU stall·lockup
  시그니처는 없다. 모든 런타임 오류가 없거나 앞으로도 안정적이라는 판정은 아니다.

이번 업로드에는 새 Fastboot 로그나 기기 측 이미지 해시가 없다. 커널 버전·DT 프로필은
앞선 후보와 일치하지만 두 업로드가 동일한 부팅 세션이라는 연속성은 단정하지 않는다.
기존 boot.img와 ZIP은 호스트 보고서의 SHA256과 다시 대조했고 변경하지 않았다.
커널/DT 코드는 이번 분석에서 변경하지 않았다.

## 경고·대기 메시지의 해석

| 메시지 | 코드와 설정을 대조한 판정 | 후속 조치 |
| --- | --- | --- |
| PSCI `failed to set PC mode: -3` | firmware가 기본 PC suspend mode 전환을 거부. 이후 OSI 방식 CPU PM domain topology 초기화는 성공 | 경고를 숨기지 않고 실제 idle/suspend/resume를 별도 검증 |
| `sync_state() pending` 8건 | BWMON 두 노드는 DT에서 활성화됐지만 `CONFIG_QCOM_ICC_BWMON=n`. Venus도 활성화됐지만 드라이버는 모듈이고 RAMdisk에는 모듈이 없음 | 후속 최소 시험 DT에서는 불필요한 consumer를 비활성화. 기능 시험 시에는 드라이버·firmware 제공. 강제 sync 우회는 적용하지 않음 |
| `regulatory.db` 로드 실패 `-2` | firmware 없는 RAMdisk의 파일 누락. Wi-Fi 자체는 이번 DT에서 비활성화 | Wi-Fi 시험에서 서명된 DB와 `regulatory.db.p7s` 공급 |
| UFS `vdd-hba`/`vccq` 공급 전원 없음 | 드라이버가 전원을 이미 켜진 것으로 가정하고 계속 진행. DT에는 `vcc`/`vccq2`가 있으며 실제 SKhynix 장치가 열거됨 | 보드/vendor 배선을 확인하기 전에 임의 regulator를 추가하지 않음. 절전 시 전원 제어는 미검증 |
| `Fixed dependency cycle(s)` 96건 | fw_devlink가 UFS↔PHY·trace graph 등의 의존 순환을 자동 완화한 안내 | 이 문구만으로 미해결 교착이나 부팅 실패로 판정하지 않음 |
| `No soundcards found` | 시험 DT에서 sound/ADSP를 비활성화한 결과 | ALSA 공통 초기화를 오디오 동작 성공으로 취급하지 않음 |
| 알 수 없는 `rcu_nocbs`/`miatoll_boot` 매개변수 | `/init` 환경변수로 전달됨. 후자는 시험 표식 | 최종 설정에서 상속된 RCU/IRQ 옵션을 별도로 정리 |

`devices_deferred`가 비어 있어도 드라이버가 없는 활성 DT consumer는 남을 수 있다.
따라서 그 빈 목록을 모든 하드웨어 초기화 완료로 취급하지 않는다.
UFS 열거에는 커널의 파티션 테이블 읽기가 포함되지만 사용자 파일 읽기·성능 검증은 하지 않았다.
초기 SCSI 메시지 `Write Protect is off`는 장치 보고 상태이며, 이후 셸에서 확인한 Linux
블록 장치 read-only=1과 구분한다. 이 문자열은 파티션 쓰기를 수행했다는 증거가 아니다.

## Android 통합에서 확인된 제한

1. ICE v3.1.75가 인식됐지만 현재 upstream 경로는 **raw key만 지원**한다고 보고한다.
   기존 `wrappedkey_v0` userdata 복호화 호환성은 미해결이다. 데이터를 마운트하거나
   키/암호화를 변경하지 않았다.
2. SCM이 QSEE 버전 `0x1400000`을 반환했지만, 기기가 allowlist에 없어 QSEE 인터페이스
   생성을 건너뛴다. 버전 질의 성공은 vendor TEE/Keymaster 서비스 호환성 검증이 아니다.
   확인 없이 allowlist를 늘리지 않았다.
3. `clk_ignore_unused`, `pd_ignore_unused`, `noirqdebug` 등의 bring-up 옵션이 남아 있다.
   현재 부팅 성공은 정상 절전·열 보호·전력 소비나 Android 운영 설정의 검증이 아니다.

## 다음 검증

단독 RAM 부팅과 상세 로그 수집 단계는 완료했다. 이후 최소 DT의 불필요한 consumer를
정리하고 화면→터치를 기능별 RAM 시험으로 확인한다. USB와 읽기 전용 UFS 기준은 유지한다.
반복 부팅·부하·절전, GPU/무선/오디오/모뎀/카메라/충전 및 Android/LineageOS는 별도 검증이다.

이번 결과는 최초 이미지의 누락된 `dmesg` 링크를 BusyBox 직접 실행으로 보완한 경로를
실기기에서 확인한 것이다. 링크를 추가해 새로 생성한 RAMdisk 자체는 아직 기기에 부팅하지 않았다.
