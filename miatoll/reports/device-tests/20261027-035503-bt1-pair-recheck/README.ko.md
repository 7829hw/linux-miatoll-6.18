# bt1 페어링 재확인 — Galaxy Buds Pro

2026-10-27 KST. 같은 bt1 이미지(`fccd44fc…`)를 `fastboot boot`로 다시 RAM 부팅했다. 새 임시 주소로 전원을 켠 뒤
사용자가 지정한 Galaxy Buds Pro와 BR/EDR Just Works 페어링을 다시 했다(btctl rev 4 `pair-classic`).

- 첫 검색에서는 이어폰이 보이지 않았다. 사용자가 다시 페어링 모드로 둔 뒤 두 번째 검색에서 발견했다.
- `ssp_enabled=1`, `pairing_complete=1`, `pair_exit=0`. 직후 연결 1개(`paired_target_connected=1`), 몇 초 뒤 0개였다.
  첫 부팅(`20261027-034959-bt1`)과 같은 결과다.
- 프로필(A2DP/HFP) 없이 기본 ACL만 있어, 약 2초 idle 해제(`HCI_DISCONN_TIMEOUT`)와 부합한다. 실제 해제 사유는 수집하지 않았다.
- 사용자는 이어폰 소리를 확인하지 못해 들리는 확인을 요청했다. 다음 단계는 A2DP 3초 SBC 시험음이다.
- 링크 키는 커널 RAM에만 있고 출력·저장하지 않았다. 주소·이름 원본은 Git 밖에 두었다.
- 아래 진단 루프의 `t=Ns` 줄은 헤더만 읽은 표본 실수다. 연결 수는 별도 `connections` 조회로 확인했다.
