"""
preview_ui.py - a runnable style mock of the board AI helper in the
Hermes Agent visual language (see hermes_theme.py for the extracted tokens).

It is a *look* prototype: controls are real Tk widgets with hover/typing
behaviour, but the data is fake. Run it to judge the style, then the same
factories get wired into board_ai_helper.py.

  python D:\\RTT\\apps\\ui\\preview_ui.py
  python D:\\RTT\\apps\\ui\\preview_ui.py --shot   # render, save PNG, exit
"""
import os
import sys
import datetime

# Declare DPI awareness before any GUI call, so Tk geometry and screen pixels
# share one coordinate system (this display runs at 112.5%). Without it,
# winfo_rootx() is virtualised and screenshot crops drift.
try:
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)   # per-monitor v2
    except Exception:
        ctypes.windll.user32.SetProcessDPIAware()
except Exception:
    pass

import tkinter as tk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hermes_theme import (  # noqa: E402
    Theme, Fonts, ON_BLUE, BLUE, PAPER, YELLOW, CYAN, GREEN, ORANGE, DANGER,
    NEUTRAL, track, mix,
)

SHOT_PATH = r"D:\RTT\_tmp\ui_preview.png"


class Preview(tk.Tk):
    W, H = 1280, 820

    def __init__(self, shot=False):
        super().__init__()
        self.shot = shot
        self.title("Board AI Console")
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w = min(self.W, sw - 120)
        h = min(self.H, sh - 140)
        self._size = (w, h)
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")
        self.configure(bg=BLUE)
        self.minsize(1000, 640)
        self.t = Theme(self)
        self.f = self.t.f
        self._build()
        if shot:
            self.overrideredirect(True)   # frameless: the capture is the design
            self.attributes("-topmost", True)
            self.lift()
            self.after(1000, self._capture)

    # ------------------------------------------------------------------ #
    def _build(self):
        t = self.t
        self._topbar()
        t.rule(self, thickness=1)

        body = t.frame(self)
        body.pack(fill="both", expand=True)
        self._sidebar(body)
        t.vrule(body, color=ON_BLUE["hair"])
        self._main(body)

        t.rule(self, thickness=1)
        self._statusbar()

    # -- top bar -------------------------------------------------------- #
    def _topbar(self):
        t = self.t
        bar = t.frame(self, bg=BLUE, height=56)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        left = t.frame(bar, bg=BLUE)
        left.pack(side="left", fill="y", padx=(22, 0))

        # square glyph mark instead of any borrowed logo
        mark = tk.Canvas(left, width=16, height=16, bg=BLUE, bd=0, highlightthickness=0)
        mark.create_rectangle(0, 0, 15, 15, outline=PAPER, width=1)
        mark.create_rectangle(4, 4, 11, 11, fill=YELLOW, outline="")
        mark.pack(side="left", pady=(1, 0))

        tk.Label(left, text=track("hermes", 1), font=self.f.label(10), fg=PAPER,
                 bg=BLUE, bd=0, highlightthickness=0).pack(side="left", padx=(10, 0))
        tk.Label(left, text="/", font=self.f.mono(10), fg=ON_BLUE["fg_40"], bg=BLUE,
                 bd=0, highlightthickness=0).pack(side="left", padx=10)
        tk.Label(left, text=track("board ai console", 1), font=self.f.label(8),
                 fg=ON_BLUE["fg_60"], bg=BLUE, bd=0,
                 highlightthickness=0).pack(side="left")

        right = t.frame(bar, bg=BLUE)
        right.pack(side="right", fill="y", padx=(0, 22))
        for txt in ("date", "clear"):
            t.button(right, txt, kind="ghost").pack(side="right", padx=(8, 0), pady=13)

        state = t.frame(right, bg=BLUE)
        state.pack(side="right", padx=(0, 14), pady=13)
        t.dot(state, YELLOW).pack(side="left")
        tk.Label(state, text=track("linked", 1), font=self.f.label(8), fg=PAPER,
                 bg=BLUE, bd=0, highlightthickness=0).pack(side="left", padx=(8, 0))

    # -- sidebar -------------------------------------------------------- #
    def _sidebar(self, parent):
        t = self.t
        side = t.frame(parent, bg=BLUE, width=306)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)

        pad = t.frame(side, bg=BLUE)
        pad.pack(fill="both", expand=True, padx=22, pady=(20, 18))

        # hero block
        tk.Label(pad, text="BOARD AI", font=self.f.hero(30), fg=PAPER, bg=BLUE,
                 bd=0, highlightthickness=0, anchor="w").pack(fill="x")
        tk.Frame(pad, bg=YELLOW, height=3, width=54, bd=0,
                 highlightthickness=0).pack(anchor="w", pady=(6, 8))
        tk.Label(pad, text=track("ra8p1 · titan mini", 0), font=self.f.label(7),
                 fg=ON_BLUE["fg_50"], bg=BLUE, bd=0,
                 highlightthickness=0, anchor="w").pack(fill="x")

        # 01 serial
        t.eyebrow(pad, "01", "serial", **{"pady": (18, 8), "fill": "x"})
        t.kv(pad, "port", "COM4  ▾").pack(fill="x", pady=(0, 8))
        t.kv(pad, "baud", "115200").pack(fill="x", pady=(0, 12))
        t.button(pad, "connect", kind="solid").pack(fill="x")

        # 02 session
        t.eyebrow(pad, "02", "session", **{"pady": (18, 8), "fill": "x"})
        t.kv(pad, "model", "deepseek-flash").pack(fill="x", pady=(0, 8))
        row = tk.Frame(pad, bg=BLUE, bd=0, highlightthickness=0)
        row.pack(fill="x", pady=(0, 8))
        tk.Label(row, text=track("key", 1), font=self.f.label(7),
                 fg=ON_BLUE["fg_40"], bg=BLUE, anchor="w", bd=0,
                 highlightthickness=0).pack(side="left")
        tk.Label(row, text=track("set", 1), font=self.f.label(7), fg=GREEN,
                 bg=BLUE, anchor="w", bd=0, highlightthickness=0).pack(side="right")
        t.kv(pad, "clock", datetime.datetime.now().strftime("%H:%M:%S")).pack(fill="x")

        # 03 image
        t.eyebrow(pad, "03", "image", **{"pady": (18, 8), "fill": "x"})
        t.kv(pad, "queue", "5 files · 592 KB").pack(fill="x", pady=(0, 12))
        t.button(pad, "import image", kind="ghost").pack(fill="x")
        t.button(pad, "open folder", kind="ghost").pack(fill="x", pady=(6, 0))

    # -- main pane ------------------------------------------------------ #
    def _main(self, parent):
        t = self.t
        main = t.frame(parent, bg=BLUE)
        main.pack(side="left", fill="both", expand=True)
        pad = t.frame(main, bg=BLUE)
        pad.pack(fill="both", expand=True, padx=24, pady=(20, 18))

        head = t.frame(pad, bg=BLUE)
        head.pack(fill="x", pady=(0, 10))
        t.eyebrow(head, "04", "channel", **{"side": "left"})
        tk.Label(head, text=track("uart2 · 115200", 0), font=self.f.label(7),
                 fg=ON_BLUE["fg_40"], bg=BLUE, bd=0,
                 highlightthickness=0).pack(side="right")

        # prompt row is packed to the bottom first, so a tall log can never
        # push it out of the window
        prow = t.frame(pad, bg=BLUE)
        prow.pack(side="bottom", fill="x", pady=(14, 0))
        tk.Label(prow, text=track("prompt", 1), font=self.f.label(8),
                 fg=ON_BLUE["fg_60"], bg=BLUE, bd=0,
                 highlightthickness=0).pack(side="left", padx=(0, 12))
        fld = t.field(prow, text="请描述这张图片，并指出图中有什么元件或异常")
        fld.pack(side="left", fill="x", expand=True)
        t.button(prow, "send", kind="solid").pack(side="left", padx=(12, 0))

        # log card
        card = t.card(pad)
        card.pack(fill="both", expand=True)
        inner = t.frame(card, bg=ON_BLUE["fill_4"])
        inner.pack(fill="both", expand=True)

        self.log = tk.Text(
            inner, bg=ON_BLUE["fill_4"], fg=PAPER, bd=0, highlightthickness=0,
            font=self.f.mono(10), wrap="word", padx=16, pady=14,
            insertbackground=YELLOW, spacing1=2, spacing3=2, cursor="arrow",
            width=1, height=1,   # never let the widget dictate window size
        )
        self.log.pack(fill="both", expand=True)
        self.log.tag_configure("ts", foreground=ON_BLUE["fg_40"], font=self.f.mono(8))
        self.log.tag_configure("ask", foreground=YELLOW, font=self.f.label(9))
        self.log.tag_configure("ans", foreground=CYAN, font=self.f.label(9))
        self.log.tag_configure("body", foreground=PAPER, font=self.f.mono(10))
        self.log.tag_configure("dim", foreground=ON_BLUE["fg_60"], font=self.f.mono(9))
        self.log.tag_configure("err", foreground=DANGER, font=self.f.mono(9))
        self.log.tag_configure("ok", foreground=GREEN, font=self.f.mono(9))

        ghost = tk.Label(inner, text="RA8P1", font=self.f.get("display", 64, "bold"),
                         fg=mix(PAPER, BLUE, 0.085), bg=ON_BLUE["fill_4"], bd=0,
                         highlightthickness=0)
        ghost.place(relx=1.0, rely=1.0, anchor="se", x=-18, y=-6)

        self._seed_log()

    def _seed_log(self):
        e = self.log
        e.configure(state="normal")
        msgs = [
            ("12:03:58", "ask", "ask 你好",
             None),
            ("12:04:01", "ans", "A",
             "你好！我是这块板子的云端助手，已经通过以太网连上 DeepSeek。\n"
             "可以问我图片里的内容，或者直接聊固件问题。"),
            ("12:04:31", "ask", "vlm_url http://192.168.137.1:8000/img_... 描述这张图",
             None),
            ("12:04:33", "dim", "body received=7764 B", None),
            ("12:04:33", "ok", "de-chunked -> 2810 B", None),
            ("12:04:36", "ans", "A",
             "图中是一块绿色 PCB，中央有若干裸露的铜焊盘；左下角一处焊盘为空，\n"
             "周围丝印清晰，未见明显氧化。"),
        ]
        for ts, kind, who, body in msgs:
            e.insert("end", ts + "  ", "ts")
            if kind == "dim" or kind == "ok":
                e.insert("end", who + "\n", kind)
                continue
            marker = "▸ ASK" if kind == "ask" else "◂ A"
            e.insert("end", marker, kind)
            e.insert("end", "\n")
            if body:
                e.insert("end", "          " + body.replace("\n", "\n          ") + "\n", "body")
            e.insert("end", "\n")
        e.configure(state="disabled")

    # -- status bar ----------------------------------------------------- #
    def _statusbar(self):
        t = self.t
        bar = t.frame(self, bg=BLUE, height=30)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        tk.Label(bar, text=track("py 3.12 · pyserial 3.5 · http :8000", 1),
                 font=self.f.label(7), fg=ON_BLUE["fg_40"], bg=BLUE, bd=0,
                 highlightthickness=0).pack(side="left", padx=22)
        tk.Label(bar, text=track("6 msg", 1), font=self.f.label(7),
                 fg=ON_BLUE["fg_40"], bg=BLUE, bd=0,
                 highlightthickness=0).pack(side="right", padx=22)

    # ------------------------------------------------------------------ #
    def _capture(self):
        from PIL import ImageGrab
        self.update_idletasks()
        self.update()
        x, y = self.winfo_rootx(), self.winfo_rooty()
        w, h = self.winfo_width(), self.winfo_height()
        print(f"window at ({x},{y}) size {w}x{h}")
        os.makedirs(os.path.dirname(SHOT_PATH), exist_ok=True)
        ImageGrab.grab(bbox=(x, y, x + w, y + h)).save(SHOT_PATH)
        print("saved", SHOT_PATH)
        self.destroy()


if __name__ == "__main__":
    Preview(shot="--shot" in sys.argv).mainloop()
