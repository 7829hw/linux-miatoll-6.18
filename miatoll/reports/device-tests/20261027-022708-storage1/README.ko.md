# storage1 실기기 결과 — UFS·SD 읽기 전용 블록 읽기

2026-10-27 KST. 브랜치 `miatoll/6.18-storage1`, 커널 `6.18.58-miatoll-storage1+`.
`fastboot boot` 1회로 RAM 부팅했다. DT는 touch1에 `sdhc_2`(6.14.7 포크 설정 그대로)만 추가했다.
모든 블록 장치를 `blockdev --setro`로 설정한 뒤에만 읽었다. 마운트·쓰기·파티션 내용 출력은 없다.
modem/persist 계열 파티션은 읽지 않았다. 원본은 `storage1-serial-*.txt`(부팅 로그)와 `steps.txt`(단계별 출력)다.
화면·터치 상태와 카드 교체는 사용자가 직접 보고 수행한 것이다.

판정: **UFS 읽기 확인, SD 호스트(UHS-I SDR104 포함) 읽기 확인. `SH64G` 카드는 CMD48 단계에서 초기화 실패**.

## UFS

- LUN sda–sdf 6개가 모두 read-only=1이며, GPT 파티션 이름을 열거했다. `super`는 `/dev/sda17`이다.
- `super`의 앞 64 MiB를 page cache를 비우고 2회 읽어 같은 SHA-256을 얻었다. 처리량은 110–140 MB/s다.
- `sync` applet 링크가 없어 `sync`는 실패했다. 장치가 read-only이고 page cache가 clean이므로
  `drop_caches`로 재읽기를 강제하는 데는 영향이 없다.

## SD 카드 3종 비교

| 카드 | 제조(manfid/date) | SCR CMD48 | 결과 |
| --- | --- | --- | --- |
| SH64G (RCA aaaa) | 미확인(초기화 실패) | 지원(ext reg 조회 시도) | `error -110 reading general info of SD ext reg` → 초기화 중단. 아카이브 결과와 동일하게 재현 |
| SU08G | 0x03/0x5344, 2010-12 | 미지원 | 핫스왑 인식, legacy 25 MHz 3.3 V. 64 MiB 2회 해시 일치, 11 MB/s |
| SM32G | 0x03/0x5344, 2020-10 | 지원 | 핫스왑 인식, **UHS-I SDR104 202 MHz 1.8 V**. 256 MiB 2회 해시 일치, 42–47 MB/s |

- SM32G가 CMD48을 지원하면서 정상 초기화됐으므로 이 호스트의 CMD48/ext reg 경로는 동작한다.
  SH64G 실패는 카드 고유 문제로 판단한다. 카드 CID를 얻지 못해 upstream 형식의 card fixup은 아직 만들 수 없다.
- 카드 검출 GPIO(TLMM 69)와 핫스왑, 1.8 V 전압 전환과 SDR104 tuning이 동작했다.
- SU08G가 high-speed가 아닌 legacy 25 MHz로 동작한 원인은 확인하지 않았다(2010년 SD 2.00 카드).
- 아카이브의 로컬 `mmc_core.sd_extreg_probe` 우회는 이식하지 않았다. 다른 카드에서는 필요하지 않았다.

## 미검증

SD/UFS 쓰기, 파일시스템 마운트, 장시간·대용량 읽기, 절전 중 카드 처리, SH64G의 CID와 card fixup.
