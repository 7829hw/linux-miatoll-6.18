# audio3 실기기 결과 — 전체 오디오 카드, 이어폰 출력, 내장 마이크

2026-10-27 KST. 브랜치 `miatoll/6.18-audio3`, 커널 `6.18.58-miatoll-audio3+`.
audio1의 전체 카드 DT에 q6afe LPASS HW vote 수정(거부 응답 즉시 전달, 100 ms 간격 최대 5초 재시도)을 더했다.
audio1 세션에서 `boot --from-shell`로 `fastboot boot` 1회 부팅했다.

판정: **부팅 시 전체 카드 자동 등록, 유선 이어폰 양쪽 출력 청취 확인, 내장 마이크 2개 음성 녹음 확인. 이어폰 마이크는 미해결.**

## 카드 등록

1.136초 첫 vote가 `error 0x16`으로 거부됐고, 100 ms 뒤 재시도에서 수락됐다(`accepted after 1 retries`).
이어 WCD937x SoundWire 장치 2개가 bind되고 `Xiaomi-miatoll` 카드가 deferred 없이 등록됐다. ADSP/MPSS fatal은 0이다.

## 이어폰 출력

- 라우팅: sm7125-mainline miatoll UCM(`alsa-ucm-conf` `059aa77e`)의 RX macro·WCD937x 순서와 BootSequence 음량을 `audio-path`로 적용했다.
- 처음 쓴 tinyalsa 2.0.0 `tinyplay`는 재생 없이 0.05–0.1초 만에 끝났다(스피커 PCM에서도 같음).
  그래서 앞선 "안 들림" 응답들은 도구 문제였다. 6회 재생 중 한 회차는 실행기 오류로 시작조차 하지 않았다.
- speaker-tone rev 6 경로를 재사용한 `pcm-test`로 바꿨다. 재생 중 DAPM에서 MultiMedia2 → RX_CODEC_DMA_RX_0 → RX macro → WCD RDAC → HPHL/HPHR가 모두 On이었다.
- 3초 시험음 6회(각 drain 3.03초)를 **사용자가 양쪽 귀에서 들었다.**

## 마이크(48 kHz 모노, 화면에 QUIET/SPEAK NOW 표시)

| 마이크 | 경로 | 조용히 RMS | 말할 때 RMS | 판정 |
| --- | --- | --- | --- | --- |
| 하단(mic1) | UCM Mic1(SMIC ADC0, ADC1) | −68.9 dBFS | −44.5 dBFS(블록 −35~−52) | 음성 녹음 확인 |
| 상단(mic2) | UCM Mic2(SMIC ADC2, ADC2 INP3) | −69.4 dBFS | −43.7 dBFS | 재시험에서 음성 녹음 확인 |
| 이어폰 | 아래 참조 | 약 −84 dBFS | 약 −84 dBFS | 미해결 |

상단 마이크 첫 시험은 말한 위치가 불분명했다. 재시험 두 번은 폰을 움직일 때 USB/IP 연결이 끊겨 실행되지 않았다.
실행기 `--wait-port`로 재연결해 다시 했다.

## 이어폰 마이크(미해결)

- MBHC는 헤드셋을 인식했다(`Headphone Jack=On`, `Mic Jack=On`, 임피던스 약 47–50 Ω).
  녹음 중 MIC BIAS2·AMIC2·ADC2도 On이었다.
- 일반 tx-macro UCM(SMIC ADC1): 시작 순간의 포화 과도 신호(0.28–0.7초)만 들어오고 이후에는 디지털 0이었다.
- curtana Android `mixer_paths_wcd937x.xml`의 `amic2`(SMIC ADC2, ADC2 INP2)와 `DEC0_BCS`까지 맞춰도
  약 −84 dBFS 잡음만 있고 음성 반응이 없었다.
- 남은 원인 후보: MBHC의 마이크 바이어스 모드, 이어폰 극성(CTIA/OMTP). 레지스터 수준 조사가 필요하다.
  `audio-path headset-mic`는 Android 경로로 바꿔 두었지만 실기기 성공은 아니다.

## 기타

스트림 정지 때마다 `wcd937x_codec: clk already disabled` 경고가 한 번씩 나왔다.
