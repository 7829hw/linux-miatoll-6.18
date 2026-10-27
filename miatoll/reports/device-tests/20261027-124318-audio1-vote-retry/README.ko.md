# audio1 재시험 — LPASS HW vote는 지원되며 초기에만 거부됨

2026-10-27 KST. audio2 세션에서 `boot --from-shell`로 audio1 이미지(전체 카드)를 다시 RAM 부팅했다.
audio1처럼 1.08초에 `cmd = 0x100f4 returned error = 0x16`이 났고, VA macro는 −110으로 실패했다.

45초에 `echo 62770000.codec > /sys/bus/platform/drivers_probe`로 VA macro probe만 다시 시도했다(드라이버 bind 속성은 막혀 있음).
- VA macro 바인딩 성공. SoundWire가 WCD937x 두 장치(`sdw:2:…:4` RX, `sdw:3:…:3` TX)를 열거했고 `wcd937x_codec`가 둘을 bind했다.
- `Xiaomi-miatoll` 전체 카드가 등록됐고 deferred 목록이 비었다.

결론: 이 ADSP는 vote 명령을 지원하며, audio_pd 시작 직후에만 거부한다.
upstream q6afe는 거부 응답을 대기자에게 전달하지 않고(3초 시간 초과), VA macro는 재시도하지 않아 영구 실패가 된다.
downstream도 같은 요청을 보내지만 Android 부팅 뒤 늦게 보내므로 이 시점 문제를 겪지 않는다.
수정 후보는 audio3(q6afe: 거부 응답 즉시 전달 + 100 ms 간격 최대 5초 재시도)다.
