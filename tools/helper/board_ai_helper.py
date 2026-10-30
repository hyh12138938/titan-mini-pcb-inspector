import sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

#!/usr/bin/env python3
"""
电路板 AI 调试助手  (Board AI Helper)
================================================
界面风格逆向自 Hermes Agent 官网（Nous Research）：
  电光蓝 #0000F2 满屏地面 / 近白 #F2F2F2 前景 / 霓虹黄青做强调
  / 方角硬边 / 等宽大写带字距的标签 / 压缩体大标题 / 1px 细线
设计 token 见 apps/ui/hermes_theme.py（从官网真实 CSS 提取）。

功能（与原版一致，仅重排布局）：
  1) 打开串口，和板子上的 AI 对话（文本走 msh 的 ask 命令）
  2) 把图片导入固定目录，选中后让板子通过 HTTP 下载再问大模型

板子侧命令（已实现）：
  ask <问题>                    纯文本
  vlm_url <url> [问题]          板子下载图片再问
  llm_key sk-xxx / date ...     配置

运行：python board_ai_helper.py
验证界面：python board_ai_helper.py --shot    （截图后退出，不出串口）
"""

import io
import os
import re
import sys
import time
import shutil
import socket
import threading
import queue
import http.server
import socketserver
import webbrowser
from urllib.parse import quote

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    print("缺少 pyserial:  pip install pyserial")
    sys.exit(1)

# 声明 DPI 感知：否则 Tk 坐标是虚拟值，字体发虚、截图错位
try:
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        ctypes.windll.user32.SetProcessDPIAware()
except Exception:
    pass

import tkinter as tk
from tkinter import filedialog, messagebox

# ---------------- 配置 ----------------
APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(APP_DIR, "ui"))

try:
    from hermes_theme import (      # noqa: E402
        Theme, ScrollArea, ON_BLUE, BLUE, PAPER, YELLOW, CYAN, GREEN, ORANGE,
        DANGER, NEUTRAL, INK, mix, track,
    )
except ImportError as e:            # 主题文件缺失时给明确提示，而不是一堆 Traceback
    print("缺少界面主题 apps/ui/hermes_theme.py :", e)
    sys.exit(1)

IMAGE_DIR = r"D:\RTT\ai_images"          # 板子下载图片的目录（也是图片仓库）
KEY_FILE = os.path.join(APP_DIR, "api_key.txt")
SHOT_PATH = r"D:\RTT\_tmp\helper_shot.png"
CAM_PORT = 8001          # frame receiver (cam_web): preview + /snap capture
HTTP_PORT = 8000
BAUD = 115200

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")

IMG_EXT = (".jpg", ".jpeg", ".png", ".gif", ".webp")


def ai_log(msg):
    import traceback, datetime
    try:
        with open(r"D:\RTT\apps\ai_debug.log", "a", encoding="utf-8") as f:
            f.write("[%s] %s\n" % (datetime.datetime.now().strftime("%H:%M:%S"), msg))
    except Exception:
        pass

def ensure_dir(p):
    if not os.path.isdir(p):
        os.makedirs(p, exist_ok=True)
    return p


def list_com_ports():
    """返回 [(device, description)]"""
    return [(p.device, (p.description or "").strip())
            for p in serial.tools.list_ports.comports()]


def port_label(dev, desc):
    if desc and desc.lower() not in ("n/a", "none"):
        return f"{dev}  {desc}"
    return dev


def is_uart_bridge(dev, desc):
    """判断是不是 USB 转串口桥（CH340/CH910/CP210x/FTDI），而不是调试探针的 CDC"""
    d = (desc or "").lower()
    for k in ("ch340", "ch341", "ch910", "cp210", "ftdi", "usb-serial",
              "usb serial", "prolific"):
        if k in d:
            return True
    if "cmsis" in d or "daplink" in d or "dap-link" in d:
        return False
    return False


def detect_pc_ip(prefer="192.168.137.1"):
    """找板子能访问到的本机 IP：优先 ICS 网卡地址"""
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if ip == prefer:
                return ip
    except Exception:
        pass
    return prefer


IMG_SOFT_LIMIT = 180 * 1024      # 超过就压缩（板子发大包容易在 TLS 读阶段失败）


def shrink_image(path, limit=IMG_SOFT_LIMIT):
    """图片超过 limit 时压缩成 <name>_s.jpg，返回实际要发送的文件路径"""
    try:
        if os.path.getsize(path) <= limit:
            return path
    except OSError:
        return path
    try:
        from PIL import Image
    except ImportError:
        return path

    try:
        im = Image.open(path)
        im = im.convert("RGB")
    except Exception:
        return path

    stem = os.path.splitext(path)[0]
    dst = stem + "_s.jpg"

    # 先降质量，再降分辨率
    for scale in (1.0, 0.8, 0.65, 0.5, 0.4, 0.3):
        w, h = im.size
        cur = im if scale == 1.0 else im.resize(
            (max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS)
        for q in (85, 80, 72, 64):
            cur.save(dst, "JPEG", quality=q, optimize=True)
            if os.path.getsize(dst) <= limit:
                return dst
    return dst


# ---------------- HTTP 文件服务 ----------------
class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, directory=None, **kwargs):
        super().__init__(*args, directory=directory, **kwargs)

    def log_message(self, fmt, *args):
        pass


