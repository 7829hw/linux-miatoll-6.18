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

## A2DP 시험음 — 사용자 청취 확인

같은 부팅에서 아카이브의 `bt-tone` revision 1(161,008 bytes, SHA-256 `cf6f0b2f…`)을 serial로 `/run`에 넣고,
폰에서 해시를 확인했다. 아카이브 실행 스크립트는 이전 컨트롤러 주소가 고정돼 있어 쓰지 않았다.
이번 부팅의 임시 주소와 이어폰 주소를 인자로 직접 실행했다.

- SDP에서 A2DP sink(L2CAP PSM 25, AVDTP 1.3)를 찾았다. 보안 수준 2, 16바이트 키.
- AVDTP Discover·GetCapabilities(SBC `3fff0225`)·SetConfiguration·GetConfiguration(`11152020`)·Open·Start·Suspend·Close가 모두 수락됐다.
- 440 Hz·3초·입력 -40 dBFS 시험음을 SBC 1,125 frame/RTP 141 packet으로 3,082 ms에 보냈다(MTU 679, bitpool 32, 48 kHz).
  최대 송신 일정 지연은 3,042 µs, `tone_exit=0`.
- **사용자가 이어폰에서 시험음을 들었다고 확인했다.** 음질·끊김, 장시간 재생, 통화·마이크, 다른 코덱은 미검증이다.
