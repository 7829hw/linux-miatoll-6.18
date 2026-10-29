#!/usr/bin/env python3
"""Package one curtana RAM boot candidate without modifying existing artifacts."""
import importlib.util
import io
import stat
import argparse
import json
from pathlib import Path, PurePosixPath
import shutil
import struct
import subprocess
import sys
import tempfile

from boot_v2 import digest, parse_boot, require
from build_initramfs import build as build_initramfs
import build_shim

ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = ROOT.parent
BOOT = ROOT / 'miatoll/boot'
TOOLS = WORKSPACE / 'tools'
PINS = {
    'aosp-mkbootimg/mkbootimg.py': '37d84b3d162e0bc62e36c1f4e1c63c85ea0caa9f29be023eb2f8efe006ad948c',
    'aosp-mkbootimg/unpack_bootimg.py': 'a9d260978a63bd06a24b6347e7dee8a28ff96639793caea15dff6aa491316308',
    'aosp-avb/avbtool.py': '78a50c8620985709f2e131cf948dcd66ecc43f09ed735e09d75751a7e21e4eb8',
}

def fdt(dtb, node, prop, kind='s'):
    return subprocess.check_output(['fdtget', '-t', kind, str(dtb), node, prop], text=True).strip()

def available(dtb, node):
    path = PurePosixPath(node)
    for parent in (*reversed(path.parents), path):
        properties = subprocess.check_output(['fdtget', '-p', str(dtb), str(parent)], text=True).splitlines()
        if 'status' in properties:
            require(fdt(dtb, str(parent), 'status') in ('okay', 'ok'), 'Disabled USB ancestor: ' + str(parent))

def analyze_avb(module, path):
    handle = module.ImageHandler(str(path), read_only=True)
    footer, header, descriptors, size = module.Avb()._parse_image(handle)
    require(footer is not None and header.algorithm_type == 0, 'Expected unsigned AVB hash metadata')
    hashes = [x for x in descriptors if isinstance(x, module.AvbHashDescriptor)]
    properties = {x.key: x.value.decode('utf-8') for x in descriptors if isinstance(x, module.AvbPropertyDescriptor)}
    require(len(hashes) == 1 and hashes[0].partition_name == 'boot', 'Unexpected AVB descriptors')
    entry = hashes[0]
    require(entry.flags == 0 and entry.hash_algorithm == 'sha256', 'Unexpected boot hash parameters')
    require(entry.image_size == footer.original_image_size, 'Invalid AVB payload size')
    import hashlib
    require(entry.digest == hashlib.sha256(entry.salt + path.read_bytes()[:entry.image_size]).digest(), 'AVB digest mismatch')
    return {'bytes': size, 'salt': entry.salt.hex(), 'flags': header.flags,
            'rollback_index': header.rollback_index, 'rollback_index_location': header.rollback_index_location,
            'properties': properties}

PROFILES = ('boot1', 'display1', 'display2', 'touch1', 'storage1', 'usb2', 'wifi1', 'wifi2', 'wifi3', 'bt1', 'battery1', 'battery2', 'reboot1', 'audio1', 'audio2', 'audio3', 'audio4', 'audio5', 'audio6', 'audio7', 'audio8', 'audio9', 'audio10', 'audio11', 'audio12', 'audio13', 'audio14', 'gpu1', 'gpu2', 'vulkan1', 'modem1', 'sdexport1', 'lineage1')

def newc_archive(entries):
    """Uncompressed newc cpio; entries are (path, bytes) or (path, None) for a directory."""
    stream = io.BytesIO()
    for inode, (name, data) in enumerate(entries + [('TRAILER!!!', b'')], start=1):
        mode = (stat.S_IFDIR | 0o755) if data is None else (0 if name == 'TRAILER!!!' else stat.S_IFREG | 0o644)
        data = data or b''
        encoded = name.encode() + b'\0'
        fields = (inode, mode, 0, 0, 2 if data == b'' and mode & stat.S_IFDIR else 1, 0,
                  len(data), 0, 0, 0, 0, len(encoded), 0)
        stream.write(b'070701' + b''.join(f'{n:08x}'.encode() for n in fields))
        stream.write(encoded)
        stream.write(b'\0' * (-stream.tell() % 4))
        stream.write(data)
        stream.write(b'\0' * (-stream.tell() % 4))
    return stream.getvalue()


