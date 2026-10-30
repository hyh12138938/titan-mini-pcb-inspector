"""
parallax_demo.py - scroll-linked parallax page, native Tkinter version.

Ports the Hermes landing-page hero effect to a Tk window. The web version is
three CSS lines because the browser can re-blur on every frame; Tkinter cannot,
so the same formula is pre-baked into discrete (blur x opacity) frames and the
scroll position picks one:

    dy        = clamp(scroll * 0.35, -64, +64)      # figure lags behind
    progress  = clamp(scroll / (vh * 0.8), 0, 1)
    opacity   = 1 - 0.7 * progress
    blur      = 8px * progress

The figure's height is sized to leave room for dy, which is what the website
buys with `scale(1.22)`.

Standalone:  python D:\\RTT\\apps\\ui\\parallax_demo.py
Verify UI:   python D:\\RTT\\apps\\ui\\parallax_demo.py --shot
"""
import os
import sys

try:
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        ctypes.windll.user32.SetProcessDPIAware()
except Exception:
    pass

import tkinter as tk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hermes_theme import (  # noqa: E402
    Theme, ON_BLUE, BLUE, PAPER, YELLOW, CYAN, GREEN, DANGER, INK, mix, track,
)

ASSET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
FIGURE = os.path.join(ASSET_DIR, "figure.png")
SHOT_PATH = r"D:\RTT\_tmp\demo_shot.png"

FIG_SIZE = 430          # on-screen size of the artwork
LAG = 0.35              # figure drift per scrolled pixel
CLAMP_PX = 64           # the site's +/-64px limit
BLUR_MAX = 8.0
LEVELS = 7              # pre-baked blur/opacity steps


def clamp(v, a, b):
    return a if v < a else (b if v > b else v)


def build_frames(size=FIG_SIZE):
    """Pre-bake the blur x opacity ladder. Tkinter has no filter animation."""
    from PIL import Image, ImageFilter, ImageTk
    base = Image.open(FIGURE).convert("RGBA")
    out = []
    for i in range(LEVELS):
        p = i / (LEVELS - 1)
        im = base.resize((size, size), Image.LANCZOS)
        blur = BLUR_MAX * p
        if blur > 0.15:
            im = im.filter(ImageFilter.GaussianBlur(blur))
        alpha = 1.0 - 0.7 * p
        if alpha < 0.999:
            im.putalpha(im.split()[3].point(lambda v, a=alpha: int(v * a)))
        out.append(ImageTk.PhotoImage(im))
    return out


