# miatoll/6.18-lineage1 히스토리 재작성 (2026-10-29)

사용자 요청으로 기기 시리얼(fastboot 시리얼, `androidboot.serialno`)을 커밋된 시험 로그에서 `REDACTED`로 바꿨다.
- 범위: `miatoll/6.18-sm7125` 위의 113개 커밋. 바뀐 것은 `miatoll/reports/` 아래 로그·JSON의 시리얼 문자열뿐이다. 소스 트리와 커밋 메시지·작성자·날짜는 같다.
- 결과 JSON과 host validation 파일에 남은 커밋 해시는 당시 빌드의 기록이라 그대로 두었다. 아래 표로 새 커밋을 찾는다.
- 재작성 전 커밋은 로컬의 보호 브랜치(`miatoll/6.18-boot1`, `miatoll/6.18-display1`)와 프로필 브랜치에 그대로 남아 있다. 이 브랜치들은 바꾸지 않았다.

| 이전 | 이후 | 제목 |
| --- | --- | --- |
| 5e565fbef12c | 5728d375e993 | miatoll: prepare isolated RAM boot profile and enable the upstream QUSB2 PHY |
| 3d56ca6e0f2d | 7d79dd3c186d | miatoll: package the RAM-only boot test and Windows log capture |
| 0ac919ef5883 | 50ecf2c348c9 | docs: record boot1 host validation and pending Windows device test |
| 5c6a8393f9ef | 609e6e5d34fa | miatoll: confirm curtana RAM boot and repair kernel log collection |
| 6a8bcceb0d0f | 0d17d34c81c8 | docs: analyze curtana boot1 kernel log and remaining bring-up gaps |
| f5caa9b888e4 | 91c1bbb03df6 | miatoll: enable the Huaxing display path in an isolated RAM profile |
| 1983c0aec259 | 581abb5e970f | miatoll: package native display RAM tests and collect DRM diagnostics |
| 3b82e59046dc | 92a1631b0165 | docs: record display1 host validation and pending device test |
| df554b298aaf | f0333757121c | docs: preserve display1 failure logs and identify display handoff faults |
| dedc133f7e34 | af91ccce7c3b | miatoll: connect the upstream MDSS reset and mark fbdev system RAM |
| 59b056224b0b | 5ce52616e33a | miatoll: package the display2 RAM test and collect display clocks |
| 5b6d5c2c16d7 | 55abb4a6c974 | miatoll: add a WSL runner for single RAM boot tests |
| 50458fdf7da3 | 6f860a01bee1 | docs: record the display2 panel output on curtana |
| 3f601aa43b53 | a128cb94d3b9 | docs: record display brightness, blanking and hold tests on curtana |
| fab0cacd57e8 | f8c849f76ee7 | miatoll: prepare the FT8756 touch RAM test on top of display2 |
| bb4c4adbf27a | 87e6f2f750eb | docs: record FT8756 touch input on curtana |
| ef88aec9fcc3 | 874d9876ff23 | miatoll: prepare the read-only UFS and SD RAM test |
| 7edd5bc03fb0 | 060223f000e4 | docs: record read-only UFS and SD reads on curtana |
| aef36b097d72 | 9103de9b6113 | miatoll: prepare the USB-C role switch and host RAM test |
| 1441356c8800 | 68dccd7f9731 | docs: record USB-C role switching and host mode on curtana |
| 6e5a5764abe2 | bc25621f0e7e | miatoll: prepare the WCN3990 Wi-Fi RAM test |
| c2009469b62f | cc98e6d2f037 | docs: record WCN3990 Wi-Fi firmware start and scan on curtana |
| 1f31acc09a3b | 2480b8ec2db0 | miatoll: prepare the WPA3 association RAM test |
| 5c682b0f9a3b | 2020ce9898bb | docs: record WPA3 association and IPv4 traffic on curtana |
| 2fe26e6b2d28 | 1de90fcbf758 | wifi: ath10k: set PMF peer flag on WCN3990 |
| 9cfa3b080b5f | 1f12065c4823 | miatoll: prepare the WCN3990 PMF peer flag RAM test |
| 11f89e0b593c | b69b6cbffaee | docs: record lower Wi-Fi latency with the WCN3990 PMF peer flag |
| 6dc0eac602c5 | d3457cf69e62 | miatoll: prepare the WCN3991 Bluetooth RAM test |
| 703869774246 | b076899722fb | docs: record WCN3991 Bluetooth bring-up and scans on curtana |
| 7f886fa8bdf6 | 0c36b4934d77 | docs: record Galaxy Buds Pro pairing on curtana |
| c92967964215 | f51202ff988f | docs: record an audible A2DP test tone to the Galaxy Buds Pro |
| be3171617991 | 57d5aa8bf87b | miatoll: prepare the read-only PM6150 QG battery telemetry test |
| 03c5639ab926 | ee67d8a203d4 | docs: record PM6150 QG telemetry and its current scale and sign |
| 16c2f49680ab | 7805e55d76ad | power: supply: qcom_qg: scale current by subtype and report charging positive |
| 4c2ef6030836 | 16823f82e0b9 | miatoll: prepare the QG current scale and sign RAM test |
| 5eb67f3bc088 | 4b17ba47d6d9 | docs: record corrected QG battery current on curtana |
| 960ed04e296e | 18b6736d08f9 | miatoll: restart a running RAM test into Fastboot from the USB shell |
| 80af2405b1ef | 256b28b0a693 | docs: record button-free Fastboot restarts from the RAM shell |
| 467ba915c260 | 96b8c8c38397 | miatoll: prepare the native ADSP audio RAM test |
| a85ff804d030 | 2d0b6c0ae823 | docs: record audio1 ADSP bring-up and the unsupported LPASS HW vote |
| 5c1b3a3ad1d9 | c9c530d6d738 | miatoll: prepare the speaker-only native audio RAM test |
| c740ab9f3e42 | 4e72ca10d03a | miatoll: play a speaker test tone through the native ADSP card |
| 64addfe1f5ac | 421e3553fcec | ASoC: qdsp6: q6afe: retry LPASS core HW votes the DSP rejects early |
| a0a78ce631aa | 056d834cc7cc | docs: record that the LPASS HW vote succeeds when retried later |
| ceac02859fbd | cfd50d5db566 | miatoll: prepare the full audio card test with the q6afe vote retry |
| ea086bddd140 | 41ee32e6149c | docs: record the full audio card, headphones and built-in microphones |
| 6597d5f720dd | 91120e38a14f | miatoll: prepare the headset microphone test with Android MBHC settings |
| e5e312967f9f | 09e7a4f91762 | miatoll: record lost plug detection and prepare a mic-bias-only test |
| 66480e852549 | 9a4696d01035 | miatoll: record lost MBHC interrupts and add the TX SoundWire wake IRQ |
| 984bc954cc0d | 39efb0de4225 | miatoll: record audio6 headset results and route the TX SoundWire wake through the PDC |
| 7e1a9146dcfe | 24de82a643da | soundwire: bus: enable wake on simple clock stop Slaves for the audio8 test |
| f592c77fc46b | b13fd0dfad69 | ASoC: codecs: wcd937x: keep the TX Slave active while a jack is registered |
| 65ae3c048391 | 64d15609f9f9 | miatoll: record audio9 headset detection results |
| 8e54c3b25e71 | 038e077d29b4 | miatoll: log the WCD MBHC state machine for the audio10 test |
| 6cd3d6be9f0a | 7d84043f8987 | arm64: dts: qcom: curtana: scale MBHC thresholds to the 2.7 V mic bias for audio11 |
| 2fa095b7761e | bc1849b5fcf1 | miatoll: record audio11 headset results and drop the MBHC diagnostics for audio12 |
| bc63cb92271d | 90949d0ee8a2 | docs: record wired headset detection and headset microphone results |
| b0b411297827 | ca06d2e5af36 | miatoll: record headset button results and add the audio13 button bins |
| 0aeedaeb2c13 | 2ba1987587b3 | docs: record headset button results |
| 305ced101d45 | 83039663e129 | miatoll: add a checksummed file pull to the RAM test runner |
| c105ca3e0da8 | c2bdf8f61e99 | docs: record the headset microphone listening check |
| 6811208a7779 | f8a7ceb29f38 | miatoll: add the audio14 idle power comparison profile |
| 849dc84871fe | a0c7aefdeac7 | docs: record the idle power cost of keeping the TX SoundWire bus active |
| ee77b6ceca3e | 83ae1527bf6f | miatoll: add the gpu1 Adreno A618 RAM test profile |
| 3bdad15b23ca | deb37c8f0bd8 | docs: record the gpu1 Adreno A618 results |
| 60377865ed2f | 0ab7506d7184 | miatoll: add the gpu2 Mesa freedreno rendering profile |
| 954411b50ed7 | bc372d3e6020 | docs: record the gpu2 Mesa freedreno rendering results |
| 1aeef805100c | d0c4c44f8a7c | miatoll: add the vulkan1 Turnip RAM test profile |
| 2a8935f48723 | 1ce7b2db4b24 | miatoll: add vk-display-probe to the vulkan1 RAM disk |
| 0cdaeb3216da | 67947c717867 | miatoll: add vk-shader-probe to the vulkan1 RAM disk |
| 723267c90a51 | 2a1feb74bdfe | docs: record the vulkan1 Turnip results |
| 1d1670ee1282 | e2963247321e | miatoll: add the modem1 read-only QMI RAM test profile |
| f745bb527eea | 825d7f08b0a8 | docs: record the modem1 MPSS and read-only QMI results |
| 083638204d79 | bb642a73213b | docs: record the modem1 online request and LTE limited service |
| 9208add30f2a | cb2933adf141 | AGENTS: record the SD-card LineageOS and modem online authorizations |
| f18cc1e9a9c9 | 9313ae486cff | AGENTS: name the SM32G card for the SD-card LineageOS route |
| 815a18e41623 | cd11152a340e | miatoll: add the sdexport1 profile to write the SM32G card from WSL |
| 176fb563c030 | bc6a8fe8f6ac | miatoll: finish wiring sd-export into the sdexport1 RAM disk |
| 734509b03c30 | 27c7679bbaab | miatoll: fix sd-export gadget unbind and always rebind the console |
| 7d82b964a1e1 | 9804942b3a6b | miatoll: match the SD export udev rule on persistent-storage IDs |
| 7752ee1fa9ff | 3940b6e09c61 | miatoll: add the lineage1 kernel profile for the SD-card Android boot |
| 77a7d81c5736 | 2793624ecb15 | miatoll: drop android-base options with unmet 6.18 dependencies |
| ed574fe8e4e9 | d794fe7fd292 | miatoll: keep lineage1 stopped at a fatal init error |
| d54b297a4ee5 | 957760aa967b | miatoll: allow a RAM boot without restarting the bootloader first |
| 33d2bb4e4990 | b93068070952 | miatoll: enable UNICODE for the casefolded Android userdata |
| 7eb975e934d7 | cb09d6b9c750 | miatoll: record the SD metadata/userdata reset before the UNICODE boot |
| b349e8dc27f7 | 82328d2ca6eb | miatoll: enable v1 cpusets and uclamp for the Android task profiles |
| cabd68c23714 | 492d8c3704f8 | miatoll: record the LineageOS SD-card boots on the lineage1 kernel |
| 3b26ca6ecc77 | 8559600baef4 | miatoll: record the build-host kernel builds |
| d0364b7e0dd2 | 67d7db17ba4f | miatoll: record the lineage1 overlay and audio results |
| bd83dbade0b6 | b44d8d003a09 | Input: ft8756: add double tap to wake with the Huaxing TDDI panel |
| 4fefc7dabbab | c5d3e568fd9a | Input: ft8756: fix the SPI transfer buffers and the read CRC check |
| 99e13a6416b3 | c73ecef9c09c | drm/panel: huaxing-ft8756: enter the low power mode at power-off |
| 6a7b3e4e9e44 | a34b118ca1f9 | Input: ft8756: trigger on the falling edge of INT |
| 57325659b294 | a93db9e74df7 | drm/panel: huaxing-ft8756: send the rest of the vendor on command |
| c4a4e8dc739b | 0438230604ce | miatoll: record the read-only UFS authorization for LineageOS Wi-Fi |
| ffba51fe71f5 | c19c629f7852 | miatoll: record the one-time WLAN board data copy authorization |
| a046d53ff730 | 3053246a39b0 | miatoll: probe UFS, MPSS and Wi-Fi in the lineage1 profile |
| 04c0c5c2e862 | 953353618a64 | miatoll: pass the los_super partition name to Android |
| 351238b8909f | d3b10845c97a | miatoll: load the regulatory database at boot in lineage1 and default to KR |
| 5db8d9fa5695 | cd74b80ec643 | miatoll: also put the WCN3991 Bluetooth firmware in the lineage1 boot ramdisk |
| c11dc29925e1 | b7517a426b48 | miatoll: record the lineage1 Wi-Fi, Bluetooth and double-tap results |
| 4eeab2b961fa | 0cc804327256 | miatoll: build the haptics drivers into lineage1 |
| 44c72f172748 | 376dbdfc171e | arm64: dts: qcom: curtana lineage1: enable the haptics I2C bus |
| bbbac387b426 | 61b809d0df82 | miatoll: record the lineage1 haptics result |
| 0b082ec93905 | 49c6dbbff14a | Input: aw8695-haptics: play the AW8624 waveform library |
| f2f621603fb1 | 2a856bc9ab4f | miatoll: record the lineage1 haptics waveform and strength result |
| 3cdf3fd4487f | b54754bd9524 | media: qcom: camss: program the SM7125 CSIPHY v1.2.2 |
| 9a13f9f76cb1 | e0c57e29fe94 | miatoll: enable the cameras in lineage1 |
| 2975e5acc7cf | bce314979a70 | media: qcom: camss: number the SC7180 CSIPHYs |
| e3f964da52ac | 7e64e48eb323 | miatoll: record the lineage1 CAMSS raw capture |
| c2980e25a195 | 961739c3b5fb | arm64: dts: qcom: curtana: keep the camera I/O rail on |
| 2d816b1b0160 | 3b007d6c37d4 | miatoll: record the lineage1 CCI master 1 fix |
