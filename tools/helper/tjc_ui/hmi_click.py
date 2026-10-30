#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""hmi_click.py - click inside the USART HMI window, bringing it to the front first.

The IDE is a plain Win32 app: it does not expose UI Automation, so the only way
to drive it is pixel clicks.  Every click must therefore be preceded by a
SetForegroundWindow, otherwise the click lands on whatever window happens to be
on top (which is how a stray click ended up in another app).

Coordinate convention used everywhere in this project:
    screenshots are 2560x1600 but the preview shown to the model is 1610x1006,
    so a coordinate measured on the preview must be multiplied by 2560/1610.
    SCALE converts preview -> real; click_r() takes real coordinates.
"""
import ctypes
import sys
import time

import pyautogui

user32 = ctypes.windll.user32
SCALE = 2560 / 1610.0

TITLE_HINT = "USART HMI"


def find_hmi():
    found = []
    EnumProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_void_p)

    def cb(hwnd, lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        n = user32.GetWindowTextLengthW(hwnd)
        if n:
            buf = ctypes.create_unicode_buffer(n + 1)
            user32.GetWindowTextW(hwnd, buf, n + 1)
            t = buf.value
            if TITLE_HINT in t:
                found.append((hwnd, t))
        return True

    user32.EnumWindows(EnumProc(cb), 0)
    return found


kernel32 = ctypes.windll.kernel32


def bring_front():
    """Force the IDE to the foreground.

    Windows refuses SetForegroundWindow from a process that does not own the
    current foreground, so we attach to the foreground thread's input queue
    first - that is the documented way around the restriction.
    """
    wins = find_hmi()
    if not wins:
        raise SystemExit("USART HMI window not found - is the IDE still open?")
    hwnd, title = wins[0]

    user32.ShowWindow(hwnd, 6)          # SW_MINIMIZE
    time.sleep(0.25)
    user32.ShowWindow(hwnd, 9)          # SW_RESTORE

    fg = user32.GetForegroundWindow()
    fg_tid = user32.GetWindowThreadProcessId(fg, None)
    my_tid = kernel32.GetCurrentThreadId()
    attached = False
    if fg_tid and fg_tid != my_tid:
        attached = bool(user32.AttachThreadInput(my_tid, fg_tid, True))
    user32.BringWindowToTop(hwnd)
    user32.SetForegroundWindow(hwnd)
    user32.SetFocus(hwnd)
    if attached:
        user32.AttachThreadInput(my_tid, fg_tid, False)
    time.sleep(0.8)
    return title


def click_r(x, y, front=True):
    if front:
        bring_front()
    pyautogui.click(int(x), int(y))
    time.sleep(0.35)


def click_p(px, py, front=True):
    """click using preview-space coordinates (multiplied by SCALE)"""
    click_r(px * SCALE, py * SCALE, front)


def shot(path):
    img = pyautogui.screenshot()
    img.save(path)
    return img


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print("usage: hmi_click.py <x> <y> [out.png]   (real screen coords)")
        sys.exit(1)
    x, y = int(args[0]), int(args[1])
    out = args[2] if len(args) > 2 else r"D:\RTT\_tmp\hmi_after.png"
    t = bring_front()
    print("front:", t)
    pyautogui.click(x, y)
    time.sleep(0.9)
    shot(out)
    print("clicked", x, y, "->", out)