class ParallaxDemo(tk.Toplevel):
    """A scrollable page whose background figure lags behind the content."""

    def __init__(self, master=None, shot=False):
        super().__init__(master)
        self.title("Parallax — scroll-linked figure")
        self.configure(bg=BLUE)
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = min(1180, sw - 120), min(780, sh - 140)
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")
        self.minsize(880, 560)

        self.t = Theme(self)
        self.f = self.t.f
        self.shot = shot
        self.scroll = 0
        self.max_scroll = 0
        self.vh = h
        self.vw = w

        self._frames = build_frames()
        self._img = None
        self._build()
        self.after(60, self._layout)
        self.bind("<Configure>", lambda e: self._on_resize(e))
        self.bind("<MouseWheel>", self._wheel)
        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<Down>", lambda e: self._scroll_by(80))
        self.bind("<Up>", lambda e: self._scroll_by(-80))
        self.bind("<Prior>", lambda e: self._scroll_by(-int(self.vh * 0.8)))
        self.bind("<Next>", lambda e: self._scroll_by(int(self.vh * 0.8)))
        self.focus_force()

        if shot:
            self.overrideredirect(True)
            self.attributes("-topmost", True)
            self.lift()
            self.after(900, lambda: self._capture(0.0))
            self.after(1700, lambda: self._capture(0.55))
            self.after(2500, lambda: self._capture(0.9))

    # ------------------------------------------------------------------ #
    def _build(self):
        t = self.t
        f = self.f

        # readout strip lives outside the scroll layer, so it can never cover copy
        self.readout_bar = tk.Frame(self, bg=INK, height=30, bd=0, highlightthickness=0)
        self.readout_bar.pack(side="bottom", fill="x")
        self.readout_bar.pack_propagate(False)
        self.var_read = tk.StringVar(value="")
        tk.Label(self.readout_bar, textvariable=self.var_read, font=f.mono(9),
                 fg=CYAN, bg=INK, anchor="w", bd=0,
                 highlightthickness=0).pack(side="left", padx=14)
        tk.Label(self.readout_bar, text="ESC 关闭   ·   滚轮 / ↑↓ 滚动",
                 font=f.mono(9), fg=ON_BLUE["fg_40"], bg=INK, anchor="e", bd=0,
                 highlightthickness=0).pack(side="right", padx=14)

        self.canvas = tk.Canvas(self, bg=BLUE, bd=0, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self._img_item = self.canvas.create_image(-999, -999, image=self._frames[0],
                                                  anchor="center")

        # content lives in a frame the canvas slides
        self.content = tk.Frame(self.canvas, bg=BLUE, bd=0, highlightthickness=0)
        self._win = self.canvas.create_window(64, 0, window=self.content,
                                              anchor="nw", width=560)

        pad = dict(fill="x")
        tk.Label(self.content, text="PARALLAX", font=f.hero(54), fg=PAPER, bg=BLUE,
                 anchor="w", bd=0, highlightthickness=0).pack(**pad)
        tk.Frame(self.content, bg=YELLOW, height=3, width=54, bd=0,
                 highlightthickness=0).pack(anchor="w", pady=(8, 10))
        tk.Label(self.content, text="SCROLL-LINKED FIGURE  ·  TKINTER EDITION",
                 font=f.label(8), fg=ON_BLUE["fg_60"], bg=BLUE, anchor="w", bd=0,
                 highlightthickness=0).pack(**pad)

        self._blocks = []
        for i, (kicker, title, body) in enumerate([
            ("01 — the mechanism",
             "Two numbers, nothing else",
             "The web version writes two CSS variables on scroll and lets calc() do the "
             "rest, so the browser composites on the GPU. There is no animation library "
             "anywhere in it."),
            ("02 — what Tk cannot do",
             "No per-frame blur",
             "Tkinter has no filter pipeline, so blur is pre-baked into seven frames. "
             "Scrolling picks the nearest one. Opacity rides along in the same frame, "
             "which is why the figure fades as it blurs instead of stepping."),
            ("03 — what it costs",
             "Discrete instead of continuous",
             "Seven steps over a full scroll is coarse enough to see if you look for it. "
             "More steps means more memory; this build holds "
             f"{LEVELS} frames of {FIG_SIZE}px artwork."),
            ("04 — the honest ceiling",
             "Close, not identical",
             "Position is continuous (canvas coordinates are cheap) but blur is not. "
             "For a frame-exact replica the page has to run in a real browser — which is "
             "what the WebView build of this app is for."),
        ]):
            blk = tk.Frame(self.content, bg=BLUE, bd=0, highlightthickness=0)
            blk.pack(fill="x", pady=(46, 0))
            tk.Label(blk, text=track(kicker, 1), font=f.label(8), fg=YELLOW, bg=BLUE,
                     anchor="w", bd=0, highlightthickness=0).pack(**pad)
            tk.Label(blk, text=title, font=f.heading(20), fg=PAPER, bg=BLUE,
                     anchor="w", bd=0, highlightthickness=0).pack(fill="x", pady=(8, 0))
            body_lbl = tk.Label(blk, text=body, font=f.mono(10),
                                fg=ON_BLUE["fg_60"], bg=BLUE, anchor="w",
                                justify="left", bd=0, highlightthickness=0)
            body_lbl.pack(fill="x", pady=(10, 0))
            self._blocks.append(body_lbl)

        tk.Frame(self.content, bg=ON_BLUE["hair"], height=1, bd=0,
                 highlightthickness=0).pack(fill="x", pady=(56, 0))
        tk.Label(self.content, text="ESC / 滚轮 关闭", font=f.mono(9),
                 fg=ON_BLUE["fg_40"], bg=BLUE, anchor="w", bd=0,
                 highlightthickness=0).pack(fill="x", pady=(14, 40))

        self._progress = tk.Frame(self.canvas, bg=ON_BLUE["fill_14"], width=3, bd=0,
                                  highlightthickness=0)
        self._prog_item = self.canvas.create_window(0, 0, window=self._progress,
                                                    anchor="nw", width=3, height=1)
        self._prog_fill = tk.Frame(self.canvas, bg=YELLOW, width=3, bd=0,
                                   highlightthickness=0)
        self._fill_item = self.canvas.create_window(0, 0, window=self._prog_fill,
                                                    anchor="nw", width=3, height=1)

    # ------------------------------------------------------------------ #
    def _layout(self):
        self.vw = max(1, self.canvas.winfo_width())
        self.vh = max(1, self.canvas.winfo_height())
        self.cx = int(self.vw * 0.715)
        self.cy = int(self.vh * 0.5)
        cw = min(int(self.vw * 0.46), 560)
        self.canvas.itemconfigure(self._win, width=cw)
        wrap = max(240, cw - 16)
        for b in getattr(self, "_blocks", []):
            b.configure(wraplength=wrap)
        self.update_idletasks()
        self.content_h = self.content.winfo_reqheight()
        self.max_scroll = max(0, self.content_h - self.vh + 40)
        self.canvas.coords(self._prog_item, self.vw - 14, 0)
        self.canvas.itemconfigure(self._prog_item, height=self.vh)
        self._apply()

    def _on_resize(self, e):
        if e.widget is self:
            self._layout()

    def _wheel(self, e):
        self._scroll_by(-int(e.delta / 120) * 64)

    def _scroll_by(self, d):
        self.scroll = clamp(self.scroll + d, 0, self.max_scroll)
        self._apply()

    def _apply(self):
        p = clamp(self.scroll / (self.vh * 0.8), 0, 1)
        dy = clamp(self.scroll * LAG, -CLAMP_PX, CLAMP_PX)
        idx = int(round(p * (LEVELS - 1)))

        if idx != getattr(self, "_idx", -1):
            self._idx = idx
            self.canvas.itemconfigure(self._img_item, image=self._frames[idx])
        self.canvas.coords(self._img_item, self.cx, self.cy + dy)
        self.canvas.coords(self._win, max(48, int(self.vw * 0.055)), -self.scroll)

        fill_h = int(self.vh * p)
        self.canvas.itemconfigure(self._fill_item, height=max(1, fill_h))

        self.var_read.set(
            f"scroll {int(self.scroll):4d}/{int(self.max_scroll)}    "
            f"dy {dy:+6.1f}px    progress {p:.3f}    frame {idx + 1}/{LEVELS}")
        # readout strip needs no show/hide: it lives outside the scroll layer

    # ------------------------------------------------------------------ #
    def _capture(self, prog):
        from PIL import ImageGrab
        self.scroll = clamp(prog * (self.vh * 0.8), 0, self.max_scroll)
        self._apply()
        self.update_idletasks()
        self.update()
        x, y = self.winfo_rootx(), self.winfo_rooty()
        w, h = self.winfo_width(), self.winfo_height()
        out = SHOT_PATH.replace(".png", f"_{prog:.2f}.png")
        ImageGrab.grab(bbox=(x, y, x + w, y + h)).save(out)
        print("saved", out, f"{w}x{h}", "scroll=", int(self.scroll), flush=True)
        if prog >= 0.9:
            self.after(250, self.master.quit)


if __name__ == "__main__":
    root = tk.Tk()
    root.withdraw()
    shot = "--shot" in sys.argv
    app = ParallaxDemo(root, shot=shot)
    root.mainloop()
    try:
        root.destroy()
    except Exception:
        pass
