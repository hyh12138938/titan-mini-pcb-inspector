#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tjc_sim.py - generate the exact instruction stream the firmware would send,
then parse that stream back and render it.

Why not just reuse tjc_ui_preview.py: that file draws pixels directly.  This one
goes through the wire format instead
    fill x,y,w,h,color\xff\xff\xff
    draw x,y,w,h,color\xff\xff\xff
    xstr x,y,w,h,fontid,fg,bg,xc,yc,sta,"text"\xff\xff\xff
so it can catch the two things a pixel renderer cannot:

  1. an argument-count or quoting mistake in the xstr format (11 args, string
     last, commas inside the string would break the panel's parser)
  2. how many bytes one full screen costs -> how long it takes at 115200

The layout constants mirror tjc_panel.c / tjc_panel.h.
"""
import math
import os
import re
import sys

from PIL import Image, ImageDraw, ImageFont

W, H = 1024, 600
BAUD = 115200
TERM = b"\xff\xff\xff"

# palette (RGB565 numbers, as sent on the wire)
C_BG, C_PANEL, C_PANEL_HI = 0x0841, 0x0862, 0x10A3
C_LINE, C_LINE_HI = 0x2124, 0x31A6
C_TEXT, C_TEXT_DIM, C_TEXT_MUTE = 0xEF7D, 0xAD75, 0x8430
C_YELLOW, C_CYAN, C_GREEN, C_RED, C_INK = 0xFEE0, 0x07FF, 0x07EE, 0xF9EA, 0x0000


def rgb565(v):
    return ((v >> 11 & 0x1F) * 255 // 31, (v >> 5 & 0x3F) * 255 // 63, (v & 0x1F) * 255 // 31)


class Stream:
    """Collects the exact bytes the firmware writes to uart1."""

    def __init__(self):
        self.buf = bytearray()
        self.cmds = []

    def _emit(self, s):
        b = s.encode("ascii", "replace") + TERM
        self.buf += b
        self.cmds.append(s)

    def cls(self):
        self._emit("cls")

    def fill(self, x, y, w, h, c):
        self._emit(f"fill {x},{y},{w},{h},{c}")

    def draw(self, x, y, w, h, c):
        self._emit(f"draw {x},{y},{w},{h},{c}")

    def xstr(self, x, y, w, h, fid, fg, bg, xc, yc, sta, text):
        # the panel splits on commas: a comma in the string must never be sent
        assert "," not in text, f"comma in string would break xstr: {text!r}"
        assert '"' not in text
        self._emit(f'xstr {x},{y},{w},{h},{fid},{fg},{bg},{xc},{yc},{sta},"{text}"')

    @property
    def nbytes(self):
        return len(self.buf)

    def seconds(self):
        return self.nbytes * 10.0 / BAUD      # 8N1 -> 10 bits per byte


# ------------------------------------------------------------------ layout
PAD, TOP_H, BODY_Y, BODY_H, BOT_Y, BOT_H = 12, 44, 56, 468, 532, 56
COL_L_X, COL_L_W = 12, 268
COL_M_X, COL_M_W = 292, 396
COL_R_X, COL_R_W = 700, 312

F_BODY, F_BIG = 1, 2


def build_ui(s, state):
    s.cls()
    # ---- top bar
    s.fill(0, 0, W, TOP_H, C_PANEL)
    s.fill(0, TOP_H - 1, W, 1, C_LINE_HI)
    s.draw(PAD, 14, 16, 16, C_TEXT)
    s.fill(PAD + 4, 18, 8, 8, C_YELLOW)
    s.xstr(PAD + 26, 14, 90, 18, F_BODY, C_TEXT, C_BG, 0, 0, 3, "HERMES")
    s.xstr(PAD + 100, 14, 12, 18, F_BODY, C_TEXT_MUTE, C_BG, 0, 0, 3, "/")
    s.xstr(PAD + 118, 14, 240, 18, F_BODY, C_TEXT_DIM, C_BG, 0, 0, 3, "BOARD AI CONSOLE")
    s.fill(COL_M_X - PAD, TOP_H, 1, BODY_H + 8, C_LINE)
    s.fill(COL_R_X - PAD, TOP_H, 1, BODY_H + 8, C_LINE)

    # ---- status
    sx = W - 210
    s.fill(sx, 16, 10, 10, C_GREEN if state["linked"] else C_TEXT_MUTE)
    s.xstr(sx + 16, 12, 80, 18, F_BODY, C_GREEN if state["linked"] else C_TEXT_MUTE,
           C_BG, 0, 0, 3, "LINKED" if state["linked"] else "OFFLINE")
    s.xstr(sx + 100, 12, 100, 18, F_BODY, C_TEXT_DIM, C_BG, 0, 0, 3, state["clock"])

    # ---- left
    x, w = COL_L_X, COL_L_W
    half = (w - 6) // 2
    s.xstr(x, BODY_Y + 2, w, 46, F_BIG, C_TEXT, C_BG, 0, 0, 3, "BOARD AI")
    s.fill(x, BODY_Y + 52, 54, 3, C_YELLOW)
    s.xstr(x, BODY_Y + 62, w, 16, F_BODY, C_TEXT_DIM, C_BG, 0, 0, 3, "RA8P1 / TITAN MINI")

    s.xstr(x, BODY_Y + 92, 20, 16, F_BODY, C_YELLOW, C_BG, 0, 0, 3, "01")
    s.fill(x + 22, BODY_Y + 99, 12, 1, C_YELLOW)
    s.xstr(x + 40, BODY_Y + 92, 160, 16, F_BODY, C_TEXT_DIM, C_BG, 0, 0, 3, "SERIAL")

    s.xstr(x, BODY_Y + 114, w, 14, F_BODY, C_TEXT_MUTE, C_BG, 0, 0, 3, "PORT")
    s.fill(x, BODY_Y + 130, w, 34, C_PANEL_HI)
    s.draw(x, BODY_Y + 130, w, 34, C_LINE_HI)
    s.xstr(x + 10, BODY_Y + 134, w - 20, 26, F_BODY, C_TEXT, C_BG, 0, 0, 3, "COM7")

    s.xstr(x, BODY_Y + 174, w, 14, F_BODY, C_TEXT_MUTE, C_BG, 0, 0, 3, "BAUD")
    s.fill(x, BODY_Y + 190, w, 34, C_PANEL_HI)
    s.draw(x, BODY_Y + 190, w, 34, C_LINE_HI)
    s.xstr(x + 10, BODY_Y + 194, w - 20, 26, F_BODY, C_TEXT, C_BG, 0, 0, 3, "115200")

    s.fill(x, BODY_Y + 234, w, 40, C_TEXT)
    s.xstr(x, BODY_Y + 234, w, 40, F_BIG, C_INK, C_TEXT, 1, 1, 3, "CONNECT")

    s.xstr(x, BODY_Y + 292, 20, 16, F_BODY, C_YELLOW, C_BG, 0, 0, 3, "02")
    s.fill(x + 22, BODY_Y + 299, 12, 1, C_YELLOW)
    s.xstr(x + 40, BODY_Y + 292, 160, 16, F_BODY, C_TEXT_DIM, C_BG, 0, 0, 3, "SESSION")

    s.xstr(x, BODY_Y + 314, 60, 16, F_BODY, C_TEXT_MUTE, C_BG, 0, 0, 3, "MODEL")
    s.xstr(x, BODY_Y + 312, w, 18, F_BODY, C_CYAN, C_BG, 2, 0, 3, "deepseek-flash")
    s.xstr(x, BODY_Y + 336, 40, 16, F_BODY, C_TEXT_MUTE, C_BG, 0, 0, 3, "KEY")
    s.xstr(x, BODY_Y + 334, w, 18, F_BODY, C_GREEN if state["key"] else C_RED,
           C_BG, 2, 0, 3, "SET" if state["key"] else "NOT SET")

    s.fill(x, BODY_Y + 360, half, 36, C_PANEL_HI)
    s.draw(x, BODY_Y + 360, half, 36, C_LINE_HI)
    s.xstr(x, BODY_Y + 360, half, 36, F_BIG, C_TEXT, C_PANEL_HI, 1, 1, 3, "PUSH")
    s.fill(x + half + 6, BODY_Y + 360, half, 36, C_PANEL_HI)
    s.draw(x + half + 6, BODY_Y + 360, half, 36, C_LINE_HI)
    s.xstr(x + half + 6, BODY_Y + 360, half, 36, F_BIG, C_TEXT, C_PANEL_HI, 1, 1, 3, "SAVE")

    s.xstr(x, BODY_Y + 404, 80, 14, F_BODY, C_TEXT_MUTE, C_BG, 0, 0, 3, "CLOCK")
    s.xstr(x, BODY_Y + 418, w, 24, F_BIG, C_TEXT, C_BG, 0, 0, 3, state["clock"])

    # ---- middle
    x, w = COL_M_X, COL_M_W
    s.xstr(x, BODY_Y, 20, 16, F_BODY, C_YELLOW, C_BG, 0, 0, 3, "04")
    s.fill(x + 22, BODY_Y + 7, 12, 1, C_YELLOW)
    s.xstr(x + 40, BODY_Y, 160, 16, F_BODY, C_TEXT_DIM, C_BG, 0, 0, 3, "CHANNEL")

    s.fill(x, BODY_Y + 22, w, 290, C_PANEL)
    s.draw(x, BODY_Y + 22, w, 290, C_LINE)
    s.xstr(x, BODY_Y + 268, w - 14, 44, F_BODY, C_LINE, C_PANEL, 2, 2, 3, "RA8P1")
    for i, (line, col) in enumerate(state["log"][:12]):
        s.xstr(x + 12, BODY_Y + 32 + i * 19, w - 24, 18, F_BODY, col, C_BG, 0, 0, 3, line)

    s.xstr(x, BODY_Y + 326, 120, 16, F_BODY, C_YELLOW, C_BG, 0, 0, 3, "CAPTURE")
    s.fill(x, BODY_Y + 346, 128, 52, C_PANEL_HI)
    s.draw(x, BODY_Y + 346, 128, 52, C_GREEN)
    s.xstr(x, BODY_Y + 347, 128, 32, F_BIG, C_GREEN, C_PANEL_HI, 1, 1, 3, "OK")
    s.xstr(x, BODY_Y + 379, 128, 18, F_BODY, C_TEXT_DIM, C_PANEL_HI, 1, 0, 3, str(state["ok"]))
    s.fill(x + 134, BODY_Y + 346, 128, 52, C_PANEL_HI)
    s.draw(x + 134, BODY_Y + 346, 128, 52, C_RED)
    s.xstr(x + 134, BODY_Y + 347, 128, 32, F_BIG, C_RED, C_PANEL_HI, 1, 1, 3, "NG")
    s.xstr(x + 134, BODY_Y + 379, 128, 18, F_BODY, C_TEXT_DIM, C_PANEL_HI, 1, 0, 3, str(state["ng"]))
    s.fill(x + 268, BODY_Y + 346, 128, 52, C_PANEL_HI)
    s.draw(x + 268, BODY_Y + 346, 128, 52, C_CYAN)
    s.xstr(x + 268, BODY_Y + 347, 128, 32, F_BIG, C_CYAN, C_PANEL_HI, 1, 1, 3, "LIVE")

    s.xstr(x, BODY_Y + 408, 40, 16, F_BODY, C_TEXT_MUTE, C_BG, 0, 0, 3, "CAM")
    s.xstr(x + 40, BODY_Y + 406, 110, 18, F_BODY, C_CYAN, C_BG, 0, 0, 3, f"luma {state['luma']}")
    s.xstr(x + 150, BODY_Y + 406, 90, 18, F_BODY, C_TEXT_DIM, C_BG, 0, 0, 3, state["wh"])
    s.xstr(x + 250, BODY_Y + 406, 80, 18, F_BODY, C_TEXT_DIM, C_BG, 0, 0, 3, f"fps {state['fps']}")

    s.xstr(x, BODY_Y + 442, 40, 16, F_BODY, C_TEXT_MUTE, C_BG, 0, 0, 3, "ASK")
    s.fill(x + 46, BODY_Y + 432, w - 46 - 84, 34, C_PANEL_HI)
    s.draw(x + 46, BODY_Y + 432, w - 46 - 84, 34, C_LINE_HI)
    s.xstr(x + 56, BODY_Y + 436, w - 46 - 100, 26, F_BODY, C_TEXT_DIM, C_BG, 0, 0, 3,
           "touch to type...")
    s.fill(x + w - 80, BODY_Y + 432, 76, 34, C_TEXT)
    s.xstr(x + w - 80, BODY_Y + 432, 76, 34, F_BIG, C_INK, C_TEXT, 1, 1, 3, "SEND")

    # ---- right
    x, w = COL_R_X, COL_R_W
    s.xstr(x, BODY_Y, 20, 16, F_BODY, C_YELLOW, C_BG, 0, 0, 3, "05")
    s.fill(x + 22, BODY_Y + 7, 12, 1, C_YELLOW)
    s.xstr(x + 40, BODY_Y, 160, 16, F_BODY, C_TEXT_DIM, C_BG, 0, 0, 3, "QUEUE")
    s.xstr(x, BODY_Y - 2, w, 18, F_BODY, C_TEXT_MUTE, C_BG, 2, 0, 3,
           f"{state['files']} FILES")

    for i in range(5):
        ry = BODY_Y + 24 + i * 51
        s.fill(x, ry, w, 46, C_PANEL)
        s.draw(x, ry, w, 46, C_LINE)
        s.xstr(x + 12, ry + 6, w - 24, 18, F_BODY, C_TEXT_DIM, C_BG, 0, 0, 3,
               f"img_{i+1:02d}.jpg")
        s.xstr(x + 12, ry + 26, w - 24, 14, F_BODY, C_TEXT_MUTE, C_BG, 0, 0, 3, "128 KB")

    by = BOT_Y - 8 - (3 * 40 + 2 * 6)
    half = (w - 6) // 2
    for bx, bw, label in ((x, half, "IMPORT"), (x + half + 6, half, "FOLDER")):
        s.fill(bx, by, bw, 40, C_PANEL_HI)
        s.draw(bx, by, bw, 40, C_LINE_HI)
        s.xstr(bx, by, bw, 40, F_BIG, C_TEXT, C_PANEL_HI, 1, 1, 3, label)
    for k, label in ((1, "REFRESH"), (2, "SEND IMAGE")):
        yy = by + 46 * k
        s.fill(x, yy, w, 40, C_TEXT if label == "SEND IMAGE" else C_PANEL_HI)
        if label != "SEND IMAGE":
            s.draw(x, yy, w, 40, C_LINE_HI)
        s.xstr(x, yy, w, 40, F_BODY if label == "SEND IMAGE" else F_BIG,
               C_INK if label == "SEND IMAGE" else C_TEXT,
               C_TEXT if label == "SEND IMAGE" else C_PANEL_HI, 1, 1, 3, label)

    # ---- bottom
    s.fill(0, BOT_Y, W, BOT_H, C_PANEL)
    s.fill(0, BOT_Y, W, 1, C_LINE_HI)
    s.xstr(PAD, BOT_Y + 10, 70, 16, F_BODY, C_TEXT_MUTE, C_BG, 0, 0, 3, "SESSION")
    s.xstr(PAD + 76, BOT_Y + 8, 200, 18, F_BODY, C_TEXT_DIM, C_BG, 0, 0, 3,
           "model deepseek-flash")
    s.xstr(PAD + 290, BOT_Y + 8, 110, 18, F_BODY, C_GREEN if state["key"] else C_RED,
           C_BG, 0, 0, 3, "key SET" if state["key"] else "key NOT SET")
    s.xstr(PAD + 410, BOT_Y + 8, 240, 18, F_BODY, C_TEXT_DIM, C_BG, 0, 0, 3,
           "http 192.168.137.1:8000")
    s.xstr(W - PAD, BOT_Y + 8, 300, 18, F_BODY, C_TEXT_MUTE, C_BG, 2, 0, 3,
           "v2 / TJC X5 / 1024x600")


# ------------------------------------------------------------------ parser
RE_FILL = re.compile(r"^fill (\d+),(\d+),(\d+),(\d+),(\d+)$")
RE_DRAW = re.compile(r"^draw (\d+),(\d+),(\d+),(\d+),(\d+)$")
RE_XSTR = re.compile(
    r'^xstr (\d+),(\d+),(\d+),(\d+),(\d+),(\d+),(\d+),(\d),(\d),(\d),"([^"]*)"$')


def _font(big, size_hint):
    names = ["bahnschrift.ttf", "BAHNSCHRIFT.TTF", "arialbd.ttf"] if big else ["consola.ttf", "cour.ttf"]
    for n in names:
        p = os.path.join(r"C:\Windows\Fonts", n)
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size_hint)
            except Exception:
                pass
    return ImageFont.load_default()


def interpret(cmds):
    """render the parsed stream: proves the wire format is self-consistent"""
    im = Image.new("RGB", (W, H), rgb565(C_BG))
    d = ImageDraw.Draw(im)
    errs = []

    for c in cmds:
        m = RE_FILL.match(c)
        if m:
            x, y, w, h, col = map(int, m.groups())
            d.rectangle([x, y, x + w - 1, y + h - 1], fill=rgb565(col))
            continue
        m = RE_DRAW.match(c)
        if m:
            x, y, w, h, col = map(int, m.groups())
            d.rectangle([x, y, x + w - 1, y + h - 1], outline=rgb565(col))
            continue
        m = RE_XSTR.match(c)
        if m:
            g = m.groups()
            x, y, w, h = map(int, g[0:4])
            fid, fg, bg = int(g[4]), int(g[5]), int(g[6])
            xc, yc, sta = int(g[7]), int(g[8]), int(g[9])
            text = g[10]
            big = (fid == F_BIG)
            size = max(8, min(h - 2, int(h * (0.78 if big else 0.86))))
            f = _font(big, size)
            tw = d.textlength(text, font=f)
            th = size
            tx = x + (w - tw) / 2 if xc == 1 else (x + w - tw if xc == 2 else x)
            ty = y + (h - th) / 2 if yc == 1 else (y + h - th if yc == 2 else y)
            if sta == 1:      # solid background
                d.rectangle([x, y, x + w - 1, y + h - 1], fill=rgb565(bg))
            d.text((tx, ty), text, font=f, fill=rgb565(fg))
            continue
        if c == "cls":
            d.rectangle([0, 0, W - 1, H - 1], fill=rgb565(C_BG))
            continue
        errs.append(c)
    return im, errs


DEFAULT_STATE = {
    "linked": True, "key": True, "clock": "12:34:56", "ok": 128, "ng": 94,
    "luma": 142, "fps": 12, "wh": "320x240", "files": 5,
    "log": [
        ("READY", C_TEXT_DIM),
        ("1) port CH340 COM7 not DAP", C_TEXT_DIM),
        ("2) connect sends CR + key", C_TEXT_DIM),
        ("3) press DATE before ask", C_TEXT_DIM),
        ("", C_TEXT_DIM),
        ("[cam] 320x240 luma=142 gain=1", C_CYAN),
        ("[cam] 153600 B -> HTTP 200", C_GREEN),
        ("[llm] ask: what do you see?", C_TEXT_DIM),
        ("A: A green PCB missing pad.", C_CYAN),
    ],
}


def main():
    out = r"D:\RTT\_tmp\tjc_ui"
    os.makedirs(out, exist_ok=True)

    st = Stream()
    build_ui(st, DEFAULT_STATE)

    im, errs = interpret(st.cmds)
    p = os.path.join(out, "sim_from_wire.png")
    im.save(p)

    with open(os.path.join(out, "sim_stream.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(st.cmds))

    print(f"commands      : {len(st.cmds)}")
    print(f"bytes on wire : {st.nbytes} ({st.nbytes/1024:.1f} KB)")
    print(f"time @115200  : {st.seconds()*1000:.0f} ms")
    print(f"unparsed cmds : {len(errs)} {errs[:3] if errs else ''}")
    print(f"max cmd len   : {max(len(c) for c in st.cmds)}")
    print("saved", p)
    return 0 if not errs else 1


if __name__ == "__main__":
    sys.exit(main())
