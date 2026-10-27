# battery1 실기기 결과 — PM6150 QG 배터리 계측(읽기 전용)

2026-10-27 KST. 브랜치 `miatoll/6.18-battery1`, 커널 `6.18.58-miatoll-battery1+`(bt1 기반). `fastboot boot` 1회.
6.14.7 포크의 `qcom_qg` 드라이버를 수정 없이 사용했다. 이 드라이버는 QG 레지스터·배터리 ADC·SDAM을 읽기만 한다.
판정: **배터리 계측 등록·값 읽기 성공. 전류 배율이 절반이고 부호가 ABI와 반대임을 실기기로 확인.**
화면 유지와 USB 분리·재연결은 사용자가 직접 확인·수행했다.

## 시험 전 Android 기준값

세션 재시작 후 폰이 설치된 Android로 켜져 있었다. 사용자 허가로 ADB `dumpsys battery`를 읽기 전용으로 조회했다.
level 100, status FULL, 4.420 V, 24.9 °C, USB 입력 500 mA였다(`android-reference/`).
shell 권한에서는 SELinux가 power_supply sysfs 직접 읽기를 막았고, dumpsys에는 순간 전류가 없다.
이후 사용자 허가로 `adb reboot bootloader`를 실행했다(쓰기 없음).

## 결과

- `qcom_qg` 전원 공급원 등록. voltage_now 4.481 V, voltage_ocv(SDAM, Android 기록값) 4.418 V, 25.6 °C, capacity 100.
- QG SUBTYPE(PMIC 0x4805, regmap debugfs 한 줄 읽기) = **0x04**.
  downstream `qg-util.c`는 0x3(5 A)에만 152.588 µA/LSB를, 그 밖에는 305.176 µA/LSB를 쓴다. 포크는 항상 5 A 값을 쓴다.
- USB 분리 시험(`battery-unplug-log.txt`, 1초 간격):

| 구간 | 전압 | 보고 전류(포크 배율) | 해석 |
| --- | --- | --- | --- |
| 연결 | 4.481 V(OCV보다 높음) | −81~−92 mA | 충전 |
| 분리(97–137초) | 4.381–4.396 V(OCV보다 낮음) | +48~+76 mA | 방전 |
| 재연결 | 4.481 V | −87~−92 mA | 충전 |

- 부호: 원시값은 충전 시 음수, 방전 시 양수다. power_supply ABI는 충전을 양수, 방전을 음수로 정한다.
- 배율을 바로잡으면 충전 약 165–185 mA, 화면 켠 방전 약 110 mA다. 독립 전류계로 확인하지는 않았다.
- 전압 배율(194.637 µV/LSB)은 downstream `V_RAW_TO_UV`와 같다.
- `current_avg`는 약 30초 주기로 갱신됐다. capacity는 전압 선형 계산이고 status는 항상 Unknown이다(포크 한계).
- 충전 제어 드라이버는 없다. 충전은 PMIC 하드웨어·부트로더 기본 설정으로만 이뤄진다.
