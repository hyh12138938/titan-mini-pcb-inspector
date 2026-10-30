# -*- coding: utf-8 -*-
"""同时读两块帧缓冲 + 校验运行固件与 ELF 是否一致"""
import struct
import sys

import numpy as np
from pyocd.core.helpers import ConnectHelper
from PIL import Image

FB0 = 0x68096080
PLANE = 800 * 480 * 2          # 768000
HAL_ENTRY = 0x02012750
ELF = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\project\Titan_Mini_pad_inspect\rtthread.elf"


def to_png(raw, path):
    a = np.frombuffer(raw, dtype="<u2").reshape(480, 800)
    r = ((a >> 11) & 0x1F) * 255 // 31
    g = ((a >> 5) & 0x3F) * 255 // 63
    b = (a & 0x1F) * 255 // 31
    Image.fromarray(np.dstack([r, g, b]).astype(np.uint8), "RGB").save(path)
    lum = np.asarray(Image.open(path).convert("L"), dtype=np.float32)
    return lum.mean(), lum.max(), len(np.unique(a))


def elf_bytes_at(vaddr, n):
    # 用 arm-none-eabi-objcopy 抽段太麻烦，直接按 elf 的 text 偏移读：用 readelf 查
    import subprocess
    readelf = r"D:\tools\arm-gnu-toolchain-13.3.rel1-mingw-w64-i686-arm-none-eabi\bin\arm-none-eabi-readelf.exe"
    out = subprocess.run([readelf, "-S", "-W", ELF], capture_output=True, text=True).stdout
    for line in out.splitlines():
        if ".text" in line and "PROGBITS" in line:
            f = line.split()
            # 形如: [ 1] .text PROGBITS addr off size ...
            i = f.index("PROGBITS")
            addr = int(f[i + 1], 16); off = int(f[i + 2], 16); size = int(f[i + 3], 16)
            if addr <= vaddr < addr + size:
                with open(ELF, "rb") as fh:
                    fh.seek(off + (vaddr - addr))
                    return fh.read(n)
    return None


def main():
    want = elf_bytes_at(HAL_ENTRY, 8)
    with ConnectHelper.session_with_chosen_probe(target_override="r7ka8p1kf") as s:
        t = s.target
        t.halt()
        got = bytes(t.read_memory_block8(HAL_ENTRY, 8))
        print(f"ELF  hal_entry[0:8] = {want.hex(' ') if want else '?'}")
        print(f"目标 hal_entry[0:8] = {got.hex(' ')}")
        print(f"固件一致: {want == got}")

        for name, addr in (("plane0", FB0), ("plane1", FB0 + PLANE)):
            raw = bytes(t.read_memory_block8(addr, PLANE))
            out = rf"D:\RTT\_re\shots\{name}.png"
            m, mx, u = to_png(raw, out)
            print(f"  {name} @0x{addr:08X}: 平均={m:6.2f} 最亮={mx:3.0f} 色数={u:5d}  -> {out}")
        t.resume()
    return 0


if __name__ == "__main__":
    sys.exit(main())
