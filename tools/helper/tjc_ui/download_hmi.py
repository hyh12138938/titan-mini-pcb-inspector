#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
download_hmi.py - flash a .HMI project into the panel over the HMI download
protocol published at wiki.tjc1688.com/advanced/hmi_download_protocol.html

    step 1  connect        00 FF FF FF + "connect" FF FF FF
            reply          comok 1,addr,model,ver,chip,serial,flashsize FF FF FF
    step 2  whmi-wri <size>,<baud>,0 FF FF FF
            reply          0x05 (single byte, ~250 ms later) at the new baud
    step 3  send the file in 4096-byte chunks; each chunk answered by 0x05

Usage:
    python download_hmi.py COM5 demo_draw.HMI --baud 460800
    python download_hmi.py COM5 demo_draw.HMI --baud 115200 --dry-run
"""
import argparse
import os
import sys
import time

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    print("need pyserial:  pip install pyserial")
    sys.exit(2)

TERM = b"\xff\xff\xff"
CHUNK = 4096


def open_port(dev, baud):
    s = serial.Serial(dev, baud, timeout=0.25, write_timeout=5.0)
    time.sleep(0.15)
    s.reset_input_buffer()
    return s


def read_until(s, sec=1.0, want=None):
    buf = b""
    end = time.time() + sec
    while time.time() < end:
        n = s.in_waiting
        if n:
            buf += s.read(n)
            if want and want in buf:
                break
        else:
            time.sleep(0.01)
    return buf


def connect(s, baud):
    """returns the comok line, or None"""
    wait = 1000000.0 / baud + 30
    for _ in range(3):
        s.write(b"\x00" + TERM)          # flush whatever partial junk is pending
        time.sleep(0.03)
        s.write(b"connect" + TERM)
        got = read_until(s, max(0.35, wait / 1000.0 * 3), want=b"comok")
        if b"comok" in got:
            m = got[got.find(b"comok"):]
            m = m.split(b"\xff")[0]
            return m.decode("ascii", "replace")
        time.sleep(0.2)
    return None


def flash(dev, path, baud, dry_run=False):
    size = os.path.getsize(path)
    print(f"file   : {path}  ({size:,} bytes)")
    print(f"port   : {dev}   download baud: {baud}")

    s = open_port(dev, 115200 if baud != 115200 else baud)
    # step 1: connect at the panel's *current* baud. Try the common ones.
    info = None
    for cur in (115200, 9600, 460800, 57600, 38400):
        s.baudrate = cur
        time.sleep(0.1)
        s.reset_input_buffer()
        info = connect(s, cur)
        if info:
            print(f"linked : {cur} baud")
            break
        print(f"  no answer at {cur}")
    if not info:
        print("FAILED: panel did not answer `connect` on any baud")
        print("  - is the USB-TTL RX on the panel TX and TX on the panel RX?")
        print("  - DIP switch ON (TTL)?  GND common?  panel powered?")
        s.close()
        return 1
    print(f"panel  : {info}")

    if dry_run:
        print("dry run: stopping before erase")
        s.close()
        return 0

    # step 2: whmi-wri
    # the comok reply leaves a tail in the buffer; drain it, then let the
    # panel settle.  No flush bytes here: a stray 00 FF FF FF right before the
    # instruction leaves the parser mid-frame and the panel never answers.
    time.sleep(0.6)
    s.reset_input_buffer()

    print(f"sending whmi-wri {size},{baud},0")
    s.write(f"whmi-wri {size},{baud},0".encode() + TERM)
    s.flush()

    # The panel answers ~250 ms later.  Some firmwares answer at the NEW baud,
    # some stay on the old one; accept either.
    pre = read_until(s, 2.0, want=b"\x05")
    print(f"  old-baud window: {len(pre)} bytes {'(0x05!)' if b'\x05' in pre else ''}")
    s.baudrate = baud
    time.sleep(0.15)
    post = read_until(s, 6.0, want=b"\x05")
    print(f"  new-baud window: {len(post)} bytes {'(0x05!)' if b'\x05' in post else ''}")
    if b"\x05" not in pre and b"\x05" not in post:
        print(f"FAILED: no 0x05 after whmi-wri (pre {pre[:16].hex(' ')} post {post[:16].hex(' ')})")
        s.baudrate = 9600
        s.close()
        return 2
    print("panel ready, streaming ...")

    # step 3: chunks
    sent = 0
    t0 = time.time()
    with open(path, "rb") as f:
        while sent < size:
            chunk = f.read(CHUNK)
            if not chunk:
                break
            for attempt in range(4):
                s.write(chunk)
                s.flush()
                ack = read_until(s, 2.0, want=b"\x05")
                if b"\x05" in ack:
                    break
            else:
                print(f"\nFAILED: no ack at offset {sent:,}")
                s.close()
                return 3
            sent += len(chunk)
            if (sent // CHUNK) % 50 == 0 or sent >= size:
                pct = sent * 100 // size
                el = time.time() - t0
                rate = sent / el / 1024 if el else 0
                print(f"\r  {sent:,}/{size:,} ({pct}%)  {rate:.0f} KB/s   ", end="", flush=True)
    print()
    print(f"done in {time.time()-t0:.1f}s")
    time.sleep(0.5)
    tail = read_until(s, 1.0)
    if tail:
        print("trailing:", tail[:32].hex(" "))
    s.close()
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("port", help="e.g. COM5")
    ap.add_argument("file", help="path to .HMI")
    ap.add_argument("--baud", type=int, default=460800, help="download baud (default 460800)")
    ap.add_argument("--dry-run", action="store_true", help="connect and stop before erasing")
    a = ap.parse_args()

    if not os.path.exists(a.file):
        print("no such file:", a.file)
        return 1
    if not a.port:
        print("ports:", [(p.device, p.description) for p in list_ports.comports()])
        return 1
    return flash(a.port, a.file, a.baud, a.dry_run)


if __name__ == "__main__":
    sys.exit(main())