class FileServer:
    def __init__(self, directory, port):
        self.directory = directory
        self.port = port
        self.httpd = None
        self.thread = None

    def start(self):
        if self.httpd:
            return True
        handler = lambda *a, **kw: QuietHandler(*a, directory=self.directory, **kw)
        socketserver.ThreadingTCPServer.allow_reuse_address = True
        self.httpd = socketserver.ThreadingTCPServer(("0.0.0.0", self.port), handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        return True

    def stop(self):
        if self.httpd:
            try:
                self.httpd.shutdown()
                self.httpd.server_close()
            except Exception:
                pass
            self.httpd = None


# ---------------- 图片卡片 ----------------
class ImageCard(tk.Frame):
    """One selectable row in the image queue: thumbnail + name + size."""

    def __init__(self, parent, app, index, name, path, size, thumb):
        super().__init__(parent, bg=ON_BLUE["fill_4"], bd=0, highlightthickness=1,
                         highlightbackground=ON_BLUE["hair"], cursor="hand2")
        self.app, self.index, self.name = app, index, name
        self.selected = False

        row = tk.Frame(self, bg=ON_BLUE["fill_4"], bd=0, highlightthickness=0)
        row.pack(fill="x", padx=8, pady=7)

        # thumbnail well
        well = tk.Frame(row, bg=ON_BLUE["fill_10"], width=88, height=66, bd=0,
                        highlightthickness=0)
        well.pack(side="left")
        well.pack_propagate(False)
        if thumb is not None:
            lbl = tk.Label(well, image=thumb, bg=ON_BLUE["fill_10"], bd=0,
                           highlightthickness=0)
            lbl.image = thumb
            lbl.pack(expand=True)
        else:
            tk.Label(well, text=track("no", 1), font=app.t.f.label(7),
                     fg=ON_BLUE["fg_40"], bg=ON_BLUE["fill_10"], bd=0,
                     highlightthickness=0).pack(expand=True)

        meta = tk.Frame(row, bg=ON_BLUE["fill_4"], bd=0, highlightthickness=0)
        meta.pack(side="left", fill="both", expand=True, padx=(10, 0))
        short = name if len(name) <= 16 else name[:13] + "…"
        tk.Label(meta, text=short, font=app.t.f.mono(9), fg=PAPER,
                 bg=ON_BLUE["fill_4"], anchor="w", bd=0,
                 highlightthickness=0).pack(fill="x")
        tk.Label(meta, text=f"{size/1024:.0f} KB", font=app.t.f.label(7),
                 fg=ON_BLUE["fg_50"], bg=ON_BLUE["fill_4"], anchor="w", bd=0,
                 highlightthickness=0).pack(fill="x", pady=(4, 0))
        self.mark = tk.Label(meta, text="", font=app.t.f.label(7), fg=YELLOW,
                             bg=ON_BLUE["fill_4"], anchor="w", bd=0,
                             highlightthickness=0)
        self.mark.pack(fill="x", pady=(4, 0))

        for w in (self, row, well, meta):
            w.bind("<Button-1>", lambda e: app.select_image(index))
            w.bind("<Double-Button-1>", lambda e: app.preview_image(index))

    def set_selected(self, on):
        self.selected = on
        bg = ON_BLUE["fill_10"] if on else ON_BLUE["fill_4"]
        self.configure(highlightbackground=YELLOW if on else ON_BLUE["hair"],
                       bg=bg)
        for child in self.winfo_children():
            child.configure(bg=bg)
            for sub in child.winfo_children():
                try:
                    if sub.cget("bg") != ON_BLUE["fill_10"]:
                        sub.configure(bg=bg)
                except Exception:
                    pass
        self.mark.configure(text=track("selected", 1) if on else "")


# ---------------- 主界面 ----------------
_FONT_CP = None
def _font_cp():
    global _FONT_CP
    if _FONT_CP is None:
        import re as _re
        try:
            t = io.open(r"D:\RTT\sdk-bsp-ra8p1-titan-mini\project\Titan_Mini_eth_cam\src\sch_font.h",
                        encoding="utf-8").read()
            head = t[:t.index("};", t.index("s_font_cp"))]
            _FONT_CP = set(int(c, 16) for c in _re.findall(r"0x([0-9A-F]{4})", head))
        except Exception:
            _FONT_CP = set()
    return _FONT_CP

def font_safe(s):
    """只保留板端字库能显示的字，避免出现空白方块"""
    cps = _font_cp()
    if not cps:
        return s
    return "".join(c for c in s if ord(c) in cps)

SYM_MAP = {"Ω": "欧", "µ": "微", "μ": "微", "±": "正负", "°": "度",
           "①": "1", "②": "2", "③": "3", "≈": "约", "≤": "小于等于", "≥": "大于等于"}
def sym(s):
    for k, v in SYM_MAP.items():
        s = s.replace(k, v)
    return s

def clean_pwr(s, maxlen=18):
    toks = re.split(r"[,，、/\s]+", s)
    cur = ""
    for t in toks:
        t = t.strip("。；;：:")
        if not t:
            continue
        if re.fullmatch(r"\d+(\.\d+)?", t) or len(t) == 1:
            continue
        if t in cur.split(","):
            continue
        cand = t if not cur else cur + "," + t
        if len(cand) > maxlen and cur:
            break
        cur = cand
    return cur


class BoardApp(tk.Tk):
    W, H = 1360, 860

    def __init__(self, shot=False):
        super().__init__()
        self.shot = shot
        self.title("电路板 AI 调试助手  —  Titan Mini / RA8P1")
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = min(self.W, sw - 80), min(self.H, sh - 120)
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")
        self.minsize(1120, 700)
        self.configure(bg=BLUE)

        self.t = Theme(self)
        self.f = self.t.f

        ensure_dir(IMAGE_DIR)
        self.ser = None
        self.rxq = queue.Queue()
        self.http_ip = detect_pc_ip()
        self.srv = FileServer(IMAGE_DIR, HTTP_PORT)
        self.img_files = []          # [(name, size)]
        self.selected = None
        self._thumbs = []            # keep PhotoImage refs alive
        self._cards = []
        self._last_image_set = set()

        # ---- state variables ----
        self.var_port = tk.StringVar(value="NO DEVICE")
        self.var_baud = tk.StringVar(value=str(BAUD))
        self.var_link = tk.StringVar(value=track("offline", 1))
        self.var_key = tk.StringVar(value=track("not set", 1))
        self.var_clock = tk.StringVar(value="--:--:--")
        self.var_queue = tk.StringVar(value="0 files")
        self.var_http = tk.StringVar(value=f":{HTTP_PORT}")
        self.var_status = tk.StringVar(value="就绪")
        self.var_compress = tk.BooleanVar(value=False)
        self.var_autokey = tk.BooleanVar(value=True)
        self.var_cap = tk.StringVar(value="ok 0 · missing 0")

        self._build()
        self._refresh_ports()
        self._refresh_images()
        self._start_server()
        self._load_key(silent=True)
        self._tick_clock()

        self._refresh_counts()
        self.after(80, self._poll_serial)
        self.after(3000, self._auto_refresh_images)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        if shot:
            self.overrideredirect(True)      # 无边框截图，只要画面
            self.attributes("-topmost", True)
            self.lift()
            self.focus_force()
            self.after(1200, self._capture)

    # ------------------------------------------------------------------ #
    # 构建界面
    # ------------------------------------------------------------------ #
    def _build(self):
        t = self.t
        self._topbar()
        t.rule(self, thickness=1)

        body = t.frame(self)
        body.pack(fill="both", expand=True)
        self._sidebar(body)
        t.vrule(body, color=ON_BLUE["hair"])
        self._channel(body)
        t.vrule(body, color=ON_BLUE["hair"])
        self._queue(body)

        t.rule(self, thickness=1)
        self._statusbar()

    # -- 顶栏 ----------------------------------------------------------- #
    def _topbar(self):
        t = self.t
        bar = t.frame(self, bg=BLUE, height=56)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        left = t.frame(bar, bg=BLUE)
        left.pack(side="left", fill="y", padx=(22, 0))
        mark = tk.Canvas(left, width=16, height=16, bg=BLUE, bd=0,
                         highlightthickness=0)
        mark.create_rectangle(0, 0, 15, 15, outline=PAPER, width=1)
        mark.create_rectangle(4, 4, 11, 11, fill=YELLOW, outline="")
        mark.pack(side="left", pady=(1, 0))
        tk.Label(left, text=track("hermes", 1), font=self.f.label(10), fg=PAPER,
                 bg=BLUE, bd=0, highlightthickness=0).pack(side="left", padx=(10, 0))
        tk.Label(left, text="/", font=self.f.mono(10), fg=ON_BLUE["fg_40"],
                 bg=BLUE, bd=0, highlightthickness=0).pack(side="left", padx=10)
        tk.Label(left, text=track("board ai console", 1), font=self.f.label(8),
                 fg=ON_BLUE["fg_60"], bg=BLUE, bd=0,
                 highlightthickness=0).pack(side="left")

        right = t.frame(bar, bg=BLUE)
        right.pack(side="right", fill="y", padx=(0, 22))
        t.button(right, "clear", kind="ghost", command=self._clear)\
            .pack(side="right", padx=(8, 0), pady=13)
        t.button(right, "date", kind="ghost", command=self._send_date)\
            .pack(side="right", padx=(8, 0), pady=13)
        t.button(right, "demo", kind="ghost", command=self._open_demo)\
            .pack(side="right", padx=(8, 0), pady=13)

        state = t.frame(right, bg=BLUE)
        state.pack(side="right", padx=(0, 16), pady=13)
        self.dot_link = t.dot(state, ON_BLUE["fg_40"])
        self.dot_link.pack(side="left")
        tk.Label(state, textvariable=self.var_link, font=self.f.label(8), fg=PAPER,
                 bg=BLUE, bd=0, highlightthickness=0).pack(side="left", padx=(8, 0))

    # -- 左栏：串口 / 会话 / 图片 ---------------------------------------- #
    def _sidebar(self, parent):
        t = self.t
        side = t.frame(parent, bg=BLUE, width=326)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)
        pad = t.frame(side, bg=BLUE)
        pad.pack(fill="both", expand=True, padx=22, pady=(18, 16))

        # Hero plate. Tk frames cannot be transparent, so instead of layering
        # type over an image the image is the canvas and the type is drawn into
        # it - the only way a Tk window gets a real picture on its face.
        hero = tk.Canvas(pad, width=282, height=150, bg=BLUE, bd=0,
                         highlightthickness=0)
        hero.pack(fill="x", pady=(0, 6))
        plate = self._banner()
        if plate is not None:
            self._banner_img = plate
            hero.create_image(0, 0, image=plate, anchor="nw")
        hero.create_text(4, 16, text="BOARD AI", font=self.f.hero(22),
                         fill=PAPER, anchor="nw")
        hero.create_rectangle(4, 50, 44, 53, fill=YELLOW, outline="")
        hero.create_text(4, 58, text="RA8P1 · TITAN MINI", font=self.f.label(6),
                         fill=ON_BLUE["fg_60"], anchor="nw")

        # 01 serial
        t.eyebrow(pad, "01", "serial", **{"pady": (11, 5), "fill": "x"})
        t.label_text(pad, "port", size=7, color=ON_BLUE["fg_40"], **{"fill": "x"})
        t.dropdown(pad, self.var_port, self._port_options,
                   on_open=self._refresh_ports).pack(fill="x", pady=(4, 8))
        t.label_text(pad, "baud", size=7, color=ON_BLUE["fg_40"], **{"fill": "x"})
        t.dropdown(pad, self.var_baud,
                   lambda: [(b, b) for b in
                            ("115200", "230400", "460800", "921600")])\
            .pack(fill="x", pady=(4, 10))
        self.btn_conn = t.button(pad, "connect", command=self._toggle_serial)
        self.btn_conn.pack(fill="x")

        # camera preview（新增：板子 cam_push 推帧，这里开小窗看）
        self.btn_cam = t.button(pad, "camera preview", command=self._open_camera)
        self.btn_cam.pack(fill="x", pady=(8, 0))

        # 图纸检测：一键 发送原理图 -> 板子识别 -> LCD 显示（带框选 + 建议）
        self.btn_sch = t.button(pad, "send schematic", command=self._send_schematic)
        self.btn_sch.pack(fill="x", pady=(8, 0))
        self.btn_pick = t.button(pad, "choose drawing…", kind="ghost",
                                 command=self._choose_drawing)
        self.btn_pick.pack(fill="x", pady=(4, 0))
        self.btn_schcam = t.button(pad, "camera mode", kind="ghost",
                                   command=self._send_camera_mode)
        self.btn_schcam.pack(fill="x", pady=(4, 0))
        # 快捷键：F5 = 发送原理图（与按钮同一函数）；F6 = 切回摄像头
        try:
            self.bind("<F5>", lambda _e: self._send_schematic())
            self.bind("<F6>", lambda _e: self._send_camera_mode())
            self.bind("<F7>", lambda _e: self._send_line("sch_snap"))   # 调试：刷新截图缓冲
            self.bind("<F4>", lambda _e: self._choose_drawing())
        except Exception:
            pass
        # 开机自动连串口（静默，失败不弹窗）
        self.after(900, self._auto_connect_silent)

        # 02 session
        t.eyebrow(pad, "02", "session", **{"pady": (11, 5), "fill": "x"})

        row = tk.Frame(pad, bg=BLUE, bd=0, highlightthickness=0)
        row.pack(fill="x", pady=(0, 6))
        tk.Label(row, text=track("model", 1), font=self.f.label(7),
                 fg=ON_BLUE["fg_40"], bg=BLUE, anchor="w", bd=0,
                 highlightthickness=0).pack(side="left")
        tk.Label(row, text="deepseek-flash", font=self.f.mono(9), fg=CYAN,
                 bg=BLUE, anchor="w", bd=0, highlightthickness=0).pack(side="right")

        row = tk.Frame(pad, bg=BLUE, bd=0, highlightthickness=0)
        row.pack(fill="x", pady=(0, 6))
        tk.Label(row, text=track("key", 1), font=self.f.label(7),
                 fg=ON_BLUE["fg_40"], bg=BLUE, anchor="w", bd=0,
                 highlightthickness=0).pack(side="left")
        self.lbl_key = tk.Label(row, textvariable=self.var_key, font=self.f.label(7),
                                fg=ON_BLUE["fg_50"], bg=BLUE, anchor="w", bd=0,
                                highlightthickness=0)
        self.lbl_key.pack(side="right")

        fld = t.field(pad, height=30)
        fld.pack(fill="x", pady=(0, 6))
        fld.ent.configure(show="*")
        self.ent_key = fld.ent
        self.ent_key.bind("<KeyRelease>", lambda e: self._sync_key_state())

        kb = tk.Frame(pad, bg=BLUE, bd=0, highlightthickness=0)
        kb.pack(fill="x", pady=(0, 8))
        t.button(kb, "push", kind="ghost", command=self._send_key)\
            .pack(side="left", fill="x", expand=True)
        t.button(kb, "save", kind="ghost", command=self._save_key)\
            .pack(side="left", fill="x", expand=True, padx=(6, 0))

        t.kv_var(pad, "clock", self.var_clock).pack(fill="x", pady=(0, 6))
        t.checkbox(pad, "AUTO PUSH KEY ON CONNECT", self.var_autokey)\
            .pack(fill="x", pady=(0, 4))



    def _banner(self):
        try:
            from PIL import Image, ImageTk
            p = os.path.join(APP_DIR, "ui", "assets", "hero_plate.jpg")
            return ImageTk.PhotoImage(Image.open(p))
        except Exception:
            return None

    def _port_options(self):
        if not getattr(self, "ports", None):
            return [("no device", "NO DEVICE")]
        return [(port_label(d, s), d) for d, s in self.ports]

    # -- 中栏：日志 ------------------------------------------------------ #
    def _channel(self, parent):
        t = self.t
        main = t.frame(parent, bg=BLUE)
        main.pack(side="left", fill="both", expand=True)
        pad = t.frame(main, bg=BLUE)
        pad.pack(fill="both", expand=True, padx=24, pady=(18, 16))

        head = t.frame(pad, bg=BLUE)
        head.pack(fill="x", pady=(0, 10))
        t.eyebrow(head, "04", "channel", **{"side": "left"})
        tk.Label(head, text="UART2 · 115200 8N1", font=self.f.label(7),
                 fg=ON_BLUE["fg_40"], bg=BLUE, bd=0,
                 highlightthickness=0).pack(side="right")

        # prompt row 先 pack 到底部，日志再大也挤不掉它
        prow = t.frame(pad, bg=BLUE)
        prow.pack(side="bottom", fill="x", pady=(12, 0))
        tk.Label(prow, text=track("prompt", 1), font=self.f.label(8),
                 fg=ON_BLUE["fg_60"], bg=BLUE, bd=0,
                 highlightthickness=0).pack(side="left", padx=(0, 12))
        fld = t.field(prow, height=34)
        fld.pack(side="left", fill="x", expand=True)
        self.ent_send = fld.ent
        self.ent_send.insert(0, "你好")
        self.ent_send.bind("<Return>", lambda e: self._send_text())
        t.button(prow, "send", kind="solid", command=self._send_text)\
            .pack(side="left", padx=(12, 0))

        # capture bar: two labelled shots for the binary dataset, plus resume
        capbar = t.frame(pad, bg=BLUE)
        capbar.pack(side="bottom", fill="x", pady=(10, 0))
        tk.Label(capbar, text=track("capture", 1), font=self.f.label(8),
                 fg=YELLOW, bg=BLUE, bd=0,
                 highlightthickness=0).pack(side="left", padx=(0, 12))
        t.button(capbar, "ok", kind="ghost", command=lambda: self._capture("ok"))\
            .pack(side="left", fill="x", expand=True)
        t.button(capbar, "missing", kind="ghost",
                 command=lambda: self._capture("missing"))\
            .pack(side="left", fill="x", expand=True, padx=(6, 0))
        t.button(capbar, "live", kind="ghost", command=self._resume_stream)\
            .pack(side="left", padx=(6, 0))
        tk.Label(capbar, textvariable=self.var_cap, font=self.f.mono(9),
                 fg=ON_BLUE["fg_60"], bg=BLUE, bd=0,
                 highlightthickness=0).pack(side="right", padx=(10, 0))

        opt = t.frame(pad, bg=BLUE)
        opt.pack(side="bottom", fill="x", pady=(8, 0))
        t.checkbox(opt, "COMPRESS IMAGE > 180 KB  (DEFAULT: SEND ORIGINAL)",
                   self.var_compress).pack(side="left")

        card = t.card(pad)
        card.pack(fill="both", expand=True)
        inner = t.frame(card, bg=ON_BLUE["fill_4"])
        inner.pack(fill="both", expand=True)

        ghost = tk.Label(inner, text="RA8P1", font=self.f.get("display", 60, "bold"),
                         fg=mix(PAPER, BLUE, 0.075), bg=ON_BLUE["fill_4"], bd=0,
                         highlightthickness=0)
        ghost.place(relx=1.0, rely=1.0, anchor="se", x=-18, y=-6)

        self.txt = tk.Text(inner, bg=ON_BLUE["fill_4"], fg=PAPER, bd=0,
                           highlightthickness=0, font=self.f.mono(10),
                           wrap="word", padx=16, pady=14,
                           insertbackground=YELLOW, spacing1=2, spacing3=2,
                           width=1, height=1, cursor="arrow")
        self.txt.pack(fill="both", expand=True)
        self.txt.tag_configure("dim", foreground=ON_BLUE["fg_60"],
                               font=self.f.mono(9))
        self.txt.tag_configure("ok", foreground=GREEN, font=self.f.mono(9))
        self.txt.tag_configure("err", foreground=DANGER, font=self.f.mono(9))
        self.txt.tag_configure("ans", foreground=CYAN, font=self.f.mono(10))
        self.txt.tag_configure("hint", foreground=YELLOW, font=self.f.label(8))
        self.txt.configure(state="disabled")

        self._append(track("ready", 1) + "\n"
                     "  1) 端口选 CH340 那个（COM4），不是 DAP 探针的 CDC\n"
                     "  2) 打开串口后会自动发一次回车和 API Key\n"
                     "  3) 提问前先点 DATE 对时，否则 TLS 会因证书有效期失败\n",
                     tag="dim")

    # -- 右栏：图片队列 -------------------------------------------------- #
    def _queue(self, parent):
        t = self.t
        side = t.frame(parent, bg=BLUE, width=346)
        side.pack(side="right", fill="y")
        side.pack_propagate(False)
        pad = t.frame(side, bg=BLUE)
        pad.pack(fill="both", expand=True, padx=20, pady=(18, 16))

        head = t.frame(pad, bg=BLUE)
        head.pack(fill="x", pady=(0, 10))
        t.eyebrow(head, "05", "queue", **{"side": "left"})
        tk.Label(head, textvariable=self.var_queue, font=self.f.label(7),
                 fg=ON_BLUE["fg_40"], bg=BLUE, bd=0,
                 highlightthickness=0).pack(side="right")

        self.btn_send_img = t.button(pad, "send image", command=self._send_image)
        self.btn_send_img.pack(side="bottom", fill="x", pady=(10, 0))
        t.button(pad, "refresh queue", kind="ghost", command=self._refresh_images)\
            .pack(side="bottom", fill="x", pady=(8, 0))
        ib = tk.Frame(pad, bg=BLUE, bd=0, highlightthickness=0)
        ib.pack(side="bottom", fill="x", pady=(8, 0))
        t.button(ib, "import", kind="ghost", command=self._import_images)\
            .pack(side="left", fill="x", expand=True)
        t.button(ib, "folder", kind="ghost", command=self._open_folder)\
            .pack(side="left", fill="x", expand=True, padx=(6, 0))

        self.qscroll = ScrollArea(pad, t, bg=BLUE)
        self.qscroll.pack(fill="both", expand=True)

    # -- 底栏 ----------------------------------------------------------- #
    def _statusbar(self):
        t = self.t
        bar = t.frame(self, bg=BLUE, height=30)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        tk.Label(bar, textvariable=self.var_status, font=self.f.label(7),
                 fg=ON_BLUE["fg_50"], bg=BLUE, bd=0,
                 highlightthickness=0).pack(side="left", padx=22)
        tk.Label(bar, text=track("v2 · 2026-10-22", 1),
                 font=self.f.label(7), fg=ON_BLUE["fg_40"], bg=BLUE, bd=0,
                 highlightthickness=0).pack(side="right", padx=22)

    # ------------------------------------------------------------------ #
    # 串口
    # ------------------------------------------------------------------ #
    def _set_status(self, msg):
        self.var_status.set(msg)

    def _refresh_ports(self):
        self.ports = list_com_ports()
        cur = self.var_port.get()
        want = cur if any(d == cur for d, _ in self.ports) else None
        if not want and self.ports:
            want = self.ports[0][0]
            for d, s in self.ports:
                if is_uart_bridge(d, s):
                    want = d
                    break
        self.var_port.set(want or "NO DEVICE")
        names = ", ".join(d for d, _ in self.ports) if self.ports else "未发现串口"
        self._set_status(names)

    def _selected_device(self):
        v = (self.var_port.get() or "").strip()
        if not v or v.upper() == "NO DEVICE":
            return ""
        return v.split()[0]

    def send_on_start(self, path):
        """--send <file>：启动后自动走一遍 打包->发送（与按钮同一函数）"""
        self.after(3000, lambda: self.pack_and_send(path))

    def _auto_connect_silent(self):
        if self.ser and self.ser.is_open:
            return
        try:
            if self._selected_device():
                self._toggle_serial()
        except Exception:
            pass

    # ---------- 图纸检测（小助手侧一键） ----------
    SCH_PORT = 8002
    SCH_DIR = r"D:\RTT\sch\serve"
    SCH_FILE = "sch_150.bin"

    def _ensure_sch_server(self):
        """确保 8002 上能取到原理图位图（没起就起一个静态服务）"""
        import socket as _socket
        try:
            with _socket.create_connection(("127.0.0.1", self.SCH_PORT), timeout=0.3):
                return True
        except Exception:
            pass
        try:
            srv = FileServer(self.SCH_DIR, self.SCH_PORT)
            srv.start()
            self._sch_srv = srv
            return True
        except Exception as exc:
            self._set_status("原理图服务启动失败: %s" % exc)
            return False

    def _pc_ip_for_board(self):
        try:
            ip = detect_pc_ip(prefer="192.168.137.1")
        except Exception:
            ip = None
        return ip or "192.168.137.1"

    SCH_FILE_PATH = r"D:\RTT\sch\serve\sch_150.bin"
    PACK_TOOL = r"D:\RTT\sch\pack_any.py"

    def _choose_drawing(self):
        """选一张原理图（PDF/PNG/JPG）-> 自动归一化打包 -> 发给板子"""
        import tkinter.filedialog as fd
        p = fd.askopenfilename(
            title="选择原理图（PDF / PNG / JPG）",
            initialdir=os.path.expanduser(r"~\Downloads"),
            filetypes=[("原理图", "*.pdf *.png *.jpg *.jpeg"), ("所有文件", "*.*")])
        if p:
            self.pack_and_send(p)

    def pack_and_send(self, path):
        if path.lower().endswith(".bin"):
            import shutil
            shutil.copyfile(path, self.SCH_FILE_PATH)
            self._append("[pack] 直接用已打包位图 %s\n" % os.path.basename(path), tag="dim")
            self._send_schematic()
            return
        self._set_status("正在打包图纸…")
        self._append("[pack] %s\n" % path, tag="dim")

        def work():
            import subprocess
            try:
                r = subprocess.run(
                    [sys.executable, self.PACK_TOOL, "--in", path,
                     "--out", self.SCH_FILE_PATH],
                    capture_output=True, text=True, encoding="utf-8", errors="replace",
                    timeout=180)
            except Exception as exc:
                self.after(0, lambda: self._set_status("打包异常: %s" % exc))
                return
            self.after(0, lambda: self._after_pack(r, path))

        threading.Thread(target=work, daemon=True).start()

    def _after_pack(self, r, path):
        self._last_src = path
        out = (r.stdout or "").strip().splitlines()
        for line in out[-4:]:
            self._append("  " + line + "\n", tag="dim")
        if r.returncode != 0:
            self._set_status("打包失败，看日志")
            self._append((r.stderr or "")[-400:] + "\n", tag="dim")
            return
        self._send_schematic()

    PROMPT = (
     "这是同一张电子原理图按田字格切成的 4 块（左上/右上/左下/右下）。\n"
     "板端已用模板检出：{RULE}（若其中含负电源如 -5V，则说明该电路是双电源；此信息仅作参考，不要复述）\n"
     "已知事实：TL084 不是轨到轨运放，单电源下输出到不了 0V，禁止声称它有轨到轨能力。\n"
 "只输出下面 4 行，严格遵守字数，不要解释、不要分析过程：\n"
     "功能：<电路用途，不超过18字；若检出负电源，不得写“单电源”>\n"
     "电源：<只列图上标注的电源网络名，逗号分隔，不超过18字>\n"
     "短接：<判断两个电源网络之间是否只隔一个小于等于100欧的电阻。必须能在图上指出该电阻的阻值以及它两端各接哪个电源网络；报不出具体阻值就回答 无。标注 DNP 或 NC 的元件不算。不超过22字>\n"
     "建议：<必须与上面“电源”项一致：若电源项含负电源(如 -5V)，按双电源给建议且全文禁止出现“单电源”字样；若不含负电源，才可针对 TL084 单电源输出摆幅给建议。不超过34字>\n"
    )

    def _after_load_check(self):
        self._send_line("sch_ai_wait")
        self.after(500, lambda: self._send_line("sch_check"))
        threading.Thread(target=self._ai_worker, daemon=True).start()

    def _ai_worker(self):
        import base64, io, json, struct, urllib.request
        try:
            import numpy as np
            from PIL import Image
        except Exception as exc:
            self._append("[ai] missing lib: %s\n" % exc, tag="dim")
            self._send_line("sch_ai_err")
            return
        try:
            ai_log("worker start")
            time.sleep(3.0)                       # 等板子跑完 sch_check，规则文本才可解析
            d = open(self.SCH_FILE_PATH, "rb").read()
            w, h, st, pay = struct.unpack("<HHII", d[4:16])
            bits = np.frombuffer(d[16:16 + pay], np.uint8).reshape(h, st)
            ink = np.unpackbits(bits, axis=1, bitorder="little")[:, :w]
            img = Image.fromarray(((1 - ink) * 255).astype(np.uint8)).convert("L")
            tiles = []
            for ty in range(2):
                for tx in range(2):
                    x0, y0 = tx * w // 2, ty * h // 2
                    t = img.crop((x0, y0, min(w, x0 + w // 2 + 40), min(h, y0 + h // 2 + 40)))
                    if t.width > 1280 or t.height > 1280:
                        k = min(1280.0 / t.width, 1280.0 / t.height)
                        t = t.resize((int(t.width * k), int(t.height * k)), Image.LANCZOS)
                    b = io.BytesIO()
                    t.save(b, "JPEG", quality=85)
                    tiles.append(base64.b64encode(b.getvalue()).decode())
            ai_log("tiles built, %d KB" % (sum(len(x) for x in tiles) // 1024))
            key = self._read_key()
            if not key:
                self._append("[ai] no api key\n", tag="dim")
                self._send_line("sch_ai_err")
                return
            d = self._detect()
            base_prompt = self._build_prompt(d)
            feedback = ""
            f = None
            for attempt in range(3):
                content = [{"type": "text", "text": base_prompt + feedback}]
                for t64 in tiles:
                    content.append({"type": "image_url",
                                    "image_url": {"url": "data:image/jpeg;base64," + t64,
                                                  "detail": "original"}})
                body = {"model": "deepseek-flash", "temperature": 0, "max_tokens": 420,
                        "thinking": {"type": "disabled"},
                        "messages": [{"role": "user", "content": content}]}
                req = urllib.request.Request("https://api.deepseek.com/chat/completions",
                    data=json.dumps(body).encode(),
                    headers={"Content-Type": "application/json",
                             "Authorization": "Bearer " + key})
                if attempt == 0:
                    ai_log("asking cloud, rule=%s" % self._rule_text())
                    self._append("[ai] asking cloud (4 tiles, %d KB)...\n"
                                 % (sum(len(x) for x in tiles) // 1024), tag="dim")
                t0 = time.time()
                with urllib.request.urlopen(req, timeout=180) as r:
                    j = json.loads(r.read().decode())
                text = j["choices"][0]["message"]["content"]
                ai_log("raw(%d) %.1fs: %s" % (attempt + 1, time.time() - t0,
                                              text.replace(chr(10), " / ")[:280]))
                f = self._parse_ai(text)
                if f is None:
                    ai_log("PARSE FAILED")
                    feedback = (chr(10) + "上次没按格式输出。必须严格只输出 4 行："
                                + chr(10) + "功能：…" + chr(10) + "电源：…"
                                + chr(10) + "短接：…" + chr(10) + "建议：…" + chr(10))
                    continue
                bad = self._advice_bad(f["建议"], d, f.get("功能", ""), f.get("电源", ""), f.get("短接", ""))
                if not bad:
                    break
                ai_log("advice rejected (%s): %s" % (bad, f["建议"]))
                feedback = (chr(10) + "上次的“建议”不合格（%s）。重新输出 4 行；"
                            "“建议”必须是一条图上尚未做到的具体改进，"
                            "禁止把图上已经做到的事当建议（图上已有双电源就不能建议采用双电源）。"
                            "确实没有可改进项就写 无。" % bad) + chr(10)
            if f is None:
                self._send_line("sch_ai_err")
                return
            ai_log("parsed: %r" % (f,))
            self._send_line("sch_ai %s@%s@%s@%s" % (f["功能"], f["电源"], f["短接"], f["建议"]))
            self._append("[ai] 上屏: %s | %s | %s\n"
                         % (f["功能"], f["电源"], f["短接"]), tag="dim")
            ai_log("pushed to board")
            time.sleep(1.5)
            self._send_line("sch_snap")          # 结果上屏后重拍快照
        except Exception as exc:
            ai_log("EXCEPTION: %r" % (exc,))
            import traceback as _tb
            ai_log(_tb.format_exc()[:1200])
            self._append("[ai] failed: %s\n" % exc, tag="dim")
            try:
                self._send_line("sch_ai_err")
            except Exception:
                pass



    def _parse_ai(self, text):
        import re
        out = {}
        for k in ("功能", "电源", "短接", "建议"):
            m = re.search(k + r"\s*[：:]\s*(.+)", text)
            if not m:
                return None
            out[k] = m.group(1).strip().split("\n")[0].strip()
        lim = {"功能": 20, "电源": 60, "短接": 22, "建议": 46}
        for k, n in lim.items():
            if len(out[k]) > n:
                out[k] = out[k][:n]
        out["短接"] = font_safe(sym(out["短接"]))
        out["建议"] = font_safe(sym(out["建议"]))
        out["电源"] = clean_pwr(font_safe(sym(out["电源"])), 18)
        return out

    def _read_key(self):
        try:
            with open(KEY_FILE, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            return ""

    def _detect(self):
        """从串口日志里取最近一次 sch_check 的检出结果"""
        import re
        buf = getattr(self, "_logbuf", "")

        def last(pat, yes):
            m = None
            for m in re.finditer(pat, buf):
                pass
            return (m is not None) and (m.group(1) in yes)

        return {
            "tl": last(r"TL084\s*:\s*(FOUND|absent)", ("FOUND",)),
            "p5": last(r"5V\s*:\s*(FOUND|missing)", ("FOUND",)),
            "n5": last(r"-5V\s*:\s*(FOUND|absent)", ("FOUND",)),
        }

    def _rule_text(self):
        d = self._detect()
        pos = []
        if d["tl"]:
            pos.append("TL084")
        if d["p5"]:
            pos.append("+5V")
        if d["n5"]:
            pos.append("-5V")
        return "、".join(pos) if pos else "无"

    def _advice_bad(self, adv, d, fct="", pwr="", short=""):
        import re as _re
        if not adv or not adv.strip():
            return "建议为空"
        a = adv.strip()
        if not d["tl"] and "TL084" in a:
            return "提及了未检出的 TL084"
        if d["n5"] and "单电源" in a:
            return "本图有负电源，却提单电源"
        if d["n5"] and any(w in a for w in ("双电源供电", "采用双电源", "使用双电源", "改为双电源",
                                            "换成双电源", "加双电源", "增加双电源",
                                            "采用负电源", "增加负电源", "加负电源")):
            return "建议了图上已经存在的双电源/负电源"
        if a in ("无", "无需", "无需修改", "无改进", "无建议", "暂无"):
            return None
        if not any(w in a for w in ("注意", "建议", "检查", "核对", "确认", "考虑", "增加",
                                    "减小", "调整", "加", "换", "改", "优化", "核实", "避免",
                                    "钳位", "限流", "布线", "靠近", "串", "并", "排查", "测")):
            return "不像一条改进建议（疑似复述图上现状）"
        sh = (short or "").strip()
        if sh[:1] in ("是", "有"):
            if ("短接" not in a) and not _re.search(r"R\d+", a) and ("欧" not in a) and ("Ω" not in a):
                return "本图已检出短接，建议必须先针对该短接（写明位号/阻值）"
        toks = set()
        for src in (pwr or "", fct or ""):
            toks |= set(_re.findall(r"[A-Za-z][A-Za-z0-9_]{2,}", src))
            toks |= set(_re.findall(r"[+-]?\d+V\d*", src))
        if not d["tl"]:
            toks.discard("TL084")
        if toks and not any(t in a for t in toks):
            return "没有引用本图的具体网络/器件名（本图可用：%s）" % "/".join(sorted(toks)[:6])
        return None

    def _build_prompt(self, d):
        """提示词按实际检出动态生成：没检出 TL084 就明令禁止提它"""
        parts = []
        if d["tl"]:
            parts.append("TL084")
        if d["p5"]:
            parts.append("+5V")
        if d["n5"]:
            parts.append("-5V")
        L = ["这是同一张电子原理图按田字格切成的 4 块（左上/右上/左下/右下）。",
             "板端已用模板检出：%s（仅作参考，不要复述）" % ("、".join(parts) if parts else "无")]
        if d["tl"]:
            L.append("已知事实：TL084 不是轨到轨运放，单电源下输出到不了 0V。")
        else:
            L.append("本图未检出 TL084：建议中禁止出现 TL084 字样，也不要提任何运放轨到轨、"
                     "单电源摆幅、换运放型号之类的内容。")
        if d["n5"]:
            L.append("本图检出负电源（-5V）：建议中禁止出现“单电源”字样，必须按双电源表述。")
        else:
            L.append("本图未检出负电源。")
        L += ["只输出下面 4 行，严格遵守字数，不要解释、不要分析过程：",
              "功能：<电路用途，不超过18字>",
              "电源：<只列图上标注的电源网络名，逗号分隔，不超过18字>",
              "短接：<判断两个电源网络之间是否只隔一个小于等于100欧的电阻。必须能在图上指出该电阻的阻值"
              "以及它两端各接哪个电源网络；报不出具体阻值就回答 无。标注 DNP 或 NC 的元件不算。不超过22字>",
              "建议：<必须针对本图这类电路的功能特点来提，而不是通用保护；"
 "并且必须写出本图“电源”或“功能”里出现过的一个具体网络名或器件位号（如 +3V3、VSYS_5V、BIAS_2V5、R21）。"
 "放大器电路看输出摆幅/偏置/带宽/失真；电源树看负载能力/纹波/上电时序/效率。"
 "**若“短接”项为有，建议必须首先针对该短接（写出电阻位号或阻值，说明需确认是否为设计意图）**。"
 "禁止把图上已经做到的事当建议：图上已有负电源就不得建议“采用/增加双电源或负电源”；"
 "图上已有去耦电容就不得建议“加去耦”。若没有可改进项，直接写 无。不超过34字>"]
        return chr(10).join(L) + chr(10)

    def _send_schematic(self):
        if not (self.ser and self.ser.is_open):
            messagebox.showwarning("提示", "请先 connect 串口")
            return
        if not self._ensure_sch_server():
            return
        url = "http://%s:%d/%s" % (self._pc_ip_for_board(), self.SCH_PORT,
                            os.path.basename(self.SCH_FILE_PATH))
        self._set_status("图纸模式：发送中…")
        self._send_line("sch_mode on")
        self.after(300, lambda: self._send_line("sch_load " + url))
        self.after(4200, self._after_load_check)
        self.after(5600, lambda: self._send_line("sch_snap"))
        self.after(6400, lambda: self._set_status("原理图已发送：屏幕显示框选与判定"))

    def _send_camera_mode(self):
        if self._send_line("sch_mode off"):
            self._set_status("已切回摄像头模式")

    def _toggle_serial(self):
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
            except Exception:
                pass
            self.ser = None
            self.btn_conn.configure(text=track("connect", 1))
            self.var_link.set(track("offline", 1))
            self.dot_link.itemconfigure(1, fill=ON_BLUE["fg_40"])
            self._append("── serial closed ──\n", tag="dim")
            return

        port = self._selected_device()
        if not port:
            messagebox.showwarning("提示", "没有可用串口")
            return
        try:
            self.ser = serial.Serial(port, int(self.var_baud.get()), timeout=0.05)
        except Exception as e:
            messagebox.showerror("打开失败", f"{port} 打不开：\n{e}\n\n（串口助手要先关掉）")
            return

        self.btn_conn.configure(text=track("disconnect", 1))
        self.var_link.set(track("linked", 1))
        self.dot_link.itemconfigure(1, fill=GREEN)
        self._append(f"── {port} @ {self.var_baud.get()} open ──\n", tag="ok")
        threading.Thread(target=self._reader, daemon=True).start()
        self._send_line("")          # 先敲回车拿提示符

        if self.var_autokey.get() and self.ent_key.get().strip():
            self.after(500, self._send_key)

    def _reader(self):
        s = self.ser
        while s and s.is_open:
            try:
                data = s.read(4096)
            except Exception:
                break
            if data:
                self.rxq.put(data)
            else:
                time.sleep(0.01)

    def _poll_serial(self):
        got = False
        while not self.rxq.empty():
            data = self.rxq.get()
            text = ANSI_RE.sub("", data.decode("utf-8", "replace"))
            self._logbuf = (getattr(self, "_logbuf", "") + text)[-4000:]
            self._append(text)
            got = True
        if got:
            self.txt.see("end")
        self._refresh_counts()
        self.after(80, self._poll_serial)

    def _classify(self, line):
        """给每行日志挑一个 tag，让通道区自己会读。"""
        s = line.strip()
        if not s:
            return None
        if s.startswith("A:"):
            return "ans"
        if "HTTP 200" in s:
            return "ok"
        low = s.lower()
        if any(k in low for k in ("failed", "error", "incomplete", "panic",
                                  "assert", "empty response")):
            return "err"
        if s.startswith("[llm]"):
            return "dim"
        if s.startswith("msh />"):
            return "hint"
        return None

    def _append(self, text, tag=None):
        t = self.txt
        t.configure(state="normal")
        start = t.index("end-1c")
        t.insert("end", text)
        end = t.index("end-1c")
        if tag:
            t.tag_add(tag, start, end)
        else:
            # 逐行判定，避免整段同色
            idx = start
            while t.compare(idx, "<", end):
                line_end = t.index(f"{idx} lineend")
                tag_i = self._classify(t.get(idx, line_end))
                if tag_i:
                    t.tag_add(tag_i, idx, line_end)
                nxt = t.index(f"{line_end}+1c")
                if t.compare(nxt, "<=", idx):
                    break
                idx = nxt
        t.configure(state="disabled")
        # the firmware reports luma with every push; turn it into a usable verdict
        # so a blown-out or black frame is caught while shooting, not at training time
        m = re.search(r"luma=(\d+)", text)
        if m:
            luma = int(m.group(1))
            if luma > 185:
                self._set_status(f"⚠ 过曝 luma={luma}：避开灯/屏幕，靠近焊盘再拍")
            elif luma < 55:
                self._set_status(f"⚠ 偏暗 luma={luma}：补光或靠近一点")
            else:
                self._set_status(f"曝光可用 luma={luma}")

    def _clear(self):
        self.txt.configure(state="normal")
        self.txt.delete("1.0", "end")
        self.txt.configure(state="disabled")
        self._set_status("已清空通道")

    def _send_line(self, text):
        if not (self.ser and self.ser.is_open):
            messagebox.showwarning("提示", "先打开串口")
            return False
        try:
            self.ser.write(text.encode("utf-8") + b"\r\n")
        except Exception as e:
            messagebox.showerror("发送失败", str(e))
            return False
        return True

    def _send_text(self):
        q = self.ent_send.get().strip()
        if not q:
            return
        if self._send_line("ask " + q):
            self.ent_send.delete(0, "end")
            self._set_status(f"已发送 ask ({len(q)} 字)")

    def _send_date(self):
        if self._send_line(time.strftime("date %Y %m %d %H %M %S")):
            self._set_status("已对时")

    def _send_key(self):
        k = self.ent_key.get().strip()
        if not k:
            messagebox.showwarning("提示", "先填 API Key")
            return
        if self._send_line("llm_key " + k):
            self._sync_key_state()
            self._set_status("API Key 已下发到板子")

    # ---------- key 存取 ----------
    def _sync_key_state(self):
        has = bool(self.ent_key.get().strip())
        self.var_key.set(track("set", 1) if has else track("not set", 1))
        self.lbl_key.configure(fg=GREEN if has else DANGER)

    def _load_key(self, silent=False):
        try:
            with open(KEY_FILE, "r", encoding="utf-8") as f:
                self.ent_key.delete(0, "end")
                self.ent_key.insert(0, f.read().strip())
        except Exception:
            if not silent:
                messagebox.showinfo("提示", "还没有保存过 key")
        self._sync_key_state()

    def _save_key(self):
        k = self.ent_key.get().strip()
        if not k:
            return
        with open(KEY_FILE, "w", encoding="utf-8") as f:
            f.write(k)
        self._sync_key_state()
        messagebox.showinfo("已保存", f"保存到\n{KEY_FILE}\n\n注意：这是明文文件，别提交到 git。")

    # ---------- 时钟 ----------
    def _tick_clock(self):
        self.var_clock.set(time.strftime("%H:%M:%S"))
        self.after(1000, self._tick_clock)

    # ---------- HTTP ----------
    def _start_server(self):
        try:
            self.srv.port = HTTP_PORT
            self.srv.start()
            self.var_http.set(f"{self.http_ip}:{HTTP_PORT}")
            self._set_status(f"HTTP 图片服务 http://{self.http_ip}:{HTTP_PORT}/")
        except Exception as e:
            self.var_http.set(f":{HTTP_PORT} FAILED")
            self._set_status("HTTP 服务启动失败")
            messagebox.showerror("HTTP 服务启动失败",
                                 f"端口 {HTTP_PORT} 可能被占用：\n{e}")

    def _open_url(self):
        webbrowser.open(f"http://{self.http_ip}:{HTTP_PORT}/")

    # ---------- dataset capture ----------
    def _capture(self, label):
        """Freeze the live view, then take one frame straight into the dataset.

        cam_push shares one push buffer with cam_stream, so the stream is
        stopped first: that both avoids a torn frame and is exactly the
        "freeze" the user asked for. The received frame is also pushed into
        the preview state, so what you see is the frame you saved.
        """
        if not (self.ser and self.ser.is_open):
            messagebox.showwarning("提示", "先打开串口")
            return
        try:
            import cam_view
            cam_view._ensure_server(CAM_PORT)
        except Exception:
            pass
        # RGB888 is the faster-looking option but its pack path is broken on
        # this firmware (frames come back geometrically sheared); RGB565 lands
        # correctly and is 1/3 the bytes. Pin it before every shot.
        self._send_line("cam_fmt 565")
        self._send_line("cam_stream stop")
        url = f"http://{self.http_ip}:{CAM_PORT}/snap?label={label}"
        if self._send_line(f"cam_push {url} 2"):
            self._set_status(f"拍照 {label} → {url}   320×240，约 2 s 后计数刷新")
            self.after(2500, self._refresh_counts)

    def _resume_stream(self):
        if not (self.ser and self.ser.is_open):
            messagebox.showwarning("提示", "先打开串口")
            return
        try:
            import cam_view
            cam_view._ensure_server(CAM_PORT)
        except Exception:
            pass
        # preview runs at div=4 (160x120): the board's HTTP path tops out near
        # 6 fps at 320x240 and 14 fps at 160x120, because every frame opens a new
        # TCP connection (~1 MB/s). Capture keeps div=2 for a sharp still.
        url = f"http://{self.http_ip}:{CAM_PORT}/frame"
        if self._send_line(f"cam_stream {url} 15 4"):
            self._set_status(f"恢复推流 160×120 → {url}（拍照仍 320×240）")

    def _refresh_counts(self):
        try:
            sys.path.insert(0, APP_DIR)
            import cam_web
            self.var_cap.set(f"ok {cam_web.count_label('ok')} · "
                             f"missing {cam_web.count_label('missing')}")
        except Exception:
            pass

    def _open_demo(self):
        """Scroll-linked parallax page (Tkinter edition)."""
        try:
            from parallax_demo import ParallaxDemo
            ParallaxDemo(self)
        except Exception as e:
            messagebox.showerror("视差演示打不开", str(e))

    def _open_camera(self):
        """摄像头预览小窗：板子执行 cam_push 把帧推到本机 8001 端口"""
        try:
            from cam_view import open_camera_window
            open_camera_window(self)
        except Exception as e:
            messagebox.showerror("摄像头预览打不开", str(e))

    def _open_folder(self):
        os.startfile(IMAGE_DIR)

    # ---------- 图片 ----------
    def _clear_queue(self):
        self.qscroll.clear()
        self._cards = []
        self._thumbs = []

    def _thumb(self, path):
        try:
            from PIL import Image, ImageTk
        except ImportError:
            return None
        try:
            im = Image.open(path)
            im.thumbnail((84, 62), Image.LANCZOS)
            return ImageTk.PhotoImage(im)
        except Exception:
            return None

    def _refresh_images(self):
        try:
            names = sorted((n for n in os.listdir(IMAGE_DIR)
                            if n.lower().endswith(IMG_EXT)), reverse=True)
        except Exception:
            names = []
        self.img_files = []
        self._clear_queue()
        total = 0
        for name in names:
            path = os.path.join(IMAGE_DIR, name)
            try:
                size = os.path.getsize(path)
            except OSError:
                size = 0
            total += size
            self.img_files.append((name, size))
            thumb = self._thumb(path)
            self._thumbs.append(thumb)
            card = ImageCard(self.qscroll.inner, self, len(self.img_files) - 1,
                             name, path, size, thumb)
            card.pack(fill="x", pady=(0, 6))
            self._cards.append(card)
        self.qscroll.bind_wheel(self.qscroll.inner)
        self.var_queue.set(f"{len(self.img_files)} FILES · {total/1024:.0f} KB")
        if self.selected is not None and self.selected >= len(self._cards):
            self.selected = None

    def _auto_refresh_images(self):
        try:
            cur = set(os.listdir(IMAGE_DIR))
        except Exception:
            cur = set()
        if cur != self._last_image_set:
            self._last_image_set = cur
            self._refresh_images()
        self.after(3000, self._auto_refresh_images)

    def _import_images(self):
        files = filedialog.askopenfilenames(
            title="选择图片（会复制到图片文件夹）",
            filetypes=[("图片", "*.jpg *.jpeg *.png *.gif *.webp"), ("所有文件", "*.*")])
        if not files:
            return
        n = 0
        for src in files:
            ext = os.path.splitext(src)[1].lower() or ".jpg"
            dst_name = time.strftime("img_%Y%m%d_%H%M%S") + f"_{n}" + ext
            try:
                shutil.copy2(src, os.path.join(IMAGE_DIR, dst_name))
                n += 1
            except Exception as e:
                messagebox.showerror("复制失败", f"{src}\n{e}")
        self._refresh_images()
        self._set_status(f"已导入 {n} 张图片")

    def select_image(self, index):
        if index == self.selected:
            return
        if self.selected is not None and self.selected < len(self._cards):
            self._cards[self.selected].set_selected(False)
        self.selected = index
        self._cards[index].set_selected(True)
        name, size = self.img_files[index]
        self._set_status(f"选中 {name}  ({size/1024:.0f} KB)")

    def preview_image(self, index):
        name, _ = self.img_files[index]
        os.startfile(os.path.join(IMAGE_DIR, name))

    def _send_image(self):
        if self.selected is None or self.selected >= len(self.img_files):
            messagebox.showwarning("提示", "先在右侧队列里点一张图片")
            return
        name, _ = self.img_files[self.selected]
        path = os.path.join(IMAGE_DIR, name)
        raw = os.path.getsize(path)

        # 大图压缩是可选的（默认发原图）；板子发超大包时可能在 TLS 读阶段断开
        send_path = shrink_image(path) if self.var_compress.get() else path
        send_name = os.path.basename(send_path)
        now = os.path.getsize(send_path)

        q = "描述这张图片"
        url = f"http://{self.http_ip}:{HTTP_PORT}/{quote(send_name)}"
        if self._send_line(f"vlm_url {url} {q}"):
            if send_name != name:
                self._set_status(f"已压缩 {raw/1024:.0f}KB → {now/1024:.0f}KB，发送 {send_name}")
            else:
                self._set_status(f"已发送 {send_name} ({now/1024:.0f} KB)")

    # ------------------------------------------------------------------ #
    def _on_close(self):
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
        except Exception:
            pass
        self.srv.stop()
        self.destroy()

    def _capture(self):
        from PIL import ImageGrab
        self.update_idletasks()
        self.update()
        x, y = self.winfo_rootx(), self.winfo_rooty()
        w, h = self.winfo_width(), self.winfo_height()
        os.makedirs(os.path.dirname(SHOT_PATH), exist_ok=True)
        ImageGrab.grab(bbox=(x, y, x + w, y + h)).save(SHOT_PATH)
        print("saved", SHOT_PATH, f"{w}x{h}")
        self._on_close()


def selftest():
    ensure_dir(IMAGE_DIR)
    print("IMAGE_DIR =", IMAGE_DIR)
    print("ports     =", list_com_ports())
    print("pc ip     =", detect_pc_ip())
    srv = FileServer(IMAGE_DIR, HTTP_PORT)
    srv.start()
    print("http      = 0.0.0.0:%d serving %s" % (HTTP_PORT, IMAGE_DIR))
    time.sleep(0.5)
    srv.stop()
    print("SELFTEST OK")


if __name__ == "__main__":
    import argparse as _ap
    _parser = _ap.ArgumentParser()
    _parser.add_argument("--send", default=None, help="启动后自动发送指定原理图")
    _args, _rest = _parser.parse_known_args()
    if "--selftest" in sys.argv:
        selftest()
    else:
        ensure_dir(IMAGE_DIR)
        _app = BoardApp(shot="--shot" in sys.argv)
        if _args.send:
            _app.send_on_start(_args.send)
        _app.mainloop()
