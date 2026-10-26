#!/usr/bin/env python3
"""Validate the compiled display test DT; this does not prove panel operation."""
from package_boot1 import available, fdt
from boot_v2 import require


def check(dtb, config):
    mdss = '/soc@0/display-subsystem@ae00000'
    dsi = mdss + '/dsi@ae94000'
    panel = dsi + '/panel@0'
    wled = '/soc@0/spmi@c440000/pmic@5/leds@d800'
    gpio = '/soc@0/spmi@c440000/pmic@4/gpio@c000'
    nodes = (mdss + '/display-controller@ae01000', dsi, panel,
             mdss + '/phy@ae94400', wled, gpio, '/soc@0/iommu@15000000')
    for node in nodes:
        available(dtb, node)
    require(fdt(dtb, panel, 'compatible') == 'huaxing,ft8756', 'Wrong display panel')
    pairs = ((panel + '/port/endpoint', dsi + '/ports/port@1/endpoint'),
             (mdss + '/display-controller@ae01000/ports/port@0/endpoint',
              dsi + '/ports/port@0/endpoint'))
    for first, second in pairs:
        for endpoint, peer in ((first, second), (second, first)):
            require(fdt(dtb, endpoint, 'remote-endpoint', 'x') == fdt(dtb, peer, 'phandle', 'x'),
                    'Broken display graph: ' + endpoint)
    require(fdt(dtb, panel, 'backlight', 'x') == fdt(dtb, wled, 'phandle', 'x'), 'Wrong WLED link')
    reset = fdt(dtb, panel, 'reset-gpios', 'x').split()
    require(reset == [fdt(dtb, gpio, 'phandle', 'x'), '3', '1'], 'Wrong panel reset GPIO')
    require(fdt(dtb, dsi + '/ports/port@1/endpoint', 'data-lanes', 'x') == '0 1 2 3', 'Wrong DSI lanes')
    require(fdt(dtb, wled, 'default-brightness', 'u') == '256', 'Unexpected initial brightness')
    require(fdt(dtb, wled, 'qcom,num-strings', 'u') == '3', 'Wrong WLED string count')
    require(fdt(dtb, mdss, 'iommus', 'x').split()[1:] == ['800', '2'], 'Changed display IOMMU binding')
    require(fdt(dtb, panel, 'vddio-supply', 'x') != '0', 'Missing panel supply')
    for node in ('/soc@0/video-codec@aa00000', '/soc@0/pmu@90b6300', '/soc@0/pmu@90cd000'):
        require(fdt(dtb, node, 'status') == 'disabled', 'Unused consumer is active: ' + node)
    require('CONFIG_DRM_CLIENT_DEFAULT="fbdev"\n' in config, 'fbdev console must be the DRM client')
    reset_connected = False
    profile = fdt(dtb, '/chosen', 'miatoll,boot-profile')
    if profile in ('display2-ram-only', 'touch1-ram-only', 'storage1-ram-only'):
        dispcc = '/soc@0/clock-controller@af00000'
        available(dtb, dispcc)
        require(fdt(dtb, dispcc, '#reset-cells', 'u') == '1', 'Invalid reset provider')
        require(fdt(dtb, mdss, 'resets', 'x').split() ==
                [fdt(dtb, dispcc, 'phandle', 'x'), '0'], 'MDSS_CORE reset not connected')
        reset_connected = True
    touch = check_touch(dtb, panel, wled) if profile in ('touch1-ram-only', 'storage1-ram-only') else None
    return dict(passed=True, panel='huaxing,ft8756', touch=touch, expected_mode='1080x2400@60',
                display_graph_bidirectional=True, enabled_ancestry_checked=list(nodes),
                reset_gpio='PM6150L GPIO3 active-low', backlight_default=256,
                display_iommu_binding_preserved=True, unused_bwmon_venus_disabled=True,
                upstream_mdss_core_reset_connected=reset_connected,
                physical_display_confirmed=False)


def check_touch(dtb, panel, wled):
    """FT8756 on SPI11 with every ancestor enabled; touch1 found QUP1 off before."""
    touch = '/soc@0/geniqup@ac0000/spi@a94000/touchscreen@0'
    available(dtb, touch)
    available(dtb, '/soc@0/dma-controller@a00000')
    require(fdt(dtb, touch, 'compatible') == 'focaltech,ft8756-spi', 'Wrong touch controller')
    require(fdt(dtb, touch, 'firmware-name') == 'focaltech_ts_fw_huaxing.bin', 'Wrong touch firmware')
    require(fdt(dtb, touch, 'panel', 'x') == fdt(dtb, panel, 'phandle', 'x'), 'Touch must follow the panel')
    tlmm = fdt(dtb, '/soc@0/pinctrl@3500000', 'phandle', 'x')
    require(fdt(dtb, touch, 'reset-gpio', 'x').split() == [tlmm, '8', '0'], 'Wrong touch reset GPIO')
    require(fdt(dtb, touch, 'irq-gpio', 'x').split() == [tlmm, '9', '2'], 'Wrong touch IRQ GPIO')
    require(fdt(dtb, '/soc@0/geniqup@ac0000/spi@a94000', 'dmas', 'x').split()[0] ==
            fdt(dtb, '/soc@0/dma-controller@a00000', 'phandle', 'x'), 'SPI11 must use GPI DMA1')
    for node in ('/soc@0/geniqup@ac0000/spi@a90000',):
        require(fdt(dtb, node, 'status') == 'disabled', 'Unused SPI10 is active')
    return dict(node=touch, compatible='focaltech,ft8756-spi', spi_hz=8000000,
                firmware='focaltech_ts_fw_huaxing.bin', reset_gpio='TLMM 8', irq_gpio='TLMM 9 falling',
                panel_follower=True, ancestors_and_gpi_dma1_enabled=True, touch_input_confirmed=False)
