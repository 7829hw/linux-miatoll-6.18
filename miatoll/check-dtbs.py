#!/usr/bin/env python3
"""Check enabled DT ancestry and panel/touch links; this is not a schema test."""
import json
import os
from pathlib import Path, PurePosixPath
import subprocess

root = Path(__file__).resolve().parents[1]
workspace = root.parent
host = workspace / "tools/host-build"
fdtget = host / "usr/bin/fdtget"
environment = dict(os.environ)
environment["LD_LIBRARY_PATH"] = str(host / "usr/lib/x86_64-linux-gnu")

def read(dtb, node, prop, kind="s"):
    return subprocess.check_output(
        [str(fdtget), "-t", kind, str(dtb), node, prop],
        text=True, env=environment).strip()

def available(dtb, node):
    path = PurePosixPath(node)
    statuses = []
    for parent in (*reversed(path.parents), path):
        properties = subprocess.check_output(
            [str(fdtget), "-p", str(dtb), str(parent)],
            text=True, env=environment).splitlines()
        status = read(dtb, str(parent), "status") if "status" in properties else "okay"
        assert status in ("okay", "ok"), (dtb.name, str(parent), status)
        statuses.append({"path": str(parent), "status": status})
    return statuses

results = []
for board in ("curtana", "joyeuse"):
    for variant, panel_compatible, touch_compatible in (
        ("huaxing", "huaxing,ft8756", "focaltech,ft8756-spi"),
        ("tianma", "tianma,nt36675", "novatek,nt36xxx-spi"),
    ):
        dtb = workspace / f"dist/miatoll-6.18/dtbs/sm7125-xiaomi-{board}-{variant}.dtb"
        assert f"xiaomi,{board}" in read(dtb, "/", "compatible").split()
        mdss = "/soc@0/display-subsystem@ae00000"
        panel = mdss + "/dsi@ae94000/panel@0"
        touch = "/soc@0/geniqup@ac0000/spi@a94000/touchscreen@0"
        assert read(dtb, panel, "compatible") == panel_compatible
        assert read(dtb, touch, "compatible") == touch_compatible
        assert read(dtb, touch, "panel", "x") == read(dtb, panel, "phandle", "x")
        endpoint_in = panel + "/port/endpoint"
        endpoint_out = mdss + "/dsi@ae94000/ports/port@1/endpoint"
        assert read(dtb, endpoint_in, "remote-endpoint", "x") == read(dtb, endpoint_out, "phandle", "x")
        assert read(dtb, endpoint_out, "remote-endpoint", "x") == read(dtb, endpoint_in, "phandle", "x")
        nodes = [panel, touch, "/soc@0/gpu@5000000", "/soc@0/camss@acb3000",
                 "/soc@0/cci@ac4a000", "/soc@0/cci@ac4b000", "/sound"]
        results.append({"dtb": dtb.name, "panel": panel_compatible,
                        "touch": touch_compatible,
                        "ancestry": {node: available(dtb, node) for node in nodes}})
print(json.dumps({"passed": True, "profiles": results}, indent=2))