def main(profile='boot1', android_ramdisk=None):
    require(profile in PROFILES, 'Unknown RAM test profile')
    DIST = WORKSPACE / ('dist/miatoll-' + profile)
    OUT = WORKSPACE / ('out-miatoll-' + profile)
    DIST.mkdir(parents=True, exist_ok=True)
    for path, expected in PINS.items():
        require(digest((TOOLS / path).read_bytes()) == expected, 'Changed tool: ' + path)
    # The original uploaded boot.img is no longer present. Use the intact,
    # previously validated audio2 container only as the header/AVB reference.
    reference = WORKSPACE / 'dist/boot-curtana-6.18-stockdt-shim-audio2.img'
    require(digest(reference.read_bytes()) == 'd99f276d122f54ed5eb1df6a0883b166c38e7d4df2df881e7b22da188eed2b3f', 'Changed reference container')
    header, original_parts = parse_boot(reference.read_bytes())
    stock_dtb = WORKSPACE / 'reference/pixelos/dtb'
    require(stock_dtb.read_bytes() == original_parts['dtb'], 'Outer DTB differs from preserved stock DTB')
    stock_kernel = (WORKSPACE / 'reference/pixelos/kernel').read_bytes()
    require(stock_kernel[56:60] == b'ARM\x64', 'Invalid original kernel header')
    stock_runtime = struct.unpack_from('<Q', stock_kernel, 16)[0]
    kernel = DIST / 'kernel/Image'
    config = (DIST / 'kernel/.config').read_text()
    release = (DIST / 'kernel/kernelrelease.txt').read_text().strip()
    require(release == '6.18.58-miatoll-' + profile + '+', 'Unexpected test kernel release: ' + release)
    require(('Linux version ' + release).encode() in kernel.read_bytes(), 'Wrong kernel payload')
    for symbol in ('BLK_DEV_INITRD', 'RD_GZIP', 'DEVTMPFS', 'USB_CONFIGFS_ACM',
                   'PHY_QCOM_QUSB2', 'DRM_SIMPLEDRM'):
        require('CONFIG_' + symbol + '=y\n' in config, 'Missing built-in: ' + symbol)
    # Dual-role DWC3 includes the gadget side used by the ACM console.
    require('CONFIG_USB_DWC3_GADGET=y\n' in config or 'CONFIG_USB_DWC3_DUAL_ROLE=y\n' in config,
            'Missing built-in DWC3 gadget support')
    if profile != 'boot1':
        for symbol in ('DRM_MSM', 'DRM_MSM_DPU', 'DRM_MSM_DSI', 'DRM_MSM_DSI_10NM_PHY',
                       'DRM_PANEL_HUAXING_FT8756', 'BACKLIGHT_QCOM_WLED', 'SC_DISPCC_7180',
                       'DRM_FBDEV_EMULATION', 'DRM_CLIENT_DEFAULT_FBDEV', 'FRAMEBUFFER_CONSOLE'):
            require('CONFIG_' + symbol + '=y\n' in config, 'Missing display built-in: ' + symbol)
    if profile in ('touch1', 'storage1', 'usb2', 'wifi1', 'wifi2', 'wifi3', 'bt1', 'battery1', 'battery2', 'reboot1', 'audio1', 'audio2', 'audio3', 'audio4', 'audio5', 'audio6', 'audio7', 'audio8', 'audio9', 'audio10', 'audio11', 'audio12', 'audio13', 'audio14', 'gpu1', 'gpu2', 'vulkan1', 'modem1', 'sdexport1', 'lineage1'):
        for symbol in ('SPI_QCOM_GENI', 'QCOM_GPI_DMA', 'TOUCHSCREEN_FT8756', 'INPUT_EVDEV'):
            require('CONFIG_' + symbol + '=y\n' in config, 'Missing touch built-in: ' + symbol)
    dtb = OUT / ('arch/arm64/boot/dts/qcom/sm7125-xiaomi-curtana-' + profile + '.dtb')
    require(fdt(dtb, '/', 'qcom,board-id', 'x') == '20022 1', 'Not the curtana board')
    require(fdt(dtb, '/chosen', 'miatoll,boot-profile') == profile + '-ram-only', 'Wrong profile')
    for node in ('/soc@0/usb@a6f8800/usb@a600000', '/soc@0/phy@88e3000'):
        available(dtb, node)
    dwc3 = '/soc@0/usb@a6f8800/usb@a600000'
    if profile in ('usb2', 'wifi1', 'wifi2', 'wifi3', 'bt1', 'battery1', 'battery2', 'reboot1', 'audio1', 'audio2', 'audio3', 'audio4', 'audio5', 'audio6', 'audio7', 'audio8', 'audio9', 'audio10', 'audio11', 'audio12', 'audio13', 'audio14', 'gpu1', 'gpu2', 'vulkan1', 'modem1', 'sdexport1', 'lineage1'):
        for symbol in ('TYPEC_QCOM_PMIC', 'REGULATOR_QCOM_USB_VBUS', 'USB_DWC3_DUAL_ROLE', 'USB_ROLE_SWITCH',
                       'USB_XHCI_HCD', 'USB_STORAGE', 'USB_HID'):
            require('CONFIG_' + symbol + '=y\n' in config, 'Missing USB role built-in: ' + symbol)
        require(fdt(dtb, dwc3, 'dr_mode') == 'otg', 'USB must be OTG')
        require('usb-role-switch' in subprocess.check_output(['fdtget', '-p', str(dtb), dwc3], text=True).split(),
                'DWC3 role switch missing')
        typec = '/soc@0/spmi@c440000/pmic@0/typec@1500'
        available(dtb, typec)
        available(dtb, '/soc@0/spmi@c440000/pmic@0/usb-vbus-regulator@1100')
        hs = dwc3 + '/ports/port@0/endpoint'
        peer = typec + '/connector/ports/port@0/endpoint'
        require(fdt(dtb, hs, 'remote-endpoint', 'x') == fdt(dtb, peer, 'phandle', 'x') and
                fdt(dtb, peer, 'remote-endpoint', 'x') == fdt(dtb, hs, 'phandle', 'x'), 'Broken role switch graph')
        require(fdt(dtb, typec + '/connector', 'power-role') == 'source', 'Unexpected Type-C power role')
    else:
        require(fdt(dtb, dwc3, 'dr_mode') == 'peripheral', 'USB must be peripheral')
    disabled = ('/soc@0/remoteproc@8300000',)
    if profile == 'lineage1':
        for symbol in ('VIDEO_QCOM_CAMSS', 'I2C_QCOM_CCI', 'VIDEO_S5KGM2', 'VIDEO_S5K5E9', 'VIDEO_OV16A1Q'):
            require('CONFIG_' + symbol + '=y\n' in config, 'Missing camera built-in: ' + symbol)
        available(dtb, '/soc@0/camss@acb3000')
    else:
        disabled += ('/soc@0/camss@acb3000',)
    if profile in ('gpu1', 'gpu2', 'vulkan1', 'modem1', 'sdexport1', 'lineage1'):
        require('CONFIG_DRM_MSM=y\n' in config and 'CONFIG_QCOM_MDT_LOADER=y\n' in config, 'Missing GPU built-in')
        for node in ('/soc@0/gpu@5000000', '/soc@0/gmu@506a000'):
            available(dtb, node)
        require(fdt(dtb, '/soc@0/gpu@5000000/zap-shader', 'firmware-name') == 'qcom/sm7125/miatoll/a615_zap.mbn',
                'Unexpected zap shader name')
    else:
        disabled += ('/soc@0/gpu@5000000',)
    if profile in ('storage1', 'usb2', 'wifi1', 'wifi2', 'wifi3', 'bt1', 'battery1', 'battery2', 'reboot1', 'audio1', 'audio2', 'audio3', 'audio4', 'audio5', 'audio6', 'audio7', 'audio8', 'audio9', 'audio10', 'audio11', 'audio12', 'audio13', 'audio14', 'gpu1', 'gpu2', 'vulkan1', 'modem1', 'sdexport1', 'lineage1'):
        for symbol in ('MMC_SDHCI_MSM', 'MMC_BLOCK', 'SCSI_UFS_QCOM', 'BLK_DEV_SD', 'EFI_PARTITION'):
            require('CONFIG_' + symbol + '=y\n' in config, 'Missing storage built-in: ' + symbol)
        available(dtb, '/soc@0/mmc@8804000')
        require(fdt(dtb, '/soc@0/mmc@8804000', 'cd-gpios', 'x').split()[1:] == ['45', '0'],
                'Unexpected SD card-detect GPIO')
    else:
        disabled += ('/soc@0/mmc@8804000',)
    if profile in ('wifi1', 'wifi2', 'wifi3', 'bt1', 'battery1', 'battery2', 'reboot1', 'audio1', 'audio2', 'audio3', 'audio4', 'audio5', 'audio6', 'audio7', 'audio8', 'audio9', 'audio10', 'audio11', 'audio12', 'audio13', 'audio14', 'gpu1', 'gpu2', 'vulkan1', 'modem1', 'sdexport1'):
        for symbol in ('ATH10K', 'ATH10K_SNOC', 'CFG80211', 'MAC80211', 'QRTR', 'QRTR_SMD',
                       'RPMSG_QCOM_GLINK_SMEM', 'QCOM_Q6V5_PAS', 'QCOM_SYSMON', 'QCOM_PD_MAPPER',
                       'QCOM_RMTFS_MEM', 'VFAT_FS', 'NLS_CODEPAGE_437', 'NLS_ISO8859_1'):
            require('CONFIG_' + symbol + '=y\n' in config, 'Missing Wi-Fi built-in: ' + symbol)
        for node in ('/soc@0/remoteproc@4080000', '/soc@0/wifi@18800000'):
            available(dtb, node)
        require(fdt(dtb, '/soc@0/remoteproc@4080000', 'firmware-name') == 'qcom/sm7125/miatoll/modem.mbn',
                'Unexpected MPSS firmware name')
    if profile in ('bt1', 'battery1', 'battery2', 'reboot1', 'audio1', 'audio2', 'audio3', 'audio4', 'audio5', 'audio6', 'audio7', 'audio8', 'audio9', 'audio10', 'audio11', 'audio12', 'audio13', 'audio14', 'gpu1', 'gpu2', 'vulkan1', 'modem1', 'sdexport1', 'lineage1'):
        for symbol in ('BT', 'BT_LE', 'BT_BREDR', 'BT_HCIUART', 'BT_HCIUART_SERDEV', 'BT_HCIUART_QCA', 'BT_QCA',
                       'SERIAL_QCOM_GENI', 'SERIAL_DEV_BUS'):
            require('CONFIG_' + symbol + '=y\n' in config, 'Missing Bluetooth built-in: ' + symbol)
        uart = '/soc@0/geniqup@8c0000/serial@88c000'
        available(dtb, uart + '/bluetooth')
        require(fdt(dtb, uart + '/bluetooth', 'compatible') == 'qcom,wcn3991-bt', 'Unexpected Bluetooth controller')
    else:
        disabled += ('/soc@0/remoteproc@4080000', '/soc@0/wifi@18800000')
    if profile not in ('audio1', 'audio2', 'audio3', 'audio4', 'audio5', 'audio6', 'audio7', 'audio8', 'audio9', 'audio10', 'audio11', 'audio12', 'audio13', 'audio14', 'gpu1', 'gpu2', 'vulkan1', 'modem1', 'sdexport1', 'lineage1'):
        disabled += ('/soc@0/remoteproc@62400000', '/sound')
    if profile == 'boot1':
        disabled += ('/soc@0/display-subsystem@ae00000',)
    else:
        from check_display import check as check_display
        display_validation = check_display(dtb, config)
    if profile == 'lineage1':
        # Android runs from the SM32G microSD. The internal UFS is probed only
        # for the read-only modem EFS (rmtfs), with MPSS and Wi-Fi; modem data
        # (IPA) stays off.
        disabled += ('/soc@0/ipa@1e40000',)
        for node in ('/soc@0/ufshc@1d84000', '/soc@0/remoteproc@4080000', '/soc@0/wifi@18800000'):
            require(fdt(dtb, node, 'status') == 'okay', 'lineage1 needs ' + node)
        for symbol in ('EROFS_FS', 'F2FS_FS', 'BLK_DEV_DM', 'ANDROID_BINDERFS', 'USB_CONFIGFS_F_FS',
                       'IP_NF_IPTABLES', 'IP6_NF_IPTABLES', 'UHID', 'ZRAM'):
            require('CONFIG_' + symbol + '=y\n' in config, 'Missing Android built-in: ' + symbol)
    for node in disabled:
        require(fdt(dtb, node, 'status') == 'disabled', 'Unexpected active device: ' + node)
    validation_file = WORKSPACE / ('out-miatoll-' + profile + '-shim-test/test-result.json')
    validation = json.loads(validation_file.read_text())
    require(validation['arm64_emulation_passed'] and validation['host_validation_passed'], 'Run test_shim.py first')
    require(validation['template_sha256'] == digest(dtb.read_bytes()), 'DT changed since shim test')
    for name, expected in validation['sources'].items():
        require(digest((ROOT / name).read_bytes()) == expected, 'Retest changed shim source: ' + name)
    if profile == 'lineage1':
        # First-stage Android ramdisk from the LineageOS build (curtana_ml).
        require(android_ramdisk is not None, 'lineage1 needs --android-ramdisk')
        android = Path(android_ramdisk).read_bytes()
        # cfg80211 loads regulatory.db at late_initcall and hci_qca loads the
        # WCN3991 firmware when it registers hci0, both long before Android
        # mounts /vendor. Without them the regulatory domain stays world (00)
        # and no country hint applies, and hci0 fails its setup. The haptics
        # driver loads its waveform library at probe as well. Append the
        # pinned files under /lib/firmware as a second, uncompressed newc
        # archive.
        import bluetooth_payload
        import haptics_payload
        import wifi_payload
        wifi, _ = wifi_payload.load(WORKSPACE)
        regdb = {name: data for name, (data, _) in wifi.items() if name.startswith('lib/firmware/regulatory.db')}
        require(sorted(regdb) == ['lib/firmware/regulatory.db', 'lib/firmware/regulatory.db.p7s'],
                'Missing pinned regulatory database')
        early = dict(regdb)
        early.update(bluetooth_payload.load_bluetooth_firmware(WORKSPACE))
        require(all(name.startswith('lib/firmware/qca/') for name in set(early) - set(regdb)),
                'Unexpected Bluetooth firmware path')
        early.update(haptics_payload.load_haptics_firmware(WORKSPACE))
        extra = newc_archive([('lib', None), ('lib/firmware', None), ('lib/firmware/qca', None)]
                             + sorted(early.items()))
        ramdisk = DIST / 'ramdisk-lineage1.img'
        ramdisk.write_bytes(android + b'\0' * (-len(android) % 4) + extra)
        ramdisk_report = {'android_ramdisk': str(android_ramdisk), 'android_bytes': len(android),
                          'android_sha256': digest(android), 'profile': profile,
                          'appended': {name: digest(data) for name, data in early.items()},
                          'bytes': ramdisk.stat().st_size, 'sha256': digest(ramdisk.read_bytes())}
    else:
        ramdisk = DIST / ('initramfs-' + profile + '.cpio.gz')
        ramdisk_report = build_initramfs(ramdisk, profile=profile)
    shim = build_shim.build(kernel, dtb, WORKSPACE / ('out-miatoll-' + profile + '-shim'))
    require(shim.stat().st_size < stock_runtime, 'Loader footprint exceeds the original kernel budget')
    shutil.copy2(dtb, DIST / dtb.name)
    command_line = ('rdinit=/init console=tty0 loglevel=8 ignore_loglevel clk_ignore_unused '
                    'pd_ignore_unused no_console_suspend deferred_probe_timeout=30 panic=0 '
                    'enforcing=0 miatoll_boot=' + profile)
    if profile != 'boot1':
        command_line += ' consoleblank=0 drm.debug=0x06'
    if profile == 'lineage1':
        # The ramdisk's /init is Android's first stage; partitions come from the
        # SD controller only (androidboot.boot_devices). A fatal init error
        # panics instead of rebooting and panic=0 keeps the kernel there, so the
        # console stays on screen and pstore can be read after a manual reset.
        command_line = ('console=tty0 loglevel=7 clk_ignore_unused pd_ignore_unused deferred_probe_timeout=30 '
                        'printk.devkmsg=on firmware_class.path=/vendor/firmware/ '
                        'androidboot.boot_devices=soc@0/8804000.mmc androidboot.super_partition=los_super androidboot.hardware=curtana_ml '
                        'androidboot.wificountrycode=KR '
                        'androidboot.selinux=permissive androidboot.verifiedbootstate=orange '
                        'androidboot.console=tty0 panic=0 androidboot.init_fatal_panic=true '
                        'miatoll_boot=lineage1')
    plain = DIST / (profile + '-plain.img')
    mkbootimg = TOOLS / 'aosp-mkbootimg/mkbootimg.py'
    command = [sys.executable, str(mkbootimg), '--kernel', str(shim), '--ramdisk', str(ramdisk),
               '--dtb', str(stock_dtb), '--header_version', '2', '--pagesize', '4096', '--base', '0',
               '--board', header['board'], '--os_version', header['os_version'],
               '--os_patch_level', header['os_patch_level'], '--cmdline', command_line, '--output', str(plain)]
    for flag, field in (('kernel_offset', 'kernel_addr'), ('ramdisk_offset', 'ramdisk_addr'),
                        ('second_offset', 'second_addr'), ('tags_offset', 'tags_addr'), ('dtb_offset', 'dtb_addr')):
        command += ['--' + flag, hex(header[field])]
    subprocess.run(command, check=True)
    built_header, parts = parse_boot(plain.read_bytes())
    require(built_header['cmdline'] == command_line, 'Command line mismatch')
    for name, path in (('kernel', shim), ('ramdisk', ramdisk), ('dtb', stock_dtb)):
        require(parts[name] == path.read_bytes(), 'Boot component mismatch: ' + name)
    avb_path = TOOLS / 'aosp-avb/avbtool.py'
    spec = importlib.util.spec_from_file_location('boot1_avb', avb_path)
    avb = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(avb)
    avb_reference = analyze_avb(avb, reference)
    image = DIST / ('boot-curtana-6.18.58-' + profile + '.img')
    shutil.copy2(plain, image)
    command = [sys.executable, str(avb_path), 'add_hash_footer', '--image', str(image),
               '--partition_name', 'boot', '--partition_size', str(avb_reference['bytes']),
               '--algorithm', 'NONE', '--hash_algorithm', 'sha256', '--salt', avb_reference['salt'],
               '--flags', str(avb_reference['flags']), '--rollback_index', str(avb_reference['rollback_index']),
               '--rollback_index_location', str(avb_reference['rollback_index_location'])]
    for key, value in avb_reference['properties'].items():
        command += ['--prop', key + ':' + value]
    subprocess.run(command, check=True)
    analyze_avb(avb, image)
    # This avbtool resolves the 'boot' descriptor as boot.img in the same folder.
    with tempfile.TemporaryDirectory(prefix='boot1-avb-verify-') as temporary:
        checked_image = Path(temporary) / 'boot.img'
        shutil.copy2(image, checked_image)
        verify = subprocess.run([sys.executable, str(avb_path), 'verify_image', '--image', str(checked_image)],
                                check=True, capture_output=True, text=True)
    (DIST / 'avb-verify.txt').write_text(verify.stdout + verify.stderr)
    unpack = WORKSPACE / ('out-miatoll-' + profile + '-unpacked')
    subprocess.run([sys.executable, str(TOOLS / 'aosp-mkbootimg/unpack_bootimg.py'),
                    '--boot_img', str(image), '--out', str(unpack)], check=True, stdout=subprocess.DEVNULL)
    for name in ('kernel', 'ramdisk', 'dtb'):
        require((unpack / name).read_bytes() == parts[name], 'Independent unpack mismatch: ' + name)
    result = {'kernel_release': release, 'image': image.name, 'image_bytes': image.stat().st_size,
              'image_sha256': digest(image.read_bytes()), 'kernel_sha256': digest(kernel.read_bytes()),
              'kernel_build_commit': (DIST / 'kernel/source-commit.txt').read_text().strip(),
              'kernel_runtime_bytes': struct.unpack_from('<Q', kernel.read_bytes(), 16)[0],
              'shim_runtime_bytes': shim.stat().st_size, 'stock_runtime_budget_bytes': stock_runtime,
              'boot_profile': profile + '-ram-only', 'dtb_sha256': digest(dtb.read_bytes()),
              'outer_dtb_sha256': digest(stock_dtb.read_bytes()), 'avb_hash_verified': True,
              'avb_algorithm': 'NONE (unsigned hash metadata, not OEM authentication)',
              'aosp_unpack_verified': True, 'shim_arm64_mock_entry_tested': True,
              'ramdisk': ramdisk_report, 'device_boot_confirmed': False,
              'reference_container': str(reference), 'reference_container_is_stock_image': False,
              'original_uploaded_boot_image_available': False,
              'hardware_scope': 'CPU/RAM, inherited framebuffer, UFS enumeration and USB console only'}
    if profile != 'boot1':
        result.update(hardware_scope='Native Huaxing DPU/DSI/WLED display, USB console and read-only UFS enumeration',
                      display_validation=display_validation, physical_display_confirmed=False)
    if profile in ('touch1', 'storage1'):
        result.update(hardware_scope=result['hardware_scope'] + ', FT8756 SPI touch with RAM firmware',
                      touch_input_confirmed=False)
    if profile in ('storage1', 'usb2'):
        result.update(hardware_scope=result['hardware_scope'] + ', read-only UFS and SD block reads',
                      storage_read_confirmed=False)
    if profile in ('usb2', 'wifi1', 'wifi2', 'wifi3', 'bt1', 'battery1', 'battery2', 'reboot1', 'audio1', 'audio2', 'audio3', 'audio4', 'audio5', 'audio6', 'audio7', 'audio8', 'audio9', 'audio10', 'audio11', 'audio12', 'audio13', 'audio14', 'gpu1', 'gpu2', 'vulkan1', 'modem1', 'sdexport1', 'lineage1'):
        result.update(hardware_scope=result['hardware_scope'] + ', PM6150 Type-C role switch and USB host',
                      usb_host_confirmed=False)
    if profile in ('wifi1', 'wifi2', 'wifi3', 'bt1', 'battery1', 'battery2', 'reboot1', 'audio1', 'audio2', 'audio3', 'audio4', 'audio5', 'audio6', 'audio7', 'audio8', 'audio9', 'audio10', 'audio11', 'audio12', 'audio13', 'audio14', 'gpu1', 'gpu2', 'vulkan1', 'modem1', 'sdexport1'):
        result.update(hardware_scope=result['hardware_scope'] +
                      ', MPSS and WCN3990 Wi-Fi with read-only RAM-shadow rmtfs and read-only modem BDF copy',
                      wifi_confirmed=False)
    if profile in ('wifi2', 'wifi3', 'bt1', 'battery1', 'battery2', 'reboot1', 'audio1', 'audio2', 'audio3', 'audio4', 'audio5', 'audio6', 'audio7', 'audio8', 'audio9', 'audio10', 'audio11', 'audio12', 'audio13', 'audio14', 'gpu1', 'gpu2', 'vulkan1', 'modem1', 'sdexport1'):
        result.update(hardware_scope=result['hardware_scope'] + ', WPA3-SAE association typed on the device console',
                      wifi_association_confirmed=False)
    if profile in ('bt1', 'battery1', 'battery2', 'reboot1', 'audio1', 'audio2', 'audio3', 'audio4', 'audio5', 'audio6', 'audio7', 'audio8', 'audio9', 'audio10', 'audio11', 'audio12', 'audio13', 'audio14', 'gpu1', 'gpu2', 'vulkan1', 'modem1', 'sdexport1', 'lineage1'):
        result.update(hardware_scope=result['hardware_scope'] + ', WCN3991 Bluetooth over UART3 with a temporary address',
                      bluetooth_confirmed=False)
    if profile in ('audio1', 'audio2', 'audio3', 'audio4', 'audio5', 'audio6', 'audio7', 'audio8', 'audio9', 'audio10', 'audio11', 'audio12', 'audio13', 'audio14', 'gpu1', 'gpu2', 'vulkan1', 'modem1', 'sdexport1', 'lineage1'):
        for symbol in ('QCOM_Q6V5_PAS', 'QCOM_APR', 'SND_SOC_QDSP6', 'SND_SOC_SM8250', 'SND_SOC_TAS2562',
                       'SND_SOC_WCD937X', 'SND_SOC_WCD937X_SDW', 'SND_SOC_LPASS_RX_MACRO',
                       'SND_SOC_LPASS_TX_MACRO', 'SND_SOC_LPASS_VA_MACRO', 'SOUNDWIRE_QCOM', 'I2C_QCOM_GENI'):
            require('CONFIG_' + symbol + '=y\n' in config, 'Missing audio built-in: ' + symbol)
        for node in ('/soc@0/remoteproc@62400000', '/sound', '/soc@0/geniqup@ac0000/i2c@a8c000/codec@4c'):
            available(dtb, node)
        require(fdt(dtb, '/soc@0/remoteproc@62400000', 'firmware-name') == 'qcom/sm7125/miatoll/adsp.mbn',
                'Unexpected ADSP firmware name')
        result.update(hardware_scope=result['hardware_scope'] + ', native ADSP audio card (TAS2562 speaker, WCD937x)',
                      audio_confirmed=False)
    if profile in ('battery1', 'battery2', 'reboot1', 'audio1', 'audio2', 'audio3', 'audio4', 'audio5', 'audio6', 'audio7', 'audio8', 'audio9', 'audio10', 'audio11', 'audio12', 'audio13', 'audio14', 'gpu1', 'gpu2', 'vulkan1', 'modem1', 'sdexport1', 'lineage1'):
        for symbol in ('BATTERY_QCOM_QG', 'NVMEM_SPMI_SDAM', 'QCOM_SPMI_ADC5'):
            require('CONFIG_' + symbol + '=y\n' in config, 'Missing battery built-in: ' + symbol)
        available(dtb, '/soc@0/spmi@c440000/pmic@0/qgauge@4800')
        result.update(hardware_scope=result['hardware_scope'] + ', read-only PM6150 QG battery telemetry',
                      battery_telemetry_confirmed=False)
    result['packaging_source_commit'] = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    checked_sources = [*BOOT.glob('*.py'), *BOOT.glob('*.ps1'), *BOOT.glob('shim/*'),
                       *(BOOT / name for name in ('init', 'boot-probe', 'usb-gadget', 'display-banner', 'display-probe',
                                                  'touch-probe', 'touch-events', 'storage-probe',
                                                  'usb-host-watch', 'wifi-start', 'wifi-services', 'wifi-board',
                                                  'wifi-probe', 'wifi-scan', 'wifi-join', 'wifi-udhcpc',
                                                  'wifi-link-probe', 'wifi-disconnect', 'bt-start', 'bt-probe',
                                                  'battery-probe', 'fastboot-reboot', 'reboot-mode.c',
                                                  'audio-init', 'audio-probe', 'speaker-tone.c', 'audio-path', 'pcm-test.c', 'gpu-probe.c', 'modem-query', 'sd-export')),
                       ROOT / ('arch/arm64/boot/dts/qcom/sm7125-xiaomi-curtana-' + profile + '.dts'),
                       ROOT / 'arch/arm64/boot/dts/qcom/sm7125-xiaomi-curtana-modem1.dts',
                       ROOT / 'arch/arm64/boot/dts/qcom/sm7125-xiaomi-curtana-vulkan1.dts',
                       ROOT / 'arch/arm64/boot/dts/qcom/sm7125-xiaomi-curtana-gpu2.dts',
                       ROOT / 'arch/arm64/boot/dts/qcom/sm7125-xiaomi-curtana-gpu1.dts',
                       ROOT / 'arch/arm64/boot/dts/qcom/sm7125-xiaomi-curtana-audio7.dts',
                       ROOT / 'arch/arm64/boot/dts/qcom/sm7125-xiaomi-curtana-audio13.dts',
                       ROOT / 'arch/arm64/boot/dts/qcom/sm7125-xiaomi-curtana-audio12.dts',
                       ROOT / 'arch/arm64/boot/dts/qcom/sm7125-xiaomi-curtana-audio11.dts',
                       ROOT / 'arch/arm64/boot/dts/qcom/sm7125-xiaomi-curtana-audio10.dts',
                       ROOT / 'arch/arm64/boot/dts/qcom/sm7125-xiaomi-curtana-audio9.dts',
                       ROOT / 'arch/arm64/boot/dts/qcom/sm7125-xiaomi-curtana-audio5.dts',
                       ROOT / 'arch/arm64/boot/dts/qcom/sm7125-xiaomi-curtana-audio4.dts',
                       ROOT / 'arch/arm64/boot/dts/qcom/sm7125-xiaomi-curtana-audio3.dts',
                       ROOT / 'arch/arm64/boot/dts/qcom/sm7125-xiaomi-curtana-audio2.dts',
                       ROOT / 'arch/arm64/boot/dts/qcom/sm7125-xiaomi-curtana-audio1.dts',
                       ROOT / 'arch/arm64/boot/dts/qcom/sm7125-xiaomi-curtana-reboot1.dts',
                       ROOT / 'arch/arm64/boot/dts/qcom/sm7125-xiaomi-curtana-battery2.dts',
                       ROOT / 'arch/arm64/boot/dts/qcom/sm7125-xiaomi-curtana-battery1.dts',
                       ROOT / 'arch/arm64/boot/dts/qcom/sm7125-xiaomi-curtana-bt1.dts',
                       ROOT / 'arch/arm64/boot/dts/qcom/sm7125-xiaomi-curtana-wifi3.dts',
                       ROOT / 'arch/arm64/boot/dts/qcom/sm7125-xiaomi-curtana-wifi2.dts',
                       ROOT / 'arch/arm64/boot/dts/qcom/sm7125-xiaomi-curtana-wifi1.dts',
                       ROOT / 'arch/arm64/boot/dts/qcom/sm7125-xiaomi-curtana-usb2.dts',
                       ROOT / 'arch/arm64/boot/dts/qcom/sm7125-xiaomi-curtana-storage1.dts',
                       ROOT / 'arch/arm64/boot/dts/qcom/sm7125-xiaomi-curtana-touch1.dts',
                       ROOT / 'arch/arm64/boot/dts/qcom/sm7125-xiaomi-curtana-display2.dts',
                       ROOT / 'arch/arm64/boot/dts/qcom/sm7125-xiaomi-curtana-display1.dts',
                       ROOT / 'arch/arm64/boot/dts/qcom/sm7125-xiaomi-curtana-boot1.dts',
                       ROOT / ('miatoll/configs/' + profile + '.config'), ROOT / 'miatoll/configs/miatoll.config']
    result['packaging_sources'] = {str(path.relative_to(ROOT)): digest(path.read_bytes())
                                    for path in checked_sources if path.is_file()}
    (DIST / (profile + '-report.json')).write_text(json.dumps(result, indent=2) + '\n')
    shutil.copy2(BOOT / 'Test-Boot1.ps1', DIST / 'Test-Boot1.ps1')
    launcher = BOOT / ('Test-' + profile.capitalize() + '.ps1')
    if profile != 'boot1' and launcher.exists():
        shutil.copy2(launcher, DIST / launcher.name)
    print(json.dumps({key: value for key, value in result.items() if key != 'ramdisk'}, indent=2))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', choices=PROFILES, default='boot1')
    parser.add_argument('--android-ramdisk', help='LineageOS first-stage ramdisk.img for lineage1')
    arguments = parser.parse_args()
    main(arguments.profile, arguments.android_ramdisk)
