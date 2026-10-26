#!/usr/bin/env python3
"""Compare the 64-bit Binder UAPI used by the vendor and this kernel.

This checks layout and ioctl numbers with the host compiler. It does not
exercise the kernel Binder driver or prove Android service compatibility.
"""
import json
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
headers = {
    "vendor_4_14": root / "miatoll/reference/vendor-4.14/include/uapi/linux/android/binder.h",
    "upstream_6_18": root / "include/uapi/linux/android/binder.h",
}
results = {}
with tempfile.TemporaryDirectory(prefix="miatoll-binder-") as directory:
    work = Path(directory)
    for name, header in headers.items():
        source = work / f"{name}.c"
        binary = work / name
        source.write_text(
            "#include <stdio.h>\n#include <stddef.h>\n#include <sys/types.h>\n"
            f"#include {json.dumps(str(header))}\n"
            "_Static_assert(sizeof(void *) == 8, \"64-bit host required\");\n"
            "int main(void) {\n"
            'printf("%u %zu %zu %zu %lu %lu %lu %lu\\n",\n'
            "BINDER_CURRENT_PROTOCOL_VERSION, sizeof(struct binder_transaction_data),\n"
            "sizeof(struct binder_write_read), offsetof(struct binder_transaction_data, data),\n"
            "(unsigned long)BINDER_WRITE_READ, (unsigned long)BINDER_VERSION,\n"
            "(unsigned long)BC_TRANSACTION, (unsigned long)BC_TRANSACTION_SG);\n"
            "return 0;\n}\n"
        )
        subprocess.run(["cc", "-Wall", "-Werror", str(source), "-o", str(binary)], check=True)
        values = list(map(int, subprocess.check_output([str(binary)], text=True).split()))
        fields = ["protocol", "transaction_size", "write_read_size", "transaction_data_offset",
                  "BINDER_WRITE_READ", "BINDER_VERSION", "BC_TRANSACTION", "BC_TRANSACTION_SG"]
        results[name] = dict(zip(fields, values))
results["match"] = results["vendor_4_14"] == results["upstream_6_18"]
print(json.dumps(results, indent=2))
raise SystemExit(0 if results["match"] else 1)
