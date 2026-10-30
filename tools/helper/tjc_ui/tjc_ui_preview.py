#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tjc_ui_preview.py - 1024x600 preview renderer for the TJC panel UI.

The panel is driven entirely from the board: every pixel is produced by TJC
serial commands (fill / draw / xstr / cls).  This renderer draws exactly the
same primitives at exactly the same coordinates, so what you see here is what
the panel will show.

Two rules that come from the panel, not from taste:
  * ASCII only.  Chinese needs a font-image resource inside the .HMI; the
    factory project may not carry one, and a missing font id draws nothing.
  * RGB565 colors.  COL_* below are 16-bit values, same numbers the firmware
    sends; the preview converts them back to 8-bit for display.

Usage:
    python tjc_ui_preview.py            -> _tmp/tjc_ui/preview.png
    python tjc_ui_preview.py --state ok
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

W, H = 1024, 600

# ---------------------------------------------------------------- palette
# 16-bit RGB565, matching the numbers the firmware will send
COL_BG        = 0x0841   # #080810 near-black navy  (page background)
COL_PANEL     = 0x0862   # #080C10 panel fill
COL_PANEL_HI  = 0x10A3   # raised panel
COL_LINE      = 0x2124   # hairlines
COL_LINE_HI   = 0x31A6   # brighter hairline
COL_TEXT      = 0xEF7D   # #F0F0F0 main text
COL_TEXT_DIM  = 0xAD75   # #ADADAD secondary  (>=4.5:1 on BG)
COL_TEXT_MUTE = 0x8430   # #848484 tertiary
COL_YELLOW    = 0xFEE0   # #FFFF00 accents
COL_CYAN      = 0x07FF   # #00FFFF
COL_GREEN     = 0x07EE   # #00FF00-ish
COL_RED       = 0xF9EA   # #FF6060
COL_INK       = 0x0000   # on-paper text


