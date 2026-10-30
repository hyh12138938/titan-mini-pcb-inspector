# -*- coding: utf-8 -*-
"""读 uart_obj[0] 原始内存，找 ra_uart_ops(0x0201C89C) 指针，判断 ops 是否为 NULL"""
import sys
import struct

from pyocd.core.helpers import ConnectHelper

UART_OBJ = 0x220208B8
SIZE = 0x110
OPS = 0x0201C89C


def main():
    with ConnectHelper.session_with_chosen_probe(target_override="r7ka8p1kf") as s:
        t = s.target
        t.halt()
        data = bytes(t.read_memory_block8(UART_OBJ, SIZE))
        print(f"uart_obj @0x{UART_OBJ:08X}  {SIZE} bytes")
        print("first 8 bytes (name):", data[:8].split(b"\x00")[0].decode("ascii", "replace"))

        found = None
        for off in range(0, SIZE - 4, 4):
            v = struct.unpack_from("<I", data, off)[0]
            if v == OPS:
                found = off
                break
        print(f"ra_uart_ops pointer found at offset: {found}")

        # 打印前 96 字节，每 16 字节一行
        print("--- dump (offset: hex) ---")
        for off in range(0, min(SIZE, 128), 16):
            chunk = data[off:off + 16]
            print(f"  +0x{off:03X}: {chunk.hex(' ')}")
        t.resume()
    return 0


if __name__ == "__main__":
    sys.exit(main())
