# audio1 실기기 결과 — ADSP 동작, 전체 카드 등록 실패(LPASS HW vote 미지원)

2026-10-27 KST. 브랜치 `miatoll/6.18-audio1`, 커널 `6.18.58-miatoll-audio1+`(reboot1 기반). `fastboot boot` 1회.
DT는 6.14.7 포크의 전체 카드(TAS2562 스피커 + WCD937x/SoundWire/LPASS macro)를 그대로 켰다.

- ADSP `running`, audio_pd UP, q6v5 fatal 0. APR의 q6core·q6afe·q6asm·q6adm 바인딩.
- TAS2562가 GENI I2C9의 `9-004c`에 바인딩됐다.
- ALSA 카드는 없다(`no soundcards`). 지연 사유는 `snd-sm8250: WCD Playback: codec dai not found`다.
- 원인: ADSP가 `AFE_CMD_REMOTE_LPASS_CORE_HW_VOTE_REQUEST`(0x100f4)를 `error = 0x16`(unknown cmd)로 거부했다.
  `AFE failed to vote (3)` 뒤 `va_macro ... failed with error -110`. RX/TX macro와 SoundWire 두 개가 VA macro를 기다리며 연쇄로 멈췄다.
- `sound/soc/qcom`은 v6.18.58과 차이가 없고 포크도 같다. 이 ADSP firmware에서는 포크 전체 카드가 같은 이유로 등록되지 않을 것으로 본다.
- 다음: audio2에서 확인된 스피커 경로만 남긴 카드로 재생을 시험한다. WCD937x는 HW vote 없이 macro 클럭을 얻는 방법을 따로 조사한다.
