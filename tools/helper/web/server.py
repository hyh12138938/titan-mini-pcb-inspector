#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
web/server.py - backend for the WebView build of the board AI helper.

Why not pywebview: its Windows backend pulls pythonnet/.NET, and that install
stalled for minutes on this machine. The window is opened by Edge/Chrome in
`--app` mode instead, which is the same Chromium/WebView2 engine rendering the
same HTML - so the visual result is identical, with zero new dependencies.

Endpoints
  GET  /                the console UI
  GET  /assets/*        static files
  GET  /thumb/<name>    cached thumbnail
  GET  /api/state       JSON snapshot
  GET  /api/events      server-sent events (serial log + state changes)
  POST /api/connect | /api/disconnect | /api/date | /api/prompt
       /api/key | /api/import | /api/folder | /api/send_image | /api/select

Run:  python web\\server.py            (opens the app window)
      python web\\server.py --no-open  (server only)
"""
import io
import json
import os
import queue
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, quote, urlparse

APP_DIR = os.path.dirname(os.path.abspath(__file__))
APPS_DIR = os.path.dirname(APP_DIR)
sys.path.insert(0, APPS_DIR)

from board_ai_helper import (  # noqa: E402
    IMAGE_DIR, KEY_FILE, HTTP_PORT, FileServer, detect_pc_ip,
    is_uart_bridge, list_com_ports, shrink_image, IMG_EXT,
)

PORT = 8765
EDGE_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


# --------------------------------------------------------------------------- #
# event fan-out
# --------------------------------------------------------------------------- #
class Hub:
    def __init__(self):
        self.clients = []
        self.lock = threading.Lock()

    def add(self):
        q = queue.Queue(maxsize=2000)
        with self.lock:
            self.clients.append(q)
        return q

    def remove(self, q):
        with self.lock:
            if q in self.clients:
                self.clients.remove(q)

    def broadcast(self, msg):
        with self.lock:
            for q in list(self.clients):
                try:
                    q.put_nowait(msg)
                except queue.Full:
                    pass


HUB = Hub()


# --------------------------------------------------------------------------- #
# hardware / filesystem state
# --------------------------------------------------------------------------- #
class Board:
    def __init__(self):
        self.ser = None
        self.port = ""
        self.baud = "115200"
        self.selected = None

    def connected(self):
        return bool(self.ser and getattr(self.ser, "is_open", False))

    def open(self, port, baud):
        import serial
        if self.connected():
            return {"ok": True}
        self.ser = serial.Serial(port, int(baud), timeout=0.05)
        self.port, self.baud = port, str(baud)
        threading.Thread(target=self._reader, daemon=True).start()
        HUB.broadcast({"type": "log", "text": f"── {port} @ {baud} open ──\n"})
        return {"ok": True}

    def close(self):
        if self.ser:
            try:
                self.ser.close()
            except Exception:
                pass
        self.ser = None
        HUB.broadcast({"type": "log", "text": "── serial closed ──\n"})

    def _reader(self):
        s = self.ser
        while s and getattr(s, "is_open", False):
            try:
                data = s.read(4096)
            except Exception:
                break
            if data:
                HUB.broadcast({"type": "log",
                               "text": data.decode("utf-8", "replace")})
            else:
                time.sleep(0.01)

    def send(self, line):
        if not self.connected():
            return False
        try:
            self.ser.write(line.encode("utf-8") + b"\r\n")
            return True
        except Exception:
            return False


BOARD = Board()
THUMBS = {}


def read_key():
    try:
        with open(KEY_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return ""


def write_key(k):
    with open(KEY_FILE, "w", encoding="utf-8") as f:
        f.write(k)


def scan_images():
    out = []
    try:
        names = sorted((n for n in os.listdir(IMAGE_DIR)
                        if n.lower().endswith(IMG_EXT)), reverse=True)
    except OSError:
        return out
    for n in names:
        try:
            size = os.path.getsize(os.path.join(IMAGE_DIR, n))
        except OSError:
            size = 0
        out.append({"name": n, "size": size, "thumb": "/thumb/" + quote(n)})
    return out


def thumb_bytes(name, box=(168, 124)):
    if name in THUMBS:
        return THUMBS[name]
    from PIL import Image
    p = os.path.join(IMAGE_DIR, name)
    im = Image.open(p)
    im.thumbnail(box, Image.LANCZOS)
    if im.mode != "RGB":
        im = im.convert("RGB")
    b = io.BytesIO()
    im.save(b, "JPEG", quality=80)
    data = b.getvalue()
    THUMBS[name] = data
    return data


def snapshot():
    ports = [{"device": d, "label": s} for d, s in list_com_ports()]
    best = ""
    for d, s in list_com_ports():
        if is_uart_bridge(d, s):
            best = d
            break
    return {
        "ports": ports,
        "port": BOARD.port or best,
        "baud": BOARD.baud,
        "connected": BOARD.connected(),
        "key_set": bool(read_key()),
        "images": scan_images(),
        "selected": BOARD.selected,
        "http": f"{detect_pc_ip()}:{HTTP_PORT}",
    }


def pick_files():
    """Native file picker without touching Tk (this runs on a worker thread)."""
    ps = (
        "Add-Type -AssemblyName System.Windows.Forms;"
        "$d = New-Object System.Windows.Forms.OpenFileDialog;"
        "$d.Multiselect = $true;"
        "$d.Filter = 'Images|*.jpg;*.jpeg;*.png;*.gif;*.webp|All files|*.*';"
        "if ($d.ShowDialog() -eq 'OK') { $d.FileNames -join \"`n\" }"
    )
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                           capture_output=True, text=True, timeout=300)
        return [l for l in r.stdout.splitlines() if l.strip()]
    except Exception:
        return []


# --------------------------------------------------------------------------- #
# http
# --------------------------------------------------------------------------- #
class Handler(BaseHTTPRequestHandler):
    server_version = "BoardAIWeb/1.0"

    def log_message(self, *a):
        pass

    # -- helpers --------------------------------------------------------
    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _file(self, path, ctype):
        try:
            with open(path, "rb") as f:
                data = f.read()
        except OSError:
            self._json({"error": "not found"}, 404)
            return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _body(self):
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            return {}
        if not n:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except Exception:
            return {}

    # -- GET ------------------------------------------------------------
    def do_GET(self):
        u = urlparse(self.path)
        p = unquote(u.path)
        if p in ("/", "/index.html"):
            self._file(os.path.join(APP_DIR, "index.html"), "text/html; charset=utf-8")
        elif p == "/demo.html":
            self._file(os.path.join(APP_DIR, "demo.html"), "text/html; charset=utf-8")
        elif p.startswith("/assets/"):
            fn = os.path.basename(p)
            ext = os.path.splitext(fn)[1].lower()
            ctype = "image/png" if ext == ".png" else "application/octet-stream"
            self._file(os.path.join(APP_DIR, "assets", fn), ctype)
        elif p.startswith("/thumb/"):
            name = os.path.basename(p)
            try:
                data = thumb_bytes(name)
            except Exception:
                self._json({"error": "thumb failed"}, 404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "image/jpeg")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "max-age=60")
            self.end_headers()
            self.wfile.write(data)
        elif p == "/api/state":
            self._json(snapshot())
        elif p == "/api/events":
            self._sse()
        else:
            self._json({"error": "not found"}, 404)

    def _sse(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        q = HUB.add()
        try:
            while True:
                try:
                    msg = q.get(timeout=15)
                except queue.Empty:
                    self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
                    continue
                self.wfile.write(("data: " + json.dumps(msg, ensure_ascii=False) +
                                  "\n\n").encode("utf-8"))
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            HUB.remove(q)

    # -- POST -----------------------------------------------------------
    def do_POST(self):
        p = urlparse(self.path).path
        b = self._body()

        if p == "/api/connect":
            if BOARD.connected():
                BOARD.close()
                self._json({"ok": True})
                return
            port = (b.get("port") or "").strip()
            if not port:
                self._json({"error": "没有可用串口"})
                return
            try:
                BOARD.open(port, b.get("baud") or "115200")
            except Exception as e:
                self._json({"error": f"{port} 打不开：{e}"})
                return
            BOARD.send("")
            if b.get("autokey") and b.get("key"):
                time.sleep(0.4)
                BOARD.send("llm_key " + str(b["key"]).strip())
            self._json({"ok": True})

        elif p == "/api/disconnect":
            BOARD.close()
            self._json({"ok": True})

        elif p == "/api/date":
            ok = BOARD.send(time.strftime("date %Y %m %d %H %M %S"))
            self._json({"ok": ok})

        elif p == "/api/prompt":
            t = (b.get("text") or "").strip()
            if not t:
                self._json({"error": "空问题"})
                return
            ok = BOARD.send("ask " + t)
            self._json({"ok": ok} if ok else {"error": "串口未连接"})

        elif p == "/api/key":
            k = (b.get("key") or "").strip()
            if not k:
                self._json({"error": "先填 Key"})
                return
            if b.get("save"):
                write_key(k)
            ok = BOARD.send("llm_key " + k) if BOARD.connected() else False
            self._json({"ok": True, "sent": ok})

        elif p == "/api/select":
            try:
                idx = int(b.get("index"))
            except (TypeError, ValueError):
                self._json({"error": "bad index"})
                return
            BOARD.selected = idx
            self._json({"ok": True})

        elif p == "/api/send_image":
            imgs = scan_images()
            idx = b.get("index")
            if idx is None or not (0 <= int(idx) < len(imgs)):
                self._json({"error": "先在右侧选一张图"})
                return
            name = imgs[int(idx)]["name"]
            path = os.path.join(IMAGE_DIR, name)
            raw = os.path.getsize(path)
            send_path = shrink_image(path) if b.get("compress") else path
            send_name = os.path.basename(send_path)
            now = os.path.getsize(send_path)
            url = f"http://{detect_pc_ip()}:{HTTP_PORT}/{quote(send_name)}"
            if not BOARD.send(f"vlm_url {url} 描述这张图片"):
                self._json({"error": "串口未连接"})
                return
            msg = (f"已压缩 {raw/1024:.0f}KB → {now/1024:.0f}KB，发送 {send_name}"
                   if send_name != name else f"已发送 {send_name} ({now/1024:.0f} KB)")
            self._json({"ok": True, "msg": msg})

        elif p == "/api/import":
            files = pick_files()
            if not files:
                self._json({"ok": True, "count": 0})
                return
            import shutil
            n = 0
            for src in files:
                ext = os.path.splitext(src)[1].lower() or ".jpg"
                dst = os.path.join(IMAGE_DIR,
                                   time.strftime("img_%Y%m%d_%H%M%S") + f"_{n}" + ext)
                try:
                    shutil.copy2(src, dst)
                    n += 1
                except Exception:
                    pass
            THUMBS.clear()
            self._json({"ok": True, "count": n})

        elif p == "/api/folder":
            try:
                os.startfile(IMAGE_DIR)
            except Exception:
                pass
            self._json({"ok": True})

        else:
            self._json({"error": "not found"}, 404)


# --------------------------------------------------------------------------- #
def open_window(url):
    for exe in EDGE_CANDIDATES:
        if os.path.exists(exe):
            try:
                subprocess.Popen([exe, f"--app={url}", "--window-size=1400,900"])
                return True
            except Exception:
                continue
    try:
        import webbrowser
        webbrowser.open(url)
        return True
    except Exception:
        return False


def main():
    os.makedirs(IMAGE_DIR, exist_ok=True)

    # the board downloads images from :8000 - same contract as the Tk build
    try:
        srv = FileServer(IMAGE_DIR, HTTP_PORT)
        srv.start()
        print(f"[img] serving {IMAGE_DIR} on 0.0.0.0:{HTTP_PORT}")
    except Exception as e:
        print(f"[img] port {HTTP_PORT} busy ({e}) - board downloads may fail")

    httpd = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{PORT}/"
    print(f"[web] {url}")

    if "--no-open" not in sys.argv:
        open_window(url)

    print("[web] ctrl+c to stop")
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nbye")


if __name__ == "__main__":
    main()
