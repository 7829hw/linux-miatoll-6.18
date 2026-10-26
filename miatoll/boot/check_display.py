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
    return dict(passed=True, panel='huaxing,ft8756', expected_mode='1080x2400@60',
                display_graph_bidirectional=True, enabled_ancestry_checked=list(nodes),
                reset_gpio='PM6150L GPIO3 active-low', backlight_default=256,
                display_iommu_binding_preserved=True, unused_bwmon_venus_disabled=True,
                physical_display_confirmed=False)
