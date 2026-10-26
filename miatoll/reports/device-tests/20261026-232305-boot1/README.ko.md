# curtana boot1 실기기 시험 — 2026-10-26 KST

판정: **새 Linux 6.18.58 커널이 RAM 사용자 공간과 USB 진단 셸까지 부팅했다.**
사용자가 Windows PC에 연결한 기존 curtana에서 실행한 로그다.
이 디렉터리의 두 `.txt` 파일은 업로드 원본 바이트를 그대로 보존한다.
파일 크기·SHA256과 기계 판독 결과는 `result.json`에 기록했다.

## 판정 근거

- Fastboot 제품명 `curtana`, 새 bootloader 세션, `fastboot boot` 요청 1회 및 `Booting OKAY`.
- USB 셸의 `uname -r`: `6.18.58-miatoll-boot1+`.
- 실제 DT의 chosen 프로필: `boot1-ram-only`.
- 셸이 `boot-probe`를 실행하고 `BOOT1_PROBE_END`에 도달했다.
- CPU `0-7` online, MemTotal `5,643,080 kB`, probe 시점 uptime `3.34`초.
- ACM gadget이 `a600000.usb`에 연결되고 UDC 상태 `configured`.
- UFS 디스크 `sda`–`sdf`와 파티션 열거. 6개 모두 read-only=1.
- RAM/가상 파일시스템만 마운트했고 모듈 목록은 비어 있다.
  deferred probe 목록도 해당 snapshot에서는 비어 있다.

보존된 배포 boot.img SHA256은
`ca100f9ebb5cba93608ff755e79ec2e9f7ffcc34e024eba8b5100671e3c9ff75`다.
배포 이미지/ZIP의 실제 해시는 기존 호스트 보고서와 다시 대조했다.
기기 로그에는 이미지 해시 자체가 출력되지 않으므로 파일명·커널 버전·DT 프로필을 통해
시험 후보와 연결한다. 커널 빌드/패키징 소스 커밋은 `result.json`을 참고한다.

## 진단 누락과 후속 수집

상세 커널 로그 대신 다음 오류가 기록됐다.

```text
/bin/boot-probe: line 31: dmesg: not found
```

최초 RAMdisk 생성기의 BusyBox 링크 목록에 `dmesg`가 빠진 진단 도구 구성 오류다.
부팅 실패를 뜻하지 않는다. 커널 초기화 경고/오류가 없다고 판정할 수도 없다.
동일한 정적 ARM64 BusyBox에 `dmesg` applet이 있음을 QEMU로 확인하고
새 RAMdisk에 링크를 추가했다. 호스트 검증은 `diagnostic-fix-validation.json`에 있다.
커널 코드는 변경하지 않았다.

현재 Git의 `miatoll/boot/Test-Boot1.ps1`은 `/bin/busybox dmesg`를 직접 실행하고,
명령 echo와 구별되는 종료 코드 행까지 기다린다. 기존 압축 해제 폴더에 이 스크립트를
복사한 뒤 아래처럼 실행하면 **현재 실행 중인 boot1에서 재부팅 없이** 수집한다.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Test-Boot1.ps1 -CaptureOnly
```

COM 포트 자동 검색이 안 되면 실제 포트 번호로 `-Port COM5` 등을 추가한다.
`-CaptureOnly` 경로는 fastboot를 호출하지 않는다. 새 캡처 경로의 Windows 실행은 아직 미검증이다.
기존 시험 boot.img와 Windows ZIP, 패키지 생성 당시 호스트 보고서는 변경하지 않았다.

## 미검증 범위

UFS의 사용자 파일 읽기·성능, 장기 안정성·반복 부팅·부하·절전, 화면 표시·터치,
SD/GPU/카메라/오디오/모뎀/무선/충전, Android/LineageOS와 vendor HAL 호환성은
이번 결과로 확인되지 않는다. 첫 시험의 주요 주변장치는 DT에서 비활성화했다.
기본 부팅 성공 이후에도 기능별 RAM 시험과 별도 Android 통합 검증이 필요하다.
