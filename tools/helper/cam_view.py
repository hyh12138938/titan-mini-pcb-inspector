#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cam_view.py — 摄像头预览面板（可直接嵌进「电路板 AI 调试助手」）

用法（嵌入）：
    from cam_view import CameraPanel
    panel = CameraPanel(parent_frame)          # 自带 HTTP 服务 + 小窗 + 放大按钮
    panel.pack(fill="both", expand=True)

用法（独立窗口自测）：
    python cam_view.py

数据来源：板子执行
    cam_push http://192.168.137.1:8001/frame
把 320×240 RGB565 原始帧 POST 到本机的预览服务（默认 8001），本面板轮询显示。

设计：
  * 若 8001 已被 cam_web.py 占用，则直接复用（以 HTTP 客户端方式取图），不重复起服务。
  * 只用标准库 + Pillow（tkinter 内建）。
"""

import io
import json
import os
import socket
import threading
import tkinter as tk
from tkinter import ttk
from urllib.parse import urlparse
from urllib.request import urlopen

try:
    from PIL import Image, ImageTk
except ImportError:                      # pragma: no cover
    Image = None
    ImageTk = None

DEFAULT_PORT = 8001
PREVIEW_W = 320
PREVIEW_H = 240


# ---------------- 服务端（复用 cam_web 的实现） ----------------
def _ensure_server(port):
    """尝试在 port 上启动预览服务；已被占用则视为“已经在跑”。"""
    try:
        import cam_web                       # 同目录
    except Exception:
        return "no-server-module"

    srv = cam_web.Server(("0.0.0.0", port), cam_web.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return "started"


def _port_open(port, host="127.0.0.1", timeout=0.3):
    s = socket.socket()
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        return True
    except OSError:
        return False
    finally:
        s.close()


class CameraPanel(tk.Frame):
    """摄像头小窗：画面 + 放大按钮 + 状态行"""

    def __init__(self, parent, port=DEFAULT_PORT, width=PREVIEW_W, height=PREVIEW_H, **kw):
        super().__init__(parent, **kw)
        self.port = port
        self.pw = width
        self.ph = height
        self.live = True
        self._photo = None
        self._last_frames = 0
        self._last_t = 0.0
        self._fps = 0.0
        self._stat_txt = "等待板子上传…"

        if not _port_open(self.port):
            _ensure_server(self.port)

        self._build()
        self.after(300, self._poll)

    # ---------- UI ----------
    def _build(self):
        head = ttk.Frame(self)
        head.pack(fill="x")
        ttk.Label(head, text="摄像头").pack(side="left")
        self.lbl_state = ttk.Label(head, text="等待…", foreground="#888")
        self.lbl_state.pack(side="right")

        wrap = tk.Frame(self, bg="#000", width=self.pw, height=self.ph)
        wrap.pack(fill="both", expand=True, pady=(4, 4))
        wrap.pack_propagate(False)

        self.canvas = tk.Label(wrap, bg="#000", fg="#5a5a66",
                               text="等待板子上传帧…", font=("Consolas", 9))
        self.canvas.pack(fill="both", expand=True)

        bar = ttk.Frame(self)
        bar.pack(fill="x")
        self.btn_zoom = ttk.Button(bar, text="放大", width=6, command=self._zoom)
        self.btn_zoom.pack(side="left")
        self.btn_live = ttk.Button(bar, text="暂停", width=6, command=self._toggle_live)
        self.btn_live.pack(side="left", padx=4)
        ttk.Button(bar, text="刷新", width=6, command=self._poll_once).pack(side="left")
        self.lbl_info = ttk.Label(bar, text="", foreground="#666")
        self.lbl_info.pack(side="right")

    # ---------- 数据 ----------
    def _fetch(self, path, timeout=1.0):
        try:
            with urlopen("http://127.0.0.1:%d%s" % (self.port, path), timeout=timeout) as r:
                return r.read()
        except Exception:
            return None

    def _poll_once(self):
        if Image is None:
            self.lbl_state.configure(text="缺少 Pillow", foreground="#b00")
            return False

        # 先看帧计数，没变就不重新取图（省带宽、画面也不会闪）
        changed = True
        st = self._fetch("/stats", timeout=1.0)
        if st:
            try:
                s = json.loads(st.decode())
                fr = s.get("frames", 0)
                if fr == self._last_frames and self._photo is not None:
                    changed = False
                self._last_frames = fr
                self._stat_txt = "%d×%d · %d 帧 · %.1f fps" % (
                    s.get("w", 0), s.get("h", 0), fr, s.get("fps", 0.0))
                if s.get("error"):
                    self._stat_txt += " · " + s["error"][:30]
            except Exception:
                pass

        if not changed:
            self.lbl_info.configure(text=self._stat_txt)
            return True

        data = self._fetch("/latest.png")
        if not data:
            self.lbl_state.configure(text="等待…", foreground="#888")
            return False
        try:
            img = Image.open(io.BytesIO(data)).convert("RGB")
        except Exception:
            return False

        img = img.resize((self.pw, self.ph), Image.NEAREST)
        self._photo = ImageTk.PhotoImage(img)
        self.canvas.configure(image=self._photo, text="")
        self.lbl_state.configure(text="实时", foreground="#080")
        self.lbl_info.configure(text=self._stat_txt)
        return True

    def _poll(self):
        if self.live:
            self._poll_once()
        self.after(50, self._poll)   # was 90ms = 11 fps ceiling

    # ---------- 交互 ----------
    def _toggle_live(self):
        self.live = not self.live
        self.btn_live.configure(text="暂停" if self.live else "继续")
        if not self.live:
            self.lbl_state.configure(text="已暂停", foreground="#888")

    def _zoom(self):
        data = self._fetch("/latest.png")
        if not data or Image is None:
            return
        try:
            img = Image.open(io.BytesIO(data)).convert("RGB")
        except Exception:
            return
        big = img.resize((img.width * 3, img.height * 3), Image.NEAREST)
        photo = ImageTk.PhotoImage(big)

        win = tk.Toplevel(self)
        win.title("摄像头 · 放大 3×  (%d×%d)" % (img.width * 3, img.height * 3))
        lbl = tk.Label(win, image=photo, bg="#000")
        lbl.image = photo                      # 保引用
        lbl.pack()
        ttk.Button(win, text="关闭", command=win.destroy).pack(fill="x")


def open_camera_window(parent, port=DEFAULT_PORT):
    """把摄像头面板弹成一个独立窗口（给主程序一键调用）"""
    win = tk.Toplevel(parent)
    win.title("摄像头预览 — Titan Mini")
    win.geometry("340x330")
    panel = CameraPanel(win, port=port)
    panel.pack(fill="both", expand=True, padx=8, pady=8)
    return win, panel


# ---------------- 独立运行自测 ----------------
def _standalone():
    root = tk.Tk()
    root.title("cam_view 自测")
    root.geometry("340x330")
    panel = CameraPanel(root)
    panel.pack(fill="both", expand=True, padx=8, pady=8)
    root.mainloop()


if __name__ == "__main__":
    _standalone()
