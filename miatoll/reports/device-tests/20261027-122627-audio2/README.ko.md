# audio2 실기기 결과 — 내장 스피커 시험음 청취 확인

2026-10-27 KST. 브랜치 `miatoll/6.18-audio2`, 커널 `6.18.58-miatoll-audio2+`.
audio1에서 이 ADSP가 LPASS HW vote를 지원하지 않아 WCD937x 경로가 카드 전체를 막는 것을 확인했다.
그래서 WCD dai-link·routing을 빼고 WCD937x·SoundWire·LPASS macro를 끈 스피커 전용 카드로 시험했다.
audio1 세션에서 `boot --from-shell`로 Fastboot에 돌아가 `fastboot boot` 1회로 부팅했다.

판정: **ALSA 카드 등록, 내장 스피커 PCM 재생 완료, 사용자가 1 kHz 시험음을 들었다.**

## 카드

`0 [Xiaomimiatoll]: sm8250 - Xiaomi-miatoll`, MultiMedia1–3 PCM, deferred probe 없음, ADSP running, fatal 0.

## 시험음 도구 수정 과정

아카이브의 speaker-tone은 실기기에서 한 번도 실행되지 않은 도구였다. 이번에 카드 이름 외에 두 가지 결함이 드러났다.

| revision | 결과 |
| --- | --- |
| 2(이미지 포함) | PCM을 라우팅보다 먼저 열어 DPCM이 `no backend DAIs enabled`로 거부(EINVAL). 믹서는 건드리지 않음 |
| 3 | 라우팅 후 열기. HW_PARAMS EINVAL, 믹서 원복 |
| 4–5 | 진단: refine 범위를 출력. 정확한 요청 조합 자체가 거부됨 |
| 6 | `q6asm-dai`가 period/buffer 크기를 480 frame 단위로 제한한다. period 960/buffer 3840으로 고쳐 재생 성공 |

revision 3–6은 USB 셸로 `/run`에 넣고 폰에서 SHA-256을 확인했다.

## 재생

48 kHz·S16·2채널, period 960/buffer 3840 frame, 1 kHz 144,000 frame(피크 −42.1 dBFS, 10 ms fade).
재생 중 앰프 게인은 raw 0이었고 끝난 뒤 16으로 복원했다. drain 완료 2,985 ms, 라우팅·입력 선택 원복, exit 0.
**사용자가 내장 스피커에서 소리를 들었다고 확인했다.** 음압·음질·좌우 구분·장시간 재생은 미검증이다.

## 미검증

이어폰·마이크(WCD937x)는 HW vote 없이 macro 클럭을 얻는 방법이 필요하다. 통화 경로와 볼륨 곡선도 미검증이다.
아카이브의 speaker-tone 호스트 시험은 revision 2–6에 대해 다시 실행하지 않았다.
