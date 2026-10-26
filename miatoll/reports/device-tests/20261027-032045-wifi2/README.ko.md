# wifi2 실기기 결과 — WPA3-SAE 연결·DHCP·IPv4 통신 확인

2026-10-27 KST. 브랜치 `miatoll/6.18-wifi2`, 커널 `6.18.58-miatoll-wifi2+`(커널·DT는 이름 외에 wifi1과 같다).
`fastboot boot` 1회로 RAM 부팅한 뒤 `wifi-start`로 MPSS와 `wlan0`를 준비했다(fatal IRQ 0).
판정: **WPA3-SAE·PMF=2·CCMP 연결, DHCPv4, 공유기·외부 ICMP 성공. 왕복 지연이 높음.**

## 비밀번호 처리

사용자는 PC 케이블을 뽑고 OTG USB 키보드를 연결했다. 폰 화면의 셸에서 `wifi-join`을 실행해 SSID를 입력하고,
비밀번호는 화면에 표시되지 않게 입력했다. 비밀번호는 `/run`의 0600 설정 파일에 hex `sae_password`로만 저장됐다.
serial, Git, 로그에는 나오지 않는다. 시험 후 supplicant를 종료하고 설정 파일을 지웠다.
SSID와 MAC/BSSID가 있는 원본은 Git 밖 `dist/miatoll-wifi2/private-logs/`에 두었다.
Git에는 가린 사본 `steps-private-redacted.txt`와 원본 해시만 넣었다.

## 경과

1. 화면에는 `WIFI_JOIN_AUTH_FAILED`가 표시됐다. 그러나 supplicant 로그에서는 5500 MHz AP로
   SAE 인증·연결·키 교환(`PTK=CCMP GTK=CCMP`)과 `CTRL-EVENT-CONNECTED`가 완료돼 있었다.
2. 원인은 RAMdisk에 `/tmp`가 없던 것이다. `wpa_cli`가 클라이언트 소켓을 만들지 못해(`No such file or directory`)
   스크립트가 `COMPLETED`를 읽지 못했다. 이후의 추가 시작 시도는 `ctrl_iface ... in use`로 종료됐다.
3. 연결이 유지된 상태에서 serial로 `/tmp`를 만들고 확인했다(비밀번호 재입력 없음).
   `wpa_state=COMPLETED`, `key_mgmt=SAE`, `sae_group=19`, `pmf=2`, CCMP였다.
   DHCPv4로 192.168.31.149/24(게이트웨이 192.168.31.1)를 받았고 신호는 -46 dBm이었다.
4. 공유기 ping 5/5(RTT 120/225/393 ms), 1.1.1.1 ping 5/5(RTT 25/188/265 ms), 손실 0%.

저장소의 `wifi-join`과 RAMdisk 빌더는 `/tmp`를 만들도록 고쳤다. 고친 RAMdisk는 아직 실기기로 시험하지 않았다.

## 해석과 다음 후보

- 높은 지연은 이전 bring-up의 PMF peer 보완 전 결과와 같은 양상이다. 펌웨어가 `mfp` feature를 보고하지 않아
  6.18 ath10k가 펌웨어 peer 명령에 PMF 비트를 넣지 않는다. 그래서 `pmf=2`는 userspace 협상 결과일 뿐,
  펌웨어 peer 설정을 증명하지 않는다. 다음 후보는 공개 ath-next 제안의 WCN3990 PMF peer 변경을 선별 이식하는 것이다(미검증 가설).
- 공장 MAC 대신 임의 MAC을 사용했다. 2.4 GHz, 장시간, 절전, 재연결, 처리량은 미검증이다.
