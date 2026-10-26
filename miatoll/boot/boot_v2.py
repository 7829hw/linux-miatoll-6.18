"""Read Android v2 headers and validate their component SHA1 ID."""
import hashlib
import struct

def require(condition, message):
    if not condition:
        raise ValueError(message)

def digest(data):
    return hashlib.sha256(data).hexdigest()

def parse_boot(data):
    require(len(data) >= 1660 and data[:8] == b'ANDROID!', 'Invalid boot header')
    keys = ('kernel_size', 'kernel_addr', 'ramdisk_size', 'ramdisk_addr',
            'second_size', 'second_addr', 'tags_addr', 'page_size',
            'header_version', 'os_version_raw')
    header = dict(zip(keys, struct.unpack_from('<10I', data, 8)))
    require(header['header_version'] == 2 and header['page_size'] == 4096,
            'Expected curtana v2/4096 header')
    header['board'] = data[48:64].split(b'\0', 1)[0].decode('ascii')
    header['cmdline'] = (data[64:576].split(b'\0', 1)[0] +
                         data[608:1632].split(b'\0', 1)[0]).decode('ascii')
    header['recovery_dtbo_size'], header['recovery_dtbo_offset'], header['header_size'] = struct.unpack_from('<IQI', data, 1632)
    header['dtb_size'], header['dtb_addr'] = struct.unpack_from('<IQ', data, 1648)
    require(header['header_size'] == 1660, 'Invalid v2 header size')
    require(header['kernel_size'] > 0 and header['dtb_size'] > 0, 'Empty kernel/DTB')
    offset = header['page_size']
    parts = {}
    image_id = hashlib.sha1()
    for name in ('kernel', 'ramdisk', 'second', 'recovery_dtbo', 'dtb'):
        size = header[name + '_size']
        require(offset + size <= len(data), 'Truncated ' + name)
        if name == 'recovery_dtbo' and size:
            require(header['recovery_dtbo_offset'] == offset, 'Invalid DTBO offset')
        parts[name] = data[offset:offset + size]
        image_id.update(parts[name])
        image_id.update(struct.pack('<I', size))
        offset = (offset + size + header['page_size'] - 1) // header['page_size'] * header['page_size']
    require(offset <= len(data), 'Truncated padding')
    require(data[576:596] == image_id.digest(), 'Invalid v2 SHA1 component ID')
    header['payload_end'] = offset
    version = header['os_version_raw'] >> 11
    header['os_version'] = f'{version >> 14}.{(version >> 7) & 127}.{version & 127}'
    patch = header['os_version_raw'] & 2047
    header['os_patch_level'] = f'{(patch >> 4) + 2000}-{patch & 15:02d}-01'
    return header, parts
