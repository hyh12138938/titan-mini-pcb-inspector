#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
摄像头预览服务（PC 端）—— 板子把帧 POST 上来，浏览器里看
------------------------------------------------------------------
板子端：
    cam_push http://192.168.137.1:8001/frame        # 抓一帧 → 2×降采样 → POST 原始 RGB565

PC 端：
    python cam_web.py            # 默认 0.0.0.0:8001
    浏览器打开 http://127.0.0.1:8001/

接口：
    POST /frame        原始像素，头部 X-Width / X-Height / X-Format(rgb565|rgb888) / X-Byte-Order(le|be)
    GET  /             预览页（小窗 + 放大按钮 + 自动刷新）
    GET  /latest.png   当前帧 PNG
    GET  /latest_full.png  放大 3× 的 PNG（供“放大”按钮打开）
    GET  /jpeg?q=80    当前帧的 JPEG（给板子取压缩图用）
    GET  /stats        JSON 状态
    POST /clear        清空当前帧

依赖：Pillow
"""

import csv
import io
import json
import os
import sys
import time
import threading
import socketserver
import http.server
from urllib.parse import urlparse, parse_qs

try:
    from PIL import Image
except ImportError:
    print("需要 Pillow:  pip install pillow")
    sys.exit(1)

PORT = 8001

# ---- dataset capture -------------------------------------------------------
# Two-class collection for the missing-solder detector. The board posts a frame
# to /snap?label=<ok|missing>; we decode it, freeze it into the preview, and
# write it under datasets/solder_pad/<label>/ plus one CSV index row so a
# training script never has to parse directory names.
DATASET_DIR = r"D:\RTT\datasets\solder_pad"
LABELS = ("ok", "missing")
SNAP_LOCK = threading.Lock()


def _label_dir(label):
    return os.path.join(DATASET_DIR, label)


def count_label(label):
    d = _label_dir(label)
    try:
        return sum(1 for n in os.listdir(d) if n.lower().endswith((".png", ".jpg")))
    except OSError:
        return 0


def save_snapshot(img, label, w, h, fmt, nbytes):
    d = _label_dir(label)
    os.makedirs(d, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    ms = int((time.time() % 1) * 1000)
    name = f"{label}_{stamp}_{ms:03d}.png"
    img.save(os.path.join(d, name), "PNG")
    with SNAP_LOCK:
        idx = os.path.join(DATASET_DIR, "_index.csv")
        fresh = not os.path.exists(idx)
        with open(idx, "a", encoding="utf-8", newline="") as f:
            wr = csv.writer(f)
            if fresh:
                wr.writerow(["file", "label", "width", "height", "format",
                             "bytes", "captured_at"])
            wr.writerow([f"{label}/{name}", label, w, h, fmt, nbytes,
                         time.strftime("%Y-%m-%d %H:%M:%S")])
    return name


STATE_LOCK = threading.Lock()
STATE = {
    "png": None,          # 原始尺寸 PNG bytes
    "jpeg": None,         # JPEG bytes
    "full": None,         # 放大 3x PNG
    "w": 0,
    "h": 0,
    "fmt": "-",
    "frames": 0,
    "t_first": 0.0,
    "t_last": 0.0,
    "last_bytes": 0,
    "error": "",
}


def decode_raw(data, w, h, fmt, order):
    """把板上来的原始像素转成 PIL Image"""
    if fmt == "rgb565":
        n = w * h
        if len(data) < n * 2:
            raise ValueError("rgb565 数据不足: %d < %d" % (len(data), n * 2))
        raw = bytearray(n * 3)
        for i in range(n):
            lo = data[2 * i]
            hi = data[2 * i + 1]
            if order == "be":
                v = (lo << 8) | hi
            else:
                v = (hi << 8) | lo
            r = (v >> 11) & 0x1F
            g = (v >> 5) & 0x3F
            b = v & 0x1F
            raw[3 * i + 0] = (r << 3) | (r >> 2)
            raw[3 * i + 1] = (g << 2) | (g >> 4)
            raw[3 * i + 2] = (b << 3) | (b >> 2)
        return Image.frombytes("RGB", (w, h), bytes(raw))
    elif fmt == "rgb888":
        if len(data) < w * h * 3:
            raise ValueError("rgb888 数据不足")
        return Image.frombytes("RGB", (w, h), bytes(data[: w * h * 3]))
    else:
        raise ValueError("未知格式: " + fmt)


def store_image(img, fmt, nbytes):
    buf = io.BytesIO()
    img.save(buf, "PNG")
    png = buf.getvalue()

    jb = io.BytesIO()
    img.save(jb, "JPEG", quality=85)
    jpeg = jb.getvalue()

    big = img.resize((img.width * 3, img.height * 3), Image.NEAREST)
    fb = io.BytesIO()
    big.save(fb, "PNG")

    now = time.time()
    with STATE_LOCK:
        if STATE["frames"] == 0:
            STATE["t_first"] = now
        STATE["png"] = png
        STATE["jpeg"] = jpeg
        STATE["full"] = fb.getvalue()
        STATE["w"] = img.width
        STATE["h"] = img.height
        STATE["fmt"] = fmt
        STATE["frames"] += 1
        STATE["t_last"] = now
        STATE["last_bytes"] = nbytes
        STATE["error"] = ""


PAGE = """<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8">
<title>摄像头预览</title>
<style>
  :root { --bg:#0B0B0F; --fg:#F2F2F2; --dim:#8A8A93; --accent:#0000F2; --neon:#E8FF2B; }
  * { box-sizing:border-box; }
  body { margin:0; background:var(--bg); color:var(--fg);
         font-family: ui-monospace, Consolas, "Cascadia Mono", monospace; }
  .wrap { max-width: 720px; margin: 32px auto; padding: 0 20px; }
  h1 { font-size: 15px; letter-spacing:.22em; text-transform:uppercase; color:var(--dim);
       font-weight:600; margin:0 0 16px; }
  .panel { border:1px solid #23232B; padding:14px; background:#0F0F14; }
  .shot { position:relative; width:320px; height:240px; background:#000;
          display:flex; align-items:center; justify-content:center; }
  .shot img { width:320px; height:240px; image-rendering:pixelated; display:block; }
  .empty { color:#4A4A55; font-size:12px; letter-spacing:.1em; }
  .bar { display:flex; gap:8px; margin-top:12px; flex-wrap:wrap; align-items:center; }
  button, a.btn { background:transparent; color:var(--fg); border:1px solid #3A3A45;
         padding:7px 12px; font:inherit; font-size:12px; letter-spacing:.08em;
         text-transform:uppercase; cursor:pointer; text-decoration:none; }
  button:hover, a.btn:hover { border-color:var(--neon); color:var(--neon); }
  a.btn.primary { background:var(--accent); border-color:var(--accent); color:#fff; }
  .stat { margin-top:14px; font-size:12px; color:var(--dim); line-height:1.7; }
  .stat b { color:var(--fg); font-weight:600; }
  .err { color:#FF5C5C; }
</style></head>
<body><div class="wrap">
  <h1>Camera · Titan Mini</h1>
  <div class="panel">
    <div class="shot" id="shot"><span class="empty">等待板子上传…</span></div>
    <div class="bar">
      <a class="btn primary" id="zoom" href="/latest_full.png" target="_blank">放大 3×</a>
      <a class="btn" id="dl" href="/latest.png" download="frame.png">保存 PNG</a>
      <button onclick="fetch('/clear',{method:'POST'}).then(()=>location.reload())">清空</button>
      <button onclick="toggleLive()" id="livebtn">暂停</button>
    </div>
    <div class="stat" id="stat">--</div>
  </div>
</div>
<script>
let live = true, n = 0, lastFrames = -1;
function toggleLive(){ live = !live; document.getElementById('livebtn').textContent = live ? '暂停' : '继续'; }
async function tick(){
  if (live) {
    try {
      const s = await (await fetch('/stats', {cache:'no-store'})).json();
      if (s.frames !== lastFrames || n === 0) {
        lastFrames = s.frames;
        const r = await fetch('/latest.png?t=' + Date.now(), {cache:'no-store'});
        if (r.ok) {
          const b = await r.blob();
          const img = document.createElement('img');
          img.src = URL.createObjectURL(b);
          const shot = document.getElementById('shot');
          shot.innerHTML = ''; shot.appendChild(img);
          n++;
        }
      }
      document.getElementById('stat').innerHTML =
        '帧率 <b>' + s.fps.toFixed(1) + '</b> fps &nbsp;·&nbsp; 尺寸 <b>' + s.w + '×' + s.h + '</b>' +
        ' &nbsp;·&nbsp; 格式 <b>' + s.fmt + '</b><br>' +
        '累计 <b>' + s.frames + '</b> 帧 &nbsp;·&nbsp; 上一帧 <b>' + (s.last_bytes/1024).toFixed(1) + ' KB</b>' +
        (s.error ? '<br><span class="err">' + s.error + '</span>' : '');
    } catch(e) {}
  }
  setTimeout(tick, 150);
}
tick();
</script>
</body></html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
            try:
                sys.stderr.write("[srv] %s => %s\n" % (self.requestline[:160], (fmt % args)[:160]))
                sys.stderr.flush()
            except Exception:
                pass

    def _send(self, code, body, ctype="application/octet-stream", extra=None):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        try:
            self.wfile.write(body)
        except Exception:
            pass

    def do_GET(self):
        u = urlparse(self.path)
        path = u.path
        if path in ("/", "/index.html"):
            return self._send(200, PAGE, "text/html; charset=utf-8")
        if path == "/latest.png":
            with STATE_LOCK:
                b = STATE["png"]
            if not b:
                return self._send(404, "no frame yet", "text/plain; charset=utf-8")
            return self._send(200, b, "image/png")
        if path == "/latest_full.png":
            with STATE_LOCK:
                b = STATE["full"]
            if not b:
                return self._send(404, "no frame yet", "text/plain; charset=utf-8")
            return self._send(200, b, "image/png")
        if path == "/jpeg":
            qs = parse_qs(u.query)
            q = int(qs.get("q", ["85"])[0])
            with STATE_LOCK:
                b = STATE["jpeg"]
            if not b or q != 85:
                with STATE_LOCK:
                    png = STATE["png"]
                if not png:
                    return self._send(404, "no frame yet", "text/plain; charset=utf-8")
                img = Image.open(io.BytesIO(png)).convert("RGB")
                buf = io.BytesIO()
                img.save(buf, "JPEG", quality=max(30, min(95, q)))
                b = buf.getvalue()
            return self._send(200, b, "image/jpeg")
        if path == "/stats":
            with STATE_LOCK:
                s = dict(STATE)
            span = max(1e-6, (s["t_last"] - s["t_first"])) if s["frames"] > 1 else 1.0
            fps = (s["frames"] - 1) / span if s["frames"] > 1 else 0.0
            return self._send(200, json.dumps({
                "w": s["w"], "h": s["h"], "fmt": s["fmt"], "frames": s["frames"],
                "fps": fps, "last_bytes": s["last_bytes"], "error": s["error"],
            }), "application/json")
        return self._send(404, "not found", "text/plain; charset=utf-8")

    def do_POST(self):
        u = urlparse(self.path)
        if u.path == "/clear":
            with STATE_LOCK:
                STATE.update(png=None, full=None, jpeg=None, w=0, h=0, frames=0,
                             t_first=0.0, t_last=0.0, last_bytes=0, error="")
            return self._send(200, "cleared", "text/plain; charset=utf-8")

        if u.path == "/snap":
            try:
                sys.stderr.write("[snap] headers: CL=%s W=%s H=%s FMT=%s ORD=%s\n" % (
                    self.headers.get("Content-Length"), self.headers.get("X-Width"),
                    self.headers.get("X-Height"), self.headers.get("X-Format"),
                    self.headers.get("X-Byte-Order")))
                sys.stderr.flush()
            except Exception:
                pass
            label = (parse_qs(u.query).get("label", ["ok"])[0] or "ok").strip().lower()
            if label not in LABELS:
                return self._send(400, "label must be ok|missing",
                                  "text/plain; charset=utf-8")
            n = int(self.headers.get("Content-Length", "0"))
            w = int(self.headers.get("X-Width", "0"))
            h = int(self.headers.get("X-Height", "0"))
            fmt = (self.headers.get("X-Format", "rgb565") or "rgb565").lower()
            order = (self.headers.get("X-Byte-Order", "le") or "le").lower()
            data = self.rfile.read(n) if n else b""
            try:
                if w <= 0 or h <= 0:
                    raise ValueError("missing X-Width / X-Height")
                img = decode_raw(data, w, h, fmt, order)
                name = save_snapshot(img, label, w, h, fmt, len(data))
                # the frame the user just shot is also the frame they see: freeze it
                store_image(img, fmt, len(data))
                return self._send(200, json.dumps({
                    "ok": True, "file": name, "label": label,
                    "ok_count": count_label("ok"),
                    "missing_count": count_label("missing"),
                }), "application/json")
            except Exception as e:
                return self._send(400, str(e), "text/plain; charset=utf-8")

        if u.path != "/frame":
            return self._send(404, "not found", "text/plain; charset=utf-8")

        n = int(self.headers.get("Content-Length", "0"))
        w = int(self.headers.get("X-Width", "0"))
        h = int(self.headers.get("X-Height", "0"))
        fmt = (self.headers.get("X-Format", "rgb565") or "rgb565").lower()
        order = (self.headers.get("X-Byte-Order", "le") or "le").lower()
        data = self.rfile.read(n) if n else b""

        try:
            if w <= 0 or h <= 0:
                raise ValueError("缺少 X-Width / X-Height 头")
            img = decode_raw(data, w, h, fmt, order)
            store_image(img, fmt, len(data))
            return self._send(200, "ok", "text/plain; charset=utf-8")
        except Exception as e:
            with STATE_LOCK:
                STATE["error"] = str(e)
            return self._send(400, str(e), "text/plain; charset=utf-8")


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    port = PORT
    for i, a in enumerate(sys.argv[1:]):
        if a == "--port" and i + 2 <= len(sys.argv[1:]):
            port = int(sys.argv[i + 2])
        elif a.startswith("--port="):
            port = int(a.split("=", 1)[1])

    srv = Server(("0.0.0.0", port), Handler)
    print("camera preview server on http://0.0.0.0:%d/" % port)
    print("板子端请执行:  cam_push http://192.168.137.1:%d/frame" % port)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
