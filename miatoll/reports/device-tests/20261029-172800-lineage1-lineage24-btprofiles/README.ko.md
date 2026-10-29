# lineage1 Wi-Fi·모뎀·Bluetooth (SD 카드 LineageOS 22.2)

2026-10-29 KST. 사용자 허락(AGENTS.md 2026-10-29 항목)에 따라 lineage1 DT에서 UFS·MPSS·Wi-Fi를 켰다. IPA는 꺼 둔다.

## 커널 쪽 변경
- lineage1 DT: UFS 컨트롤러, MPSS remoteproc, Wi-Fi(ath10k_snoc) 활성화; IPA 비활성.
- 커널 명령줄: `androidboot.super_partition=los_super`, `androidboot.wificountrycode=KR`(SIM 없음).
- 부트 ramdisk 뒤에 두 번째 newc 아카이브로 `/lib/firmware/regulatory.db(.p7s)`와 WCN3991 BT 펌웨어(`qca/`)를 붙였다.
  cfg80211(late_initcall)과 hci_qca(약 0.6 s)가 `/vendor` 마운트 전에 읽기 때문이다.

## 시행에서 확인한 문제와 수정
- lineage21: first-stage init이 `by-name/super` 실패로 bootloader 재부팅(pstore 확인). 내부 UFS에도 super/metadata/userdata/misc가
  있고, first-stage는 필요한 파티션을 장치와 무관하게 이름으로 찾는다. SD 파티션을 `los_*`로 바꾸고(GPT 이름만, `write_sd.sh rename`)
  super 메타데이터의 블록 장치 이름도 `los_super`로 맞췄다(lpdump 확인).
- lineage22: 2.4 GHz에만 연결. regdb 미로드로 world(00) 도메인 → ramdisk에 regdb를 넣어 해결(lineage23 이후 5 GHz 연결, 사용자 확인).
- lineage22: ADSP `offline`(모뎀 추가로 remoteproc 번호 변경). Android 쪽에서 이름으로 찾아 시작하도록 수정 → `running`, 사운드카드 등록.
- lineage22: BT가 켜지지 않음. 주소 없는 QCA가 unconfigured로 등록돼 HAL이 대기하다 스택이 abort. dragonboard `set_bdaddr.sh`
  (serialno에서 주소 생성, 공장 주소 아님)와 BT 펌웨어 ramdisk 수록으로 해결.

## 장치 런타임 결과
- UFS 블록 장치 sda–sdf 모두 `ro=1`, 마운트 없음. EFS 링크(modemst1/2, fsg, fsc)는 읽기 전용 rmtfs(RAM shadow)만 사용.
- 모뎀 `running`, ath10k 펌웨어 `WLAN.HL.3.2.2-00947`, 기기 BDF(`cal file`) 사용, wlan0 MAC은 무작위.
- Wi-Fi: 2.4 GHz·5 GHz 연결과 인터넷 동작(사용자 확인). 국가 코드 KR.
- Bluetooth: 검색·페어링, A2DP(소프트웨어 SBC 등) 이어폰 재생(사용자 확인).
- 미확인: Wi-Fi 처리량·장시간·절전, BT HFP 통화 음성(SCO 경로 없음), 공장 BD/Wi-Fi MAC 주소.
