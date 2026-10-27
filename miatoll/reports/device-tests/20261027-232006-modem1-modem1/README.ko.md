# modem1 실기기 결과 — MPSS 기동과 읽기 전용 QMI 조회

2026-10-27 KST. vulkan1 위에 다음을 RAM 디스크에 추가했다.
- qmicli(libqmi 1.36.0, QRTR): Alpine v3.22 main/community. 두 APKINDEX의 RSA 서명을 Alpine 키로 확인했다. 키는 두 경로에서 받아 동일함을 확인했다.
- 읽기 전용 래퍼 `modem-query`: QMI get 요청만 보내고 식별자·위치 필드를 가린다.
- MPSS는 기존 `wifi-start`로 기동했다(NV 원본 파티션은 read-only, RAM-shadow rmtfs, 자동 복구 비활성).
- 이번 시험에서 쓴 QMI 요청은 모두 조회(get)다. 운영 모드·SIM·NV/EFS를 바꾸는 요청은 보내지 않았다.
- SIM 없음(사용자 확인).

## 결과 (장치 런타임)
- MPSS `modem.mbn` 62183024 B 부팅 → remoteproc0 `running`.
- QRTR 노드 0(모뎀) 서비스: DMS, NAS, WDS, UIM, Voice, WMS, CAT, PDC, IPA control, Data Port Mapper, Location, IMS, ATH10k WLAN 등. 노드 1(apps)에 RMTFS·TFTP, 노드 5(ADSP)에 sensors·SLIMbus.
- DMS:
  - 제조사 QUALCOMM INCORPORATED, model '0'.
  - revision `MPSS.AT.4.4.c6-00071-RENNELL_GEN_PACK-3 (Dec 05 2022)`.
  - capabilities: GSM/UMTS/LTE, SIM 지원, non-simultaneous-cs-ps.
  - IMEI 등 식별자는 존재만 확인했다(값은 가림, Git·로그에 남기지 않음).
- 운영 모드: `shutting-down`(부팅 후 약 50 s 뒤에도 같음), HW restricted no.
- UIM: 슬롯 1·2 모두 `no-atr-received`(SIM 없음과 일치).
- NAS:
  - `not-registered-searching`, CS/PS detached, GSM/WCDMA/LTE 서비스 없음.
  - signal-strength는 망 없음(-128 dBm)이지만 IO -106 dBm·SINR 9.0 dB로 수신 경로 측정값이 나왔다.
  - signal-info는 InformationUnavailable.
- rmtfs가 RAM shadow로 모뎀 EFS 요청을 처리했다(rmtfs.log).

## online 전환 (사용자 허락, 런타임 상태만)
사용자가 SIM 없이 DMS 운영 모드 `online` 요청 1회를 허락했다. 기록은 AGENTS.md에 남겼다. SIM/PIN·통화·SMS·데이터·NV/EFS·파티션 쓰기는 하지 않았다.
- `qmicli --dms-set-operating-mode=online`: 성공. 모드가 `shutting-down` → `online`으로 바뀌었다.
  - 부팅 직후의 `shutting-down`은 호스트(RIL 역할)의 online 요청을 기다리는 상태로 보인다.
- 60 s 뒤 NAS 상태:
  - LTE service `limited`(SIM 없음 → 긴급 서비스용 camping), Service capability cs-ps.
  - MCC 450 / MNC 08. Cell ID와 TAC는 가렸다.
  - GSM/WCDMA는 none.
- 신호(LTE): RSSI -54 dBm, RSRP -79~-85 dBm, RSRQ -9~-10 dB, SNR 8.2~12.6 dB.

## 남은 일
- SIM을 이용한 망 등록, 데이터(IPA/rmnet, WDS), 통화·SMS는 미시험이다.
- RIL/Android 연동도 미시험이다.
