# -*- coding: utf-8 -*-
"""串口取证：枚举所有 COM 口 -> 复位板子让它自己打印启动日志 -> 抓每个口的输出。"""
import subprocess
import sys
import threading
import time

import serial
from serial.tools import list_ports


def ports():
    return [(p.device, p.description, p.hwid) for p in list_ports.comports()]


def cmd_list():
    for d, desc, hwid in ports():
        print(f"  {d:10s} {desc:40s} {hwid}")
    return 0


def do_reset():
    try:
        r = subprocess.run(["pyocd", "reset", "-t", "r7ka8p1kf"],
                           capture_output=True, text=True, timeout=30)
        print("  pyocd reset:", (r.stdout or r.stderr).strip()[:140])
        return True
    except Exception as e:
        print("  pyocd reset failed:", e)
        return False


def grab(secs=9.0, baud=115200, reset=False):
    results = {}
    opened = []
    threads = []

    def rd(dev, ser, secs):
        buf = b""
        end = time.time() + secs
        while time.time() < end:
            try:
                n = ser.in_waiting
                if n:
                    buf += ser.read(n)
                else:
                    time.sleep(0.01)
            except Exception:
                break
        results[dev] = buf

    for dev, desc, _ in ports():
        try:
            opened.append((dev, serial.Serial(dev, baud, timeout=0.1)))
        except Exception as e:
            results[dev] = ("<open failed> " + str(e)).encode()

    for dev, ser in opened:
        t = threading.Thread(target=rd, args=(dev, ser, secs), daemon=True)
        t.start()
        threads.append((t, ser))

    time.sleep(0.5)
    if reset:
        do_reset()

    for t, ser in threads:
        t.join()
        try:
            ser.close()
        except Exception:
            pass

    tag = "after reset" if reset else "passive"
    print(f"--- {tag}, {secs:.0f}s @ {baud} ---")
    total = 0
    for dev, _ in [(d, None) for d, _, _ in ports()]:
        data = results.get(dev, b"")
        total += len(data)
        print(f"  {dev:10s} {len(data):5d} bytes  {data[:120]!r}")
    print(f"  TOTAL {total} bytes")
    return total


def poke(port, baud):
    ser = serial.Serial(port, baud, timeout=0.2)
    time.sleep(0.3)
    ser.reset_input_buffer()
    for cmd in (b"\r\n", b"version\r\n", b"help\r\n", b"ps\r\n"):
        ser.write(cmd)
        time.sleep(0.6)
        n = ser.in_waiting
        if n:
            data = ser.read(n)
            print(f"  [{port} @{baud}] got {len(data)} B: {data[:250]!r}")
            ser.close()
            return True
    print(f"  [{port} @{baud}] nothing")
    ser.close()
    return False


def main():
    a = sys.argv[1] if len(sys.argv) > 1 else "list"

    if a == "list":
        return cmd_list()
    if a == "listen":
        secs = float(sys.argv[2]) if len(sys.argv) > 2 else 6.0
        grab(secs, 115200, False)
        grab(secs, 9600, False)
        return 0
    if a == "reset":
        secs = float(sys.argv[2]) if len(sys.argv) > 2 else 9.0
        grab(secs, 115200, True)
        return 0
    if a == "poke":
        ok = False
        for b in (115200, 9600, 921600):
            if poke(sys.argv[2], b):
                ok = True
                break
        return 0 if ok else 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
