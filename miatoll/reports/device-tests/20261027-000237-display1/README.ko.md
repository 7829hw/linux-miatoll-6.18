# display1 실기기 결과 — 화면·백라이트 실패

2026-10-27 KST. 사용자가 제출한 Fastboot/serial 로그와 화면 관찰을 보존했다.
판정: **Linux 부팅·USB 셸 성공, 실제 화면 출력 실패, 백라이트 꺼짐**.
원본 로그의 SHA256·명령 목록·증거 행 번호는 `result.json`에 있다.

## Fastboot 동작의 구분

로그에는 다음 순서가 한 번씩 있다.

1. `fastboot devices`, `getvar product`로 curtana 확인.
2. `fastboot reboot bootloader`로 새 bootloader 세션 시작.
3. 재연결 후 `fastboot boot ...display1.img`로 RAM에 이미지 전송.
4. `6.18.58-miatoll-display1+` USB 셸에서 probe와 dmesg 완료.

`flash`/`erase`/`format`/`unlock` 명령은 없다. 전송 메시지 `Sending 'boot.img'`는
`fastboot boot`의 RAM 이미지 전송이다. `reboot bootloader`는 시험 전 스크립트 단계다.
첨부된 로그에는 Linux 실행 이후 Fastboot로 자동 재부팅한 기록이 없다.
로그 수집이 끝난 뒤의 추가 재부팅 여부는 이 자료만으로 판단할 수 없다.

## 화면 실패의 근거

- uptime 4.35초에서 CPU 0–7 online, USB 응답 및 UFS 디스크 6개 read-only=1 확인.
- `msmdrmfb` 1080×2400/32bpp, DSI connected/DPMS On, CRTC active=1.
- VT 쓰기 완료 표식이 있지만 사용자는 화면이 검고 백라이트도 꺼졌다고 보고했다.
  DRM 등록·atomic state·VT 쓰기는 물리 표시 성공의 증거로 충분하지 않다.
- display SID `0x800`, context bank 3에서 `0x9c000000` 등 부트로더 화면 버퍼 영역의
  SMMU translation fault가 발생했다. 첫 dmesg dump에 10개 메시지,
  fault IRQ snapshot에 7,796회가 기록됐다. 두 번째 dmesg는 같은 사건의 반복 출력이다.
- DSI enable 중 pixel RCG configuration update 경고와 호출 스택이 있다.
- `sys_imageblit`/`sys_fillrect`는 `FBINFO_VIRTFB` 누락을 경고한다.
  이 helper는 경고 후에도 그리기를 계속하므로 이 플래그만으로 검은 화면 전체를 설명하지 않는다.
- WLED `brightness=actual_brightness=256`, `bl_power=0`이지만 현재 드라이버에는
  하드웨어 밝기 readback callback이 없다. 이 값은 실제 광량/모듈 출력 측정이 아니다.
- fbdev의 `blank=4`는 소프트웨어 상태다. 등록 시 초기값이 POWERDOWN으로 설정되는
  경로가 있어 이를 DRM CRTC active 상태와 혼동하지 않는다.

이전 scanout이 남은 채 새로운 IOMMU 도메인으로 전환되는 인계 문제가 주된 수정 가설이다.
현재 6.18의 `msm_mdss_reset()`과 SC7180 DISPCC reset controller는 이미 구현돼 있지만,
해당 MDSS DT에는 `resets` 연결이 없다. 다음 display2에서는 이 표준 경로를 연결한다.

## 수정 범위와 다음 판정

display2는 별도 DT에서 `DISP_CC_MDSS_CORE_BCR`를 MDSS에 연결한다.
MSM fbdev가 `msm_gem_get_vaddr()`로 매핑한 시스템 RAM에는 `FBINFO_VIRTFB`를 지정한다.
RAM 시험의 VT 표시 전 표준 `fb0/blank=0` unblank 요청도 한 번 수행하고 결과를 기록한다.
DSI 클록·WLED·패널 명령과 IOMMU 보호/오류 보고는 유지한다.
커널에 이미 있는 기능을 복제하는 DPU reset helper는 추가하지 않는다.

기존 display1 이미지/ZIP은 보존한다. 수정 후보의 SMMU IRQ·클록 경고·실제 화면·백라이트는
새 실기기 로그로 확인해야 한다.
