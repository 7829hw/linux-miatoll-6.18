#!/usr/bin/env python3
"""Verify compiled ARM64 artifacts without accessing a device."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess

root = Path(__file__).resolve().parents[1]
workspace = root.parent
dist = workspace / "dist/miatoll-6.18"
out = workspace / "out-miatoll-6.18"
release = (dist / "kernelrelease.txt").read_text().strip()
image = (dist / "Image").read_bytes()
assert image[56:60] == b"ARM\x64", "Invalid ARM64 Image header"
runtime_size = struct.unpack_from("<Q", image, 16)[0]
assert runtime_size >= len(image)
modules = sorted((dist / "modules").rglob("*.ko"))
expected_count = len((out / "modules.order").read_text().splitlines())
assert len(modules) == expected_count, (len(modules), expected_count)
for module in modules:
    data = module.read_bytes()
    assert data[:5] == b"\x7fELF\x02", module
    assert data[5] == 1 and struct.unpack_from("<H", data, 18)[0] == 183, module
    assert b"vermagic=" + release.encode() + b" " in data, module
dtbs = sorted((dist / "dtbs").glob("*.dtb"))
assert len(dtbs) == 4
for dtb in dtbs:
    assert struct.unpack_from(">I", dtb.read_bytes())[0] == 0xD00DFEED, dtb
subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor", "v6.18.58", "HEAD"], check=True)
subprocess.run(["git", "-C", str(root), "diff", "--quiet", "v6.18.58", "--", "Makefile"], check=True)
code_paths = ["arch", "drivers", "sound", "fs", "include", "kernel", "security",
              "block", "mm", "ipc", "net", "scripts", "lib", "Makefile", "Kconfig",
              "miatoll/build.sh", "miatoll/configs"]
clean = subprocess.run(["git", "-C", str(root), "diff", "--quiet", "HEAD", "--", *code_paths]).returncode == 0
def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()
result = {
    "passed": True,
    "source_commit": subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip(),
    "kernel_source_and_config_clean": clean,
    "official_base": "v6.18.58",
    "official_makefile_unchanged": True,
    "kernelrelease": release,
    "image_bytes": len(image),
    "image_sha256": digest(dist / "Image"),
    "image_runtime_bytes": runtime_size,
    "previous_downstream_runtime_reference_bytes": 40615936,
    "module_count": len(modules),
    "all_modules_aarch64_and_matching_vermagic": True,
    "dtbs": [{"name": p.name, "bytes": p.stat().st_size, "sha256": digest(p)} for p in dtbs],
    "device_runtime_tested": False,
    "lineageos_boot_tested": False,
    "dt_schema_validation_performed": False,
}
print(json.dumps(result, indent=2))
