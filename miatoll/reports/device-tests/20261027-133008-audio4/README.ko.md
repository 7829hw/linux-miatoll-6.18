# audio4 실기기 결과 — MBHC 스위치 설정 오류로 플러그 감지 상실

2026-10-27 KST. audio3에 curtana Android DT 값을 적용했다. micbias1–3을 2700 mV로 바꾸고,
`qcom,hphl-jack-type-normally-closed`와 `qcom,ground-jack-type-normally-closed`를 넣었다.
카드는 정상 등록됐지만 이어폰을 다시 꽂아도 MBHC 이벤트가 없었다. Headphone/Mic Jack은 Off였다.
audio3(스위치 속성 없음)에서는 플러그 감지와 임피던스 측정이 됐다. 그래서 downstream의
`qcom,msm-mbhc-hphl-swh/gnd-swh = <1>`은 upstream normally-closed 속성과 같은 뜻이 아닌 것으로 본다. upstream 기본값을 유지한다.
마이크 바이어스 2700 mV는 audio5에서 단독으로 시험한다.
