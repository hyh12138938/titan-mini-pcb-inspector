#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
电路板 AI 调试助手  (Board AI Helper)
------------------------------------------------
两个功能：
  1) 打开串口，和板子上的 AI 对话（发的文本走 msh 的 ask 命令）
  2) 把电脑上的图片导入固定文件夹，选中后发给板子（板子通过 HTTP 下载再转给大模型）

板子侧依赖（已实现）：
  ask <问题>                    纯文本
  vlm_url <url> [问题]          板子下载图片再问
  llm_key sk-xxx / date ...     配置

作者：为本机 Titan Mini / RA8P1 项目定制
运行：python board_ai_helper.py
"""

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

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# ---------------- 配置 ----------------
APP_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_DIR = r"D:\RTT\ai_images"          # 板子下载图片的目录（也是图片仓库）
KEY_FILE = os.path.join(APP_DIR, "api_key.txt")
HTTP_PORT = 8000
BAUD = 115200

ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def ensure_dir(p):
    if not os.path.isdir(p):
        os.makedirs(p, exist_ok=True)
    return p


def list_com_ports():
    """返回 [(device, description)]"""
    return [(p.device, (p.description or "").strip()) for p in serial.tools.list_ports.comports()]


def port_label(dev, desc):
    if desc and desc.lower() not in ("n/a", "none"):
        return f"{dev}  {desc}"
    return dev


def is_uart_bridge(dev, desc):
    """判断是不是 USB 转串口桥（CH340/CH910/CP210x/FTDI），而不是调试探针的 CDC"""
    d = (desc or "").lower()
    h = (dev or "").lower()
    for k in ("ch340", "ch341", "ch910", "cp210", "ftdi", "usb-serial", "usb serial", "prolific"):
        if k in d:
            return True
    # 探针 CDC 常见描述
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
        try:
            self.httpd = socketserver.ThreadingTCPServer(("0.0.0.0", self.port), handler)
        except Exception as e:
            self.httpd = None
            raise e
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


# ---------------- 主界面 ----------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("电路板 AI 调试助手  —  Titan Mini / RA8P1")
        self.geometry("1000x680")
        self.minsize(860, 560)

        ensure_dir(IMAGE_DIR)
        self.ser = None
        self.rxq = queue.Queue()
        self.http_ip = tk.StringVar(value=detect_pc_ip())
        self.http_port = tk.StringVar(value=str(HTTP_PORT))
        self.srv = FileServer(IMAGE_DIR, HTTP_PORT)
        self.img_files = []          # [(filename, original_name)]

        self._build_ui()
        self._refresh_ports()
        self._refresh_images()
        self._start_server()
        self.after(80, self._poll_serial)
        self.after(3000, self._auto_refresh_images)

    # ---------- UI ----------
    def _build_ui(self):
        pad = dict(padx=6, pady=4)

        # 顶部：串口
        top = ttk.LabelFrame(self, text="① 串口连接")
        top.pack(fill="x", **pad)

        ttk.Label(top, text="端口").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        self.cmb_port = ttk.Combobox(top, width=10, state="readonly")
        self.cmb_port.grid(row=0, column=1, padx=4, pady=4)
        ttk.Button(top, text="刷新", command=self._refresh_ports, width=6)\
            .grid(row=0, column=2, padx=4)

        ttk.Label(top, text="波特率").grid(row=0, column=3, padx=(16, 4))
        self.cmb_baud = ttk.Combobox(top, width=8, state="readonly",
                                     values=["115200", "921600", "460800", "230400"])
        self.cmb_baud.set(str(BAUD))
        self.cmb_baud.grid(row=0, column=4, padx=4)

        self.btn_open = ttk.Button(top, text="打开串口", command=self._toggle_serial, width=10)
        self.btn_open.grid(row=0, column=5, padx=12)

        self.lbl_state = ttk.Label(top, text="未连接", foreground="#b00")
        self.lbl_state.grid(row=0, column=6, padx=6)

        ttk.Button(top, text="对时", command=self._send_date, width=6)\
            .grid(row=0, column=7, padx=4)

        # AI key
        keyf = ttk.Frame(self)
        keyf.pack(fill="x", padx=6)
        ttk.Label(keyf, text="API Key").pack(side="left")
        self.ent_key = ttk.Entry(keyf, show="*", width=52)
        self.ent_key.pack(side="left", padx=6)
        ttk.Button(keyf, text="下发到板子", command=self._send_key, width=10).pack(side="left")
        ttk.Button(keyf, text="载入", command=self._load_key, width=6).pack(side="left", padx=4)
        ttk.Button(keyf, text="保存", command=self._save_key, width=6).pack(side="left")
        self.var_autokey = tk.BooleanVar(value=True)
        ttk.Checkbutton(keyf, text="打开串口后自动下发", variable=self.var_autokey)\
            .pack(side="left", padx=10)
        self._load_key(silent=True)

        # 中部左右
        body = ttk.Frame(self)
        body.pack(fill="both", expand=True, padx=6, pady=4)

        left = ttk.LabelFrame(body, text="② 对话（串口）")
        left.pack(side="left", fill="both", expand=True)

        self.txt = tk.Text(left, wrap="word", font=("Consolas", 9), bg="#101418", fg="#d8e0e8")
        self.txt.pack(fill="both", expand=True, padx=4, pady=(4, 0))
        self.txt.insert("end",
                        "提示：\n"
                        "  1) 端口要选 CH340 那个（COM4），不是 DAP 探针的 CDC（COM3）\n"
                        "  2) 打开串口后会自己发一次回车和 API Key\n"
                        "  3) 点「对时」再提问，否则 TLS 会因证书有效期失败\n"
                        "----------------------------------------------------------\n\n")
        self.txt.configure(state="disabled")

        sf = ttk.Frame(left)
        sf.pack(fill="x", padx=4, pady=4)
        self.ent_send = ttk.Entry(sf)
        self.ent_send.pack(side="left", fill="x", expand=True)
        self.ent_send.bind("<Return>", lambda e: self._send_text())
        ttk.Button(sf, text="发送", command=self._send_text, width=8).pack(side="left", padx=4)
        ttk.Button(sf, text="清屏", command=self._clear, width=6).pack(side="left")

        right = ttk.LabelFrame(body, text="③ 图片 → AI", width=390)
        right.pack(side="right", fill="y", padx=(8, 0))
        right.pack_propagate(False)

        srvf = ttk.Frame(right)
        srvf.pack(fill="x", padx=4, pady=4)
        ttk.Label(srvf, text="板子下载地址").pack(side="left")
        ttk.Entry(srvf, textvariable=self.http_ip, width=14).pack(side="left", padx=4)
        ttk.Label(srvf, text=":").pack(side="left")
        ttk.Entry(srvf, textvariable=self.http_port, width=6).pack(side="left")
        self.lbl_srv = ttk.Label(srvf, text="", foreground="#080")
        self.lbl_srv.pack(side="left", padx=6)

        ttk.Label(right, text="图片文件夹：" + IMAGE_DIR,
                  foreground="#555", wraplength=360).pack(fill="x", padx=6, pady=(0, 4))

        self.lst = tk.Listbox(right, height=14, font=("Consolas", 9))
        self.lst.pack(fill="both", expand=True, padx=6)
        self.lst.bind("<Double-Button-1>", lambda e: self._preview())

        bf = ttk.Frame(right)
        bf.pack(fill="x", padx=6, pady=4)
        ttk.Button(bf, text="导入图片…", command=self._import_images).pack(side="left")
        ttk.Button(bf, text="打开文件夹", command=lambda: os.startfile(IMAGE_DIR)).pack(side="left", padx=4)
        ttk.Button(bf, text="刷新", command=self._refresh_images, width=6).pack(side="left")
        ttk.Button(bf, text="浏览", command=self._open_url).pack(side="right")

        qf = ttk.Frame(right)
        qf.pack(fill="x", padx=6)
        ttk.Label(qf, text="问题").pack(side="left")
        self.ent_q = ttk.Entry(qf)
        self.ent_q.insert(0, "请描述这张图片，并指出图中有什么元件或异常")
        self.ent_q.pack(side="left", fill="x", expand=True, padx=4)

        self.var_compress = tk.BooleanVar(value=False)
        ttk.Checkbutton(right, text="大图自动压缩（>180KB，默认关闭=发原图）",
                        variable=self.var_compress).pack(fill="x", padx=6)

        ttk.Button(right, text="发送选中图片给 AI  ▶",
                   command=self._send_image).pack(fill="x", padx=6, pady=6)

        # 状态栏
        self.status = tk.StringVar(value="就绪")
        ttk.Label(self, textvariable=self.status, anchor="w", relief="sunken")\
            .pack(fill="x", side="bottom")

    # ---------- 串口 ----------
    def _refresh_ports(self):
        self.ports = list_com_ports()
        labels = [port_label(d, s) for d, s in self.ports]
        self.cmb_port["values"] = labels
        if labels:
            if self.cmb_port.get() not in labels:
                pick = 0
                for i, (d, s) in enumerate(self.ports):
                    if is_uart_bridge(d, s):
                        pick = i
                        break
                self.cmb_port.set(labels[pick])
        names = ", ".join(d for d, _ in self.ports) if self.ports else "未发现"
        self.status.set("串口: " + names)

    def _selected_device(self):
        lbl = (self.cmb_port.get() or "").strip()
        return lbl.split()[0] if lbl else ""

    def _toggle_serial(self):
        if self.ser and self.ser.is_open:
            try:
                self.ser.close()
            except Exception:
                pass
            self.ser = None
            self.btn_open.configure(text="打开串口")
            self.lbl_state.configure(text="未连接", foreground="#b00")
            return

        port = self._selected_device()
        if not port:
            messagebox.showwarning("提示", "没有可用串口")
            return
        try:
            self.ser = serial.Serial(port, int(self.cmb_baud.get()), timeout=0.05)
        except Exception as e:
            messagebox.showerror("打开失败", f"{port} 打不开：\n{e}\n\n（串口助手要先关掉）")
            return

        self.btn_open.configure(text="关闭串口")
        self.lbl_state.configure(text=f"{port} 已连接", foreground="#080")
        threading.Thread(target=self._reader, daemon=True).start()
        self._send_line("")          # 先敲一个回车拿提示符

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
            text = data.decode("utf-8", "replace")
            text = ANSI_RE.sub("", text)
            self._append(text)
            got = True
        if got:
            self.txt.see("end")
        self.after(80, self._poll_serial)

    def _append(self, text):
        self.txt.configure(state="normal")
        self.txt.insert("end", text)
        self.txt.configure(state="disabled")

    def _clear(self):
        self.txt.configure(state="normal")
        self.txt.delete("1.0", "end")
        self.txt.configure(state="disabled")

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
        t = self.ent_send.get().strip()
        if not t:
            return
        if self._send_line("ask " + t):
            self.ent_send.delete(0, "end")

    def _send_date(self):
        self._send_line(time.strftime("date %Y %m %d %H %M %S"))

    def _send_key(self):
        k = self.ent_key.get().strip()
        if not k:
            messagebox.showwarning("提示", "先填 API Key")
            return
        self._send_line("llm_key " + k)

    # ---------- key 存取 ----------
    def _load_key(self, silent=False):
        try:
            with open(KEY_FILE, "r", encoding="utf-8") as f:
                self.ent_key.delete(0, "end")
                self.ent_key.insert(0, f.read().strip())
        except Exception:
            if not silent:
                messagebox.showinfo("提示", "还没有保存过 key")

    def _save_key(self):
        k = self.ent_key.get().strip()
        if not k:
            return
        with open(KEY_FILE, "w", encoding="utf-8") as f:
            f.write(k)
        messagebox.showinfo("已保存", f"保存到\n{KEY_FILE}\n\n注意：这是明文文件，别提交到 git。")

    # ---------- HTTP ----------
    def _start_server(self):
        try:
            self.srv.port = int(self.http_port.get())
            self.srv.start()
            self.lbl_srv.configure(text=f"服务中 :{self.srv.port}", foreground="#080")
        except Exception as e:
            self.lbl_srv.configure(text="启动失败", foreground="#b00")
            messagebox.showerror("HTTP 服务启动失败",
                                 f"端口 {self.http_port.get()} 可能被占用：\n{e}")

    def _open_url(self):
        webbrowser.open(f"http://{self.http_ip.get()}:{self.http_port.get()}/")

    # ---------- 图片 ----------
    def _refresh_images(self):
        self.img_files = []
        self.lst.delete(0, "end")
        try:
            names = sorted(os.listdir(IMAGE_DIR))
        except Exception:
            names = []
        for n in names:
            if n.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")):
                self.img_files.append(n)
                size = os.path.getsize(os.path.join(IMAGE_DIR, n))
                self.lst.insert("end", f"{n}   ({size/1024:.0f} KB)")
        self.status.set(f"图片 {len(self.img_files)} 张  |  {IMAGE_DIR}")
        self._last_image_set = set(names)

    def _auto_refresh_images(self):
        try:
            cur = set(os.listdir(IMAGE_DIR))
        except Exception:
            cur = set()
        if cur != getattr(self, "_last_image_set", None):
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
            dst = os.path.join(IMAGE_DIR, dst_name)
            try:
                shutil.copy2(src, dst)
                n += 1
            except Exception as e:
                messagebox.showerror("复制失败", f"{src}\n{e}")
        self._refresh_images()
        self.status.set(f"已导入 {n} 张图片")

    def _preview(self):
        idx = self.lst.curselection()
        if not idx:
            return
        name = self.img_files[idx[0]]
        os.startfile(os.path.join(IMAGE_DIR, name))

    def _send_image(self):
        idx = self.lst.curselection()
        if not idx:
            messagebox.showwarning("提示", "先在列表里选中一张图片")
            return
        name = self.img_files[idx[0]]
        path = os.path.join(IMAGE_DIR, name)
        raw = os.path.getsize(path)

        # 大图压缩是可选的（默认发原图）；板子发超大包时可能在 TLS 读阶段断开
        send_path = shrink_image(path) if self.var_compress.get() else path
        send_name = os.path.basename(send_path)
        now = os.path.getsize(send_path)

        q = self.ent_q.get().strip() or "描述这张图片"
        url = f"http://{self.http_ip.get()}:{self.http_port.get()}/{quote(send_name)}"
        if self._send_line(f"vlm_url {url} {q}"):
            if send_name != name:
                self.status.set(f"已压缩 {raw/1024:.0f}KB → {now/1024:.0f}KB，发送 {send_name}")
            else:
                self.status.set(f"已发送 {send_name} ({now/1024:.0f} KB)")


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
    if "--selftest" in sys.argv:
        selftest()
    else:
        ensure_dir(IMAGE_DIR)
        App().mainloop()
