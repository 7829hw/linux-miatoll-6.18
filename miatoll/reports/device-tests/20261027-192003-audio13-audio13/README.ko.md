# audio13 첫 RAM 부팅 — Linux USB 시리얼 미출현, Android로 부팅됨

2026-10-27 KST. `fastboot boot`의 전송과 부팅은 OKAY였다. 그러나 120초 안에 Linux ACM 포트가 나타나지 않았다.
이후 폰은 `18d1:4e11`(Android ADB)로 보였다. 규칙에 따라 재전송하지 않고 사용자에게 알렸다.
사용자 허락을 받아 `adb reboot bootloader`를 1회 실행한 뒤 같은 이미지로 다시 부팅했고, 이번에는 정상이었다(`20261027-192323-audio13-audio13-retry`).
- audio13은 audio12와 DT 버튼 임계값만 다르다. 원인은 확인하지 못했다.
- 화면 관찰이나 ramoops 같은 크래시 기록은 없다.
- audio9 세션 끝에도 몇 시간 뒤 Android로 넘어가 있었던 적이 있다. 반복되면 원인을 따로 조사한다.
