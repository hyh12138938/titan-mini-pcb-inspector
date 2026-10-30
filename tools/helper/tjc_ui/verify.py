#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify.py - check the panel UI before it ever reaches hardware.

Two things can silently break on the panel and both are cheap to catch here:

  1. a hit box that does not sit on top of the button you can see
     -> overlay the BTN_* rectangles from tjc_panel.h on the rendered screen
  2. anything drawn outside 0..1023 x 0..599
     -> every zone is bounds-checked

The zones below are transcribed from tjc_panel.h (BTN_*/BOX_* macros).  They are
deliberately duplicated rather than parsed: if the C header changes and this
file is not updated, the overlay in the output will visibly disagree with the
screenshot, which is exactly the signal we want.
"""
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tjc_ui_preview as P

BODY = 56

# --- transcribed from tjc_panel.h ---
ZONES = [
    ("CONNECT",   12,  BODY + 234, 268, 40),
    ("PUSH",      12,  BODY + 360, 131, 36),
    ("SAVE",      149, BODY + 360, 131, 36),
    ("OK",        292, BODY + 346, 128, 52),
    ("NG",        426, BODY + 346, 128, 52),
    ("LIVE",      560, BODY + 346, 128, 52),
    ("ASK box",   338, BODY + 432, 266, 34),
    ("SEND",      608, BODY + 432,  76, 34),
    ("IMPORT",    700, 532 - 8 - 132, 153, 40),
    ("FOLDER",    859, 532 - 8 - 132, 153, 40),
    ("REFRESH",   700, 532 - 8 - 132 + 46, 312, 40),
    ("SEND IMAGE",700, 532 - 8 - 132 + 92, 312, 40),
]


def check_bounds():
    bad = []
    for name, x, y, w, h in ZONES:
        if x < 0 or y < 0 or x + w > P.W or y + h > P.H:
            bad.append((name, x, y, w, h))
    return bad


def check_overlap():
    """two zones must never claim the same pixel: the later one would win and a
    button would feel dead"""
    bad = []
    for i in range(len(ZONES)):
        for j in range(i + 1, len(ZONES)):
            n1, x1, y1, w1, h1 = ZONES[i]
            n2, x2, y2, w2, h2 = ZONES[j]
            if x1 < x2 + w2 and x2 < x1 + w1 and y1 < y2 + h2 and y2 < y1 + h1:
                bad.append((n1, n2))
    return bad


def overlay(state):
    canvas = P.render(state)
    im = canvas.im.convert("RGB")
    d = ImageDraw.Draw(im, "RGBA")
    f = P.f_mono(11)

    for name, x, y, w, h in ZONES:
        d.rectangle([x, y, x + w - 1, y + h - 1], outline=(255, 0, 255, 255), width=2)
        d.text((x + 4, y + h - 14), name, font=f, fill=(255, 0, 255, 255))
    return im


def main():
    out = r"D:\RTT\_tmp\tjc_ui"
    os.makedirs(out, exist_ok=True)

    bad_b = check_bounds()
    bad_o = check_overlap()
    print(f"zones: {len(ZONES)}")
    print("out of bounds:", bad_b if bad_b else "none")
    print("overlapping :", bad_o if bad_o else "none")

    # three states: normal, offline, and a full log (checks text clipping)
    for tag, st in (("normal", dict(P.DEFAULT_STATE)),
                    ("offline", dict(P.DEFAULT_STATE, linked=False, key=False,
                                     log=[("OFFLINE - no serial", P.COL_RED)])),
                    ("fulllog", dict(P.DEFAULT_STATE,
                                     log=[(f"line {i:02d} " + "x" * 30, P.COL_TEXT_DIM)
                                          for i in range(12)]))):
        p = os.path.join(out, f"preview_{tag}.png")
        P.render(st).save(p)
        print("saved", p)

    ov = overlay(dict(P.DEFAULT_STATE))
    p = os.path.join(out, "hotzones.png")
    ov.save(p)
    print("saved", p)

    return 0 if not bad_b and not bad_o else 1


if __name__ == "__main__":
    sys.exit(main())
