"""Pinned AW8624 waveform library for the lineage1 RAMdisk.

aw8624_haptic.bin is the vendor SRAM waveform library of the Xiaomi sm6250
devices, git blob bd3cf04d in TheMuppets proprietary_vendor_xiaomi_sm6250-common
lineage-22.2 (b93a6532, vendor/firmware/aw8624_haptic.bin). The aw8695-haptics
driver loads it at probe, before Android mounts /vendor.
"""
import hashlib
from pathlib import Path

NAME = 'aw8624_haptic.bin'
SHA256 = '51dff3f76b1cf631f3b88f28c88d0d6f0790585483b69758252b71bce39d99e0'


def load_haptics_firmware(root):
    data = (Path(root) / 'downloads' / 'haptics-firmware' / NAME).read_bytes()
    if len(data) != 3729 or hashlib.sha256(data).hexdigest() != SHA256:
        raise ValueError('Haptics waveform library differs from pinned input')
    if sum(data[2:]) & 0xffff != int.from_bytes(data[:2], 'big'):
        raise ValueError('Haptics waveform library checksum mismatch')
    return {'lib/firmware/' + NAME: data}