def rgb565(v):
    r = (v >> 11) & 0x1F
    g = (v >> 5) & 0x3F
    b = v & 0x1F
    return (r * 255 // 31, g * 255 // 63, b * 255 // 31)


# ---------------------------------------------------------------- fonts
FONT_DIR = r"C:\Windows\Fonts"


def _font(names, size):
    for n in names:
        p = os.path.join(FONT_DIR, n)
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def f_disp(size):   # condensed display — the Hermes headline voice
    return _font(["bahnschrift.ttf", "BAHNSCHRIFT.TTF", "arialbd.ttf"], size)


def f_mono(size):   # labels / readouts
    return _font(["consola.ttf", "cour.ttf"], size)


# ---------------------------------------------------------------- canvas
class Canvas:
    """Mirrors the TJC primitive set the firmware uses."""

    def __init__(self, w=W, h=H):
        self.im = Image.new("RGB", (w, h), rgb565(COL_BG))
        self.d = ImageDraw.Draw(self.im)

    def fill(self, x, y, w, h, col):
        self.d.rectangle([x, y, x + w - 1, y + h - 1], fill=rgb565(col))

    def box(self, x, y, w, h, col):
        """hollow rect, 1px, drawn inside the box (draw x,y,x+w,y+h,color)"""
        self.d.rectangle([x, y, x + w - 1, y + h - 1], outline=rgb565(col))

    def hline(self, x, y, w, col):
        self.d.line([x, y, x + w - 1, y], fill=rgb565(col))

    def vline(self, x, y, h, col):
        self.d.line([x, y, x, y + h - 1], fill=rgb565(col))

    def text(self, x, y, s, font, col, anchor="la"):
        self.d.text((x, y), s, font=font, fill=rgb565(col), anchor=anchor)

    def text_track(self, x, y, s, font, col, tracking=1):
        """letter-spaced label, mimicking the site's .1em tracking"""
        cx = x
        for ch in s:
            self.d.text((cx, y), ch, font=font, fill=rgb565(col), anchor="la")
            cx += self.d.textlength(ch, font=font) + tracking
        return cx

    def save(self, path):
        self.im.save(path)
        return path


# ---------------------------------------------------------------- layout
# Everything below is the single source of truth.  The generator
# gen_layout_h.py turns these numbers into ui_layout.h for the firmware.
L = {
    # top bar
    "top_h": 44,
    # columns
    "pad": 12,
    "col_l_x": 12, "col_l_w": 268,
    "col_m_x": 292, "col_m_w": 396,
    "col_r_x": 700, "col_r_w": 312,
    "body_y": 56,
    "body_h": 468,
    # bottom strip
    "bot_y": 532, "bot_h": 56,
}


def draw_frame(c):
    p = L["pad"]
    # top bar
    c.fill(0, 0, W, L["top_h"], COL_PANEL)
    c.hline(0, L["top_h"] - 1, W, COL_LINE_HI)

    # logo mark: 16x16 outline + inner block (same as the PC console)
    c.box(p, 14, 16, 16, COL_TEXT)
    c.fill(p + 4, 18, 8, 8, COL_YELLOW)

    c.text_track(p + 26, 15, "HERMES", f_mono(15), COL_TEXT, 1)
    c.text_track(p + 26 + 78, 15, "/", f_mono(15), COL_TEXT_MUTE, 1)
    c.text_track(p + 26 + 94, 15, "BOARD AI CONSOLE", f_mono(13), COL_TEXT_DIM, 1)

    # column dividers
    c.vline(L["col_m_x"] - p, L["top_h"], L["body_h"] + 8, COL_LINE)
    c.vline(L["col_r_x"] - p, L["top_h"], L["body_h"] + 8, COL_LINE)

    # bottom strip
    c.fill(0, L["bot_y"], W, L["bot_h"], COL_PANEL)
    c.hline(0, L["bot_y"], W, COL_LINE_HI)


def draw_status(c, state):
    x = W - 200
    on = state.get("linked")
    c.fill(x, 16, 10, 10, COL_GREEN if on else COL_TEXT_MUTE)
    c.text_track(x + 16, 14, "LINKED" if on else "OFFLINE", f_mono(13),
                 COL_GREEN if on else COL_TEXT_MUTE, 1)


def draw_left(c, state):
    x, y = L["col_l_x"], L["body_y"]
    w = L["col_l_w"]

    # hero
    c.text(x, y + 2, "BOARD AI", f_disp(40), COL_TEXT)
    c.fill(x, y + 52, 54, 3, COL_YELLOW)
    c.text_track(x, y + 62, "RA8P1 / TITAN MINI", f_mono(11), COL_TEXT_DIM, 1)

    # 01 SERIAL
    yy = y + 92
    c.text_track(x, yy, "01", f_mono(11), COL_YELLOW, 1)
    c.hline(x + 22, yy + 7, 12, COL_YELLOW)
    c.text_track(x + 40, yy, "SERIAL", f_mono(11), COL_TEXT_DIM, 1)

    yy += 22
    c.text_track(x, yy, "PORT", f_mono(10), COL_TEXT_MUTE, 1)
    c.fill(x, yy + 16, w, 34, COL_PANEL_HI)
    c.box(x, yy + 16, w, 34, COL_LINE_HI)
    c.text(x + 10, yy + 24, state.get("port", "COM7"), f_mono(15), COL_TEXT)

    yy += 60
    c.text_track(x, yy, "BAUD", f_mono(10), COL_TEXT_MUTE, 1)
    c.fill(x, yy + 16, w, 34, COL_PANEL_HI)
    c.box(x, yy + 16, w, 34, COL_LINE_HI)
    c.text(x + 10, yy + 24, state.get("baud", "115200"), f_mono(15), COL_TEXT)

    yy += 60
    c.fill(x, yy, w, 40, COL_TEXT)
    c.text(x + w // 2, yy + 20, "CONNECT", f_mono(14), COL_INK, anchor="mm")

    # 02 SESSION
    yy += 58
    c.text_track(x, yy, "02", f_mono(11), COL_YELLOW, 1)
    c.hline(x + 22, yy + 7, 12, COL_YELLOW)
    c.text_track(x + 40, yy, "SESSION", f_mono(11), COL_TEXT_DIM, 1)

    yy += 22
    c.text_track(x, yy, "MODEL", f_mono(10), COL_TEXT_MUTE, 1)
    c.text(x + w, yy - 2, "deepseek-flash", f_mono(12), COL_CYAN, anchor="ra")

    yy += 22
    c.text_track(x, yy, "KEY", f_mono(10), COL_TEXT_MUTE, 1)
    c.text(x + w, yy - 2, "SET" if state.get("key") else "NOT SET", f_mono(12),
           COL_GREEN if state.get("key") else COL_RED, anchor="ra")

    yy += 24
    half = (w - 6) // 2
    c.box(x, yy, half, 36, COL_LINE_HI)
    c.text(x + half // 2, yy + 18, "PUSH", f_mono(12), COL_TEXT, anchor="mm")
    c.box(x + half + 6, yy, half, 36, COL_LINE_HI)
    c.text(x + half + 6 + half // 2, yy + 18, "SAVE", f_mono(12), COL_TEXT, anchor="mm")

    yy += 44
    c.text_track(x, yy, "CLOCK", f_mono(10), COL_TEXT_MUTE, 1)
    c.text(x, yy + 14, state.get("clock", "12:34:56"), f_mono(16), COL_TEXT)


def draw_mid(c, state):
    x, y = L["col_m_x"], L["body_y"]
    w = L["col_m_w"]

    c.text_track(x, y, "04", f_mono(11), COL_YELLOW, 1)
    c.hline(x + 22, y + 7, 12, COL_YELLOW)
    c.text_track(x + 40, y, "CHANNEL", f_mono(11), COL_TEXT_DIM, 1)

    # log panel
    ly = y + 22
    lh = 290
    c.fill(x, ly, w, lh, COL_PANEL)
    c.box(x, ly, w, lh, COL_LINE)

    fm = f_mono(13)
    lx, ty = x + 12, ly + 10
    for line, col in state.get("log", [])[:12]:
        c.text(lx, ty, line[:52], fm, col)
        ty += 19

    # watermark
    c.text(x + w - 14, ly + lh - 44, "RA8P1", f_disp(44), COL_PANEL_HI, anchor="ra")

    # CAPTURE block
    by = ly + lh + 14
    c.text_track(x, by, "CAPTURE", f_mono(11), COL_YELLOW, 1)

    bw, bh = (w - 12) // 3, 52
    labels = [("OK", COL_GREEN, "ok"), ("NG", COL_RED, "ng"), ("LIVE", COL_CYAN, "live")]
    for i, (lab, col, key) in enumerate(labels):
        bx = x + i * (bw + 6)
        c.fill(bx, by + 20, bw, bh, COL_PANEL_HI)
        c.box(bx, by + 20, bw, bh, col)
        c.text(bx + bw // 2, by + 20 + 18, lab, f_mono(18), col, anchor="mm")
        if key in ("ok", "ng"):
            c.text(bx + bw // 2, by + 20 + 38,
                   str(state.get(key, 0)), f_mono(11), COL_TEXT_DIM, anchor="mm")

    # readout row
    ry = by + 20 + bh + 12
    c.text_track(x, ry, "CAM", f_mono(10), COL_TEXT_MUTE, 1)
    c.text(x + 40, ry - 2, f"luma {state.get('luma', 142)}", f_mono(13), COL_CYAN)
    c.text(x + 150, ry - 2, f"{state.get('wh', '320x240')}", f_mono(13), COL_TEXT_DIM)
    c.text(x + 260, ry - 2, f"fps {state.get('fps', 12)}", f_mono(13), COL_TEXT_DIM)

    # prompt row (touch keyboard target)
    py = ry + 22
    c.text_track(x, py + 12, "ASK", f_mono(10), COL_TEXT_MUTE, 1)
    c.fill(x + 46, py, w - 46 - 84, 34, COL_PANEL_HI)
    c.box(x + 46, py, w - 46 - 84, 34, COL_LINE_HI)
    c.text(x + 56, py + 8, state.get("prompt", "touch to type..."), f_mono(13),
           COL_TEXT_DIM if not state.get("prompt") else COL_TEXT)
    c.fill(x + w - 80, py, 76, 34, COL_TEXT)
    c.text(x + w - 80 + 38, py + 17, "SEND", f_mono(12), COL_INK, anchor="mm")


def draw_right(c, state):
    x, y = L["col_r_x"], L["body_y"]
    w = L["col_r_w"]

    c.text_track(x, y, "05", f_mono(11), COL_YELLOW, 1)
    c.hline(x + 22, y + 7, 12, COL_YELLOW)
    c.text_track(x + 40, y, "QUEUE", f_mono(11), COL_TEXT_DIM, 1)
    c.text(x + w, y - 2, f"{state.get('files', 5)} FILES", f_mono(11),
           COL_TEXT_MUTE, anchor="ra")

    # file rows (no thumbnails: pushing images into the panel needs .HMI assets)
    ry = y + 24
    for i, (name, size) in enumerate(state.get("queue", [])):
        if i >= 6:
            break
        rh = 46
        c.fill(x, ry, w, rh, COL_PANEL)
        c.box(x, ry, w, rh, COL_LINE)
        if i == state.get("sel", 0):
            c.fill(x, ry, 3, rh, COL_YELLOW)
        c.text(x + 12, ry + 8, name[:26], f_mono(13),
               COL_TEXT if i == state.get("sel", 0) else COL_TEXT_DIM)
        c.text(x + 12, ry + 26, size, f_mono(10), COL_TEXT_MUTE)
        ry += rh + 5

    # actions
    by = L["bot_y"] - 8 - (3 * 40 + 2 * 6)
    half = (w - 6) // 2
    c.box(x, by, half, 40, COL_LINE_HI)
    c.text(x + half // 2, by + 20, "IMPORT", f_mono(12), COL_TEXT, anchor="mm")
    c.box(x + half + 6, by, half, 40, COL_LINE_HI)
    c.text(x + half + 6 + half // 2, by + 20, "FOLDER", f_mono(12), COL_TEXT, anchor="mm")

    by += 46
    c.box(x, by, w, 40, COL_LINE_HI)
    c.text(x + w // 2, by + 20, "REFRESH", f_mono(12), COL_TEXT, anchor="mm")

    by += 46
    c.fill(x, by, w, 40, COL_TEXT)
    c.text(x + w // 2, by + 20, "SEND IMAGE", f_mono(13), COL_INK, anchor="mm")


def draw_bottom(c, state):
    y = L["bot_y"] + 8
    c.text_track(L["pad"], y + 4, "SESSION", f_mono(10), COL_TEXT_MUTE, 1)
    c.text(L["pad"] + 68, y + 2, f"model {state.get('model', 'deepseek-flash')}",
           f_mono(12), COL_TEXT_DIM)
    c.text(L["pad"] + 290, y + 2, f"key {'SET' if state.get('key') else 'NOT SET'}",
           f_mono(12), COL_GREEN if state.get("key") else COL_RED)
    c.text(L["pad"] + 400, y + 2, f"http {state.get('http', '192.168.137.1:8000')}",
           f_mono(12), COL_TEXT_DIM)
    c.text(W - L["pad"], y + 2, "v2 / TJC X5 / 1024x600", f_mono(11),
           COL_TEXT_MUTE, anchor="ra")


def render(state=None):
    state = state or DEFAULT_STATE
    c = Canvas()
    draw_frame(c)
    draw_status(c, state)
    draw_left(c, state)
    draw_mid(c, state)
    draw_right(c, state)
    draw_bottom(c, state)
    return c


DEFAULT_STATE = {
    "linked": True, "port": "COM7", "baud": "115200", "key": True,
    "clock": "12:34:56", "model": "deepseek-flash",
    "log": [
        ("READY", COL_TEXT_DIM),
        ("1) port: CH340 (COM7), not the DAP CDC", COL_TEXT_DIM),
        ("2) connect sends CR + api key", COL_TEXT_DIM),
        ("3) press DATE before asking", COL_TEXT_DIM),
        ("", COL_TEXT_DIM),
        ("[cam] 320x240 luma=142 gain=1", COL_CYAN),
        ("[cam] 153600 B -> HTTP 200 (77 ms)", COL_GREEN),
        ("[llm] ask: what do you see?", COL_TEXT_DIM),
        ("A: A green PCB with a missing solder pad.", COL_CYAN),
    ],
    "ok": 128, "ng": 94, "luma": 142, "fps": 12, "wh": "320x240",
    "files": 5,
    "queue": [("probe_64k.jpg", "63 KB"), ("probe_128k.jpg", "118 KB"),
              ("img_test_320x240.jpg", "8 KB"), ("img_..._0_5.jpg", "128 KB"),
              ("img_..._0_0.jpg", "232 KB")],
    "sel": 0, "http": "192.168.137.1:8000",
    "prompt": "",
}


if __name__ == "__main__":
    out_dir = r"D:\RTT\_tmp\tjc_ui"
    os.makedirs(out_dir, exist_ok=True)
    st = dict(DEFAULT_STATE)
    if "--state" in sys.argv:
        i = sys.argv.index("--state")
        if i + 1 < len(sys.argv) and sys.argv[i + 1] == "offline":
            st["linked"] = False
            st["key"] = False
            st["log"] = [("OFFLINE - no serial", COL_RED)]
    path = os.path.join(out_dir, "preview.png")
    render(st).save(path)
    print("saved", path, f"{W}x{H}")
