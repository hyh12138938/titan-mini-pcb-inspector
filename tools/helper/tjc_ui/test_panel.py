#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_panel.py - talk to the TJC panel directly from the PC, before any board.

Why this step exists: if you wire the panel straight to the board and nothing
shows up, you cannot tell whether the panel, the wiring, the baud rate or the
firmware is at fault.  Twenty seconds with this script splits that in half.

Hook up the USB-TTL adapter (the CH340 that normally goes to the board) like:

    CH340 5V   ->  panel 5V        (or use a separate 5V/1A supply)
    CH340 GND  ->  panel GND
    CH340 TX   ->  panel RX
    CH340 RX   ->  panel TX

Panel DIP switch must be ON (= TTL).  OFF is RS232 and will damage pins.

Usage:
    python test_panel.py COM7
    python test_panel.py COM7 --draw        # also draw a test card
    python test_panel.py COM7 --baud 9600   # force a baud instead of probing
"""
import sys
import time

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    print("pyserial missing:  pip install pyserial")
    sys.exit(2)

TERM = b"\xff\xff\xff"


def open_port(port, baud):
    return serial.Serial(port, baud, timeout=0.3, write_timeout=1.0)


def drain(ser, seconds=0.4):
    end = time.time() + seconds
    buf = b""
    while time.time() < end:
        n = ser.in_waiting
        if n:
            buf += ser.read(n)
        else:
            time.sleep(0.02)
    return buf


def cmd(ser, s, note=""):
    ser.write(s.encode("ascii") + TERM)
    ser.flush()
    time.sleep(0.12)
    if note:
        print(f"    -> {note}")


def probe(port):
    """The panel ships at 9600. Try 9600 first: if it answers there we also flip
    it to 115200 the same way the firmware does."""
    print(f"[1] opening {port} @9600 (factory default)")
    ser = open_port(port, 9600)
    drain(ser, 0.3)
    ser.write(b"\x00" + TERM)          # terminate any junk it booted with
    time.sleep(0.15)

    ser.write(b"baud=115200" + TERM)   # runtime switch, not stored
    time.sleep(0.3)
    ser.close()

    print("[2] reopening @115200")
    ser = open_port(port, 115200)
    drain(ser, 0.3)
    ser.write(b"\x00" + TERM)
    time.sleep(0.15)

    # a harmless query the panel answers on 0x71 / 0x70
    ser.write(b"sendme" + TERM)
    time.sleep(0.25)
    got = drain(ser, 0.5)
    print(f"    reply to 'sendme': {got.hex(' ') if got else '(none)'}")
    return ser, got


def draw_card(ser):
    print("[3] drawing a test card")
    cmd(ser, "cls", "screen should go black")
    time.sleep(0.2)
    cmd(ser, "fill 0,0,1024,120,2146", "top bar (dark blue)")
    cmd(ser, "fill 40,160,944,3,65280", "a yellow rule")
    cmd(ser, "draw 40,200,400,120,65535", "white outline box")
    cmd(ser, "fill 40,340,300,80,2016", "green block")
    cmd(ser, "fill 360,340,300,80,63488", "red block")
    for i, (y, txt) in enumerate([
        (30, "PANEL TEST"),
        (150, "if you can read this the wiring is right"),
        (225, "box = draw"),
        (370, "green"),
        (470, "TJC1060X570 / 1024x600"),
    ]):
        cmd(ser, f'xstr 60,{y},900,40,1,65535,0,0,0,3,"{txt}"')
    print("    done - look at the panel")


def main():
    if len(sys.argv) < 2:
        print("ports:")
        for p in list_ports.comports():
            print(f"  {p.device}  {p.description}")
        print("\nusage: python test_panel.py COM7 [--draw] [--baud N]")
        return 1

    port = sys.argv[1]
    force_baud = None
    if "--baud" in sys.argv:
        force_baud = int(sys.argv[sys.argv.index("--baud") + 1])

    try:
        if force_baud:
            print(f"opening {port} @{force_baud}")
            ser = open_port(port, force_baud)
            drain(ser, 0.3)
            ser.write(b"\x00" + TERM)
            time.sleep(0.2)
            got = b""
        else:
            ser, got = probe(port)
    except serial.SerialException as e:
        print(f"\nCANNOT OPEN {port}: {e}")
        print("  - is the board still holding it? unplug the board's USB")
        print("  - wrong COM? run this script with no arguments to list ports")
        return 2

    if "--draw" in sys.argv:
        draw_card(ser)
    else:
        print("[3] sending cls (screen should go black)")
        cmd(ser, "cls")
        print("[3] sending fill 0,0,200,200,2016 (a green square, top-left)")
        cmd(ser, "fill 0,0,200,200,2016")

    ser.close()
    print("\n如果屏有变化 -> 屏、接线、电平、波特率都没问题，问题只会出在固件侧")
    print("如果屏完全没反应 -> 先查拨码 ON(TTL)、GND 是否共地、5V 是否有电")
    return 0


if __name__ == "__main__":
    sys.exit(main())
