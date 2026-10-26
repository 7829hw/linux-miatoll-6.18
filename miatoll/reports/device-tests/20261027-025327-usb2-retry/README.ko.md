# usb2 실기기 결과 — USB-C 역할 전환·host 모드 확인

2026-10-27 KST. 브랜치 `miatoll/6.18-usb2`, 커널 `6.18.58-miatoll-usb2+`.
첫 시도(`20261027-024842-usb2`)가 fastboot 전송 정지로 실패했다. 사용자 승인 후 1회 재시도로 RAM 부팅했고 쓰기는 없다.
DT는 storage1에서 boot1의 peripheral 전용 설정을 되돌렸다. PM6150 Type-C, VBUS, DWC3 role switch를
6.14.7 포크·공통 DT 상태로 복구하고, Type-C/VBUS 드라이버 내장과 dual-role DWC3를 사용했다.
화면 표시와 OTG 장치 교체·키보드 입력은 사용자가 직접 보고 수행했다.

판정: **기본 device 역할(ACM), Type-C 연결에 따른 host 전환, USB 저장장치·HID 입력, device 역할 복귀 확인**.

## 결과

- 부팅 후 `typec/port0`는 power `source`, data role `device`, partner 없음이었다.
  PC는 USB-A→C 케이블(Rp)이라 source 전용 포트와 Type-C 연결을 맺지 않는다.
  DWC3는 기본 peripheral 모드로 ACM 콘솔을 제공했다.
- 사용자가 PC 케이블을 뽑고 OTG로 USB 메모리를 연결했다. role이 host로 바뀌고 xHCI가 시작됐다(141초).
  64.2 GB 메모리는 high-speed로 `sdg`(`sdg1`, `sdg2`)로 등록됐다.
  감시 스크립트가 read-only(`ro=1`)로 설정한 뒤 16 MiB를 2회 읽었고 SHA-256이 일치했다(약 15 MB/s).
  분리 시 `Synchronize Cache failed`는 장치 제거 때의 일반 메시지이며 쓰기는 없었다.
- 이어서 QSENN 2.4G 무선 수신기가 HID 키보드·마우스로 등록됐다(183초). 사용자는 입력한 글자가 화면에 보였다고 확인했다.
- 장치를 빼고 PC 케이블을 다시 연결하자 xHCI가 제거되고 device 모드로 돌아왔다(220초).
  ACM 콘솔도 재열거됐다. configfs gadget은 UDC core가 다시 bind했으며 스크립트의 재bind 경로는 쓰이지 않았다.
- 감시 로그의 역할 순서: device(partner 없음) → host(partner attached) → device. 원본은 `usb-host-watch-log.txt`다.
- SMMU fault·커널 WARNING은 0건이고 화면·터치는 정상이었다.

## 시험 도구 관련 기록

- 6.18의 usb_role 클래스는 userspace 제어가 허용된 경우에만 `role` 속성을 노출한다. 그래서 패키징된 감시 스크립트는
  역할을 읽지 못했다. DWC3 debugfs `mode`를 읽도록 고친 스크립트(SHA-256 `01a72aee…8a5b`)를
  serial로 `/run`에 넣어 실행했다. 커널·이미지는 바뀌지 않았다.
- 화면의 디스크 읽기 횟수 표시는 자기 로그 줄까지 세어 증가했다(표시 버그, 실제 읽기는 2회). 저장소 스크립트를 수정했다.
- RAMdisk에 `chmod`/`uniq`/`sync` applet 링크가 없었다. 이후 프로필에서 추가한다.

## 미검증

Type-C partner로서 PC(USB-C DRP)와의 연결, 충전·전원 역할 전환과 PD, 화면/USB 동시 절전,
USB 3 경로(이 기기는 USB 2.0 전용 DT), USB 쓰기와 장시간 사용.
