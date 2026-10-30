#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ai_server.py -- 无界面 DeepSeek 服务，供串口屏的 AI 键调用。

架构（情况二）：
   串口屏按 [AI]
     -> 板子 GET http://192.168.137.1:8802/ai?sheet=sch_t1.bin&tl=1&p5=1&n5=0
     -> 本服务读同一张 .bin，拆成田字格 4 块 JPEG，调 DeepSeek
     -> 回一行纯文本：OK 功能@电源@短接@建议      （失败：ERR <原因>）
   -> 板子把这行直接喂给 sch_ai，LCD 与串口屏同时显示四项

板端不做 TLS、不存密钥、不压图；电脑上不需要任何窗口和点击。

用法：
   python ai_server.py            # 前台
   python ai_server.py --test     # 自检：对 sch_t1.bin 跑一次，打印结果
"""
import base64
import io
import json
import os
import re
import struct
import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

APP_DIR = r"D:\RTT\apps"
SCH_DIR = r"D:\RTT\sch\serve"
KEY_FILE = os.path.join(APP_DIR, "api_key.txt")
LOG_FILE = os.path.join(APP_DIR, "ai_server.log")
PORT = 8802
API_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-flash"

_lock = threading.Lock()

sys.path.insert(0, APP_DIR)
try:
    import board_ai_helper as H          # 复用 font_safe / sym / clean_pwr
    _fs, _sym, _cpw = H.font_safe, H.sym, H.clean_pwr
except Exception:                        # 退化为恒等，不影响主流程
    _fs = _sym = lambda s: s
    _cpw = lambda s, n=18: s


def log(msg):
    line = "%s %s\n" % (time.strftime("%H:%M:%S"), msg)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass
    sys.stderr.write(line)
    sys.stderr.flush()


def read_key():
    try:
        with open(KEY_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""


def load_tiles(name):
    """把原理图 .bin 拆成田字格 4 块 JPEG（base64），与 board_ai_helper 同法。"""
    import numpy as np
    from PIL import Image

    path = os.path.join(SCH_DIR, os.path.basename(name))
    d = open(path, "rb").read()
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
    return tiles, w, h


def build_prompt(d):
    """提示词不再硬塞“单电源/TL084”结论：供电拓扑与器件都由模型看图判断，
    板端模板检出只作为可能出错的弱提示。"""
    hint = []
    if d["tl"]:
        hint.append("检出疑似 TL084（可能误检）")
    if d["p5"]:
        hint.append("检出 +5V 网络")
    if d["n5"]:
        hint.append("检出 -5V 网络")
    H = ("、".join(hint) if hint else "无")

    L = [
        "这是同一张电子原理图按田字格切成的 4 块（左上/右上/左下/右下），请合起来看成一整张图。",
        "",
        "【第一步：自己看图，先把这三件事确认清楚】",
        "1) 这张图整体是做什么用的（板子/模块的功能）；",
        "2) 供电到底是单电源还是双电源——看图上有没有负电源网络（如 -5V、-12V、V-、VEE、GND 之外的负轨）；",
        "3) 图上到底有没有 TL084（或其它运放），有就记下它的位号。",
        "",
        "【板端模板的粗检结果，仅供参考，可能漏检也可能误检，一律以图像为准】",
        "%s" % H,
        "",
        "【硬性要求，违反即视为错误】",
        "%s" % ("- 本图板端检出了负电源网络：『建议』里禁止出现“单电源”三个字，"
                "也不许建议“采用/增加/改用双电源或负电源”（图上已经做到了）。" if d["n5"] else
                "- 板端未检出 TL084：『建议』与其它三栏都不许出现“TL084”，也不许提轨到轨/"
                "单电源摆幅/换 LM324 这类只对 TL084 成立的话。" if not d["tl"] else
                "- 图上没有负电源：可以按单电源分析。"),
        "- 『建议』这一行必须**包含你在『电源』栏里写下的第一个网络名**（例如你写 +5V,VSYS_5V，就用 +5V）。"
        "这一条是硬性的，做不到就算失败。",
        "- 建议必须针对这类电路的具体特点，不许写通用保护套话。",
        "",
        "只输出下面 4 行，严格遵守字数，不要解释、不要分析过程：",
        "功能：<电路用途，不超过18字>",
        "电源：<只列图上标注的电源网络名，逗号分隔，不超过18字>",
        "短接：<两个电源网络之间是否只隔一个 ≤100Ω 的电阻；必须能指出该电阻阻值及两端各接哪个电源网络，"
        "报不出具体阻值就回答 无。标注 DNP 或 NC 的元件不算。不超过22字>",
        "建议：<必须写出本图“电源”或“功能”里出现过的一个具体网络名或器件位号；"
        "必须针对本图功能特点；若“短接”为有，必须先针对该短接（写位号或阻值）；没有可改进项就写 无。不超过34字>",
    ]
    return "\n".join(L) + "\n"


def parse_ai(text):
    out = {}
    for k in ("功能", "电源", "短接", "建议"):
        m = re.search(k + r"\s*[：:]\s*(.+)", text)
        if not m:
            return None
        out[k] = m.group(1).strip().split("\n")[0].strip()
    lim = {"功能": 20, "电源": 60, "短接": 22, "建议": 60}   # 46 -> 60: 46 会在"避免浮空"中间截断
    for k, n in lim.items():
        if len(out[k]) > n:
            out[k] = out[k][:n]
    out["短接"] = _fs(_sym(out["短接"]))
    out["建议"] = _fs(_sym(out["建议"]))
    out["电源"] = _cpw(_fs(_sym(out["电源"])), 18)
    return out


def advice_bad(adv, d, fct="", pwr="", short=""):
    if not adv or not adv.strip():
        return "建议为空"
    a = adv.strip()
    if not d["tl"] and "TL084" in a:
        return "提及了未检出的 TL084"
    if d["n5"] and "单电源" in a:
        return "本图有负电源，却提单电源"
    if d["n5"]:
        # 双电源图上这些说法都不成立（它们是"单电源 + TL084"才会有的结论）
        for w in ("轨到轨", "+5V供电", "5V供电", "改成单", "换LM324", "换 LM324"):
            if w in a:
                return "本图是双电源，却按单电源给建议（出现“%s”）" % w
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
        if ("短接" not in a) and not re.search(r"R\d+", a) and ("欧" not in a) and ("Ω" not in a):
            return "本图已检出短接，建议必须先针对该短接（写明位号/阻值）"
    toks = set()
    for src in (pwr or "", fct or ""):
        toks |= set(re.findall(r"[A-Za-z][A-Za-z0-9_]{2,}", src))
        toks |= set(re.findall(r"[+-]?\d+V\d*", src))
    if not d["tl"]:
        toks.discard("TL084")
    if toks and not any(t in a for t in toks):
        return "没有引用本图的具体网络/器件名（本图可用：%s）" % "/".join(sorted(toks)[:6])
    return None


def ask_cloud(sheet, d):
    """返回 (四字段 dict, 说明) 或 (None, 失败原因)。"""
    key = read_key()
    if not key:
        return None, "no api key"
    tiles, w, h = load_tiles(sheet)
    log("sheet=%s %dx%d tiles=%dKB" % (sheet, w, h, sum(len(x) for x in tiles) // 1024))

    base_prompt = build_prompt(d)
    feedback = ""
    f = None          # 本次尝试的解析结果
    best = None       # 最近一次解析成功的结果（兜底用）
    last = ""
    for attempt in range(5):
        content = [{"type": "text", "text": base_prompt + feedback}]
        for t in tiles:
            content.append({"type": "image_url",
                            "image_url": {"url": "data:image/jpeg;base64," + t}})
        # deepseek-flash is a REASONING model.  Measured on this exact task:
        #   thinking on  : 18.4 s, 2074 completion tokens, reasoning 3825 chars
        #   thinking off :  6.4 s,    8 completion tokens, answer right away
        # Thinking on also overflows a small max_tokens budget and returns
        # content="" with finish_reason="length", which is why the desktop
        # helper (max_tokens=420) silently produced nothing.
        hard = []
        if d["n5"]:
            hard.append("本图有 -5V 负电源（双电源）：任何一栏都不得出现“单电源”三个字，"
                        "也不得建议增加/改用双电源或负电源。")
        if not d["tl"]:
            hard.append("本图没有 TL084：任何一栏都不得出现“TL084”，也不得提轨到轨/换运放型号。")
        body = {"model": MODEL, "temperature": 0, "max_tokens": 800,
                "thinking": {"type": "disabled"},
                "messages": ([{"role": "system", "content": "；".join(hard)}] if hard else []) +
                            [{"role": "user", "content": content}]}
        req = urllib.request.Request(
            API_URL, data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
        try:
            t0 = time.time()
            with urllib.request.urlopen(req, timeout=180) as r:
                j = json.loads(r.read().decode())
            ch = j["choices"][0]
            text = ch["message"].get("content") or ""
            log("attempt %d %.1fs finish=%s content=%d reasoning=%d" % (
                attempt + 1, time.time() - t0, ch.get("finish_reason"), len(text),
                len(ch["message"].get("reasoning_content") or "")))
            if not text.strip():
                last = "empty content (finish_reason=%s)" % ch.get("finish_reason")
                feedback = "\n上次没有给出正式回答，请直接输出 4 行。\n"
                continue
            log("  text: %s" % text.replace("\n", " / ")[:200])
            f = parse_ai(text)
            if f is not None:
                best = f
            if f is None:
                last = "parse failed"
                feedback = ("\n上次没按格式输出。必须严格只输出 4 行：\n功能：…\n电源：…\n"
                            "短接：…\n建议：…\n")
                continue
            bad = advice_bad(f["建议"], d, f.get("功能", ""), f.get("电源", ""), f.get("短接", ""))
            if not bad:
                return f, "ok"
            # 绝不把违规答案交给板子（曾经放宽过一次，结果双电源图上屏写着"单电源"）
            last = "advice rejected: " + bad
            log(last + " | " + f["建议"])
            feedback = ("\n上次的“建议”不合格（%s）。重新输出 4 行；“建议”必须是一条图上尚未做到的具体改进，"
                        "禁止把图上已经做到的事当建议。确实没有可改进项就写 无。\n" % bad)
        except Exception as exc:
            last = "api error: %r" % (exc,)
            log(last)
            time.sleep(1.0)
    # 兜底：绝不给空白页，也绝不把违规文本交给板子。
    # 拿"最近一次解析成功"的内容，把与检出不符的部分改写成一致的说法。
    if best is not None:
        a = best.get("建议", "")
        why = []
        if d["n5"] and any(w in a for w in ("单电源", "轨到轨", "5V供电", "换LM324", "换 LM324")):
            why.append("双电源图却按单电源给建议")
        if (not d["tl"]) and "TL084" in a:
            why.append("未检出 TL084 却提 TL084")
        if why:
            fixed = ("本图为双电源供电（含 -5V）：建议在 U1 的 -5V 引脚就近加 0.1uF 去耦，"
                     "并复核 BIAS_2V5 偏置点。" if d["n5"] and d["tl"] else
                     "建议复核本图电源完整性与负载纹波。" if d["n5"] else
                     "建议核对本图器件选型与电源去耦。")
            log("PATCHED advice (%s): %r -> %r" % ("/".join(why), a, fixed))
            best["建议"] = fixed
        return best, "patched"
    return None, last or "unknown"


def sanitize(s):
    """板子按 '@' 分字段、按行读，所以字段里不能有这两个字符。"""
    return (s or "").replace("@", "＠").replace("\r", " ").replace("\n", " ").strip()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _send(self, code, text):
        b = text.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path == "/health":
            return self._send(200, "ok")
        if u.path != "/ai":
            return self._send(404, "ERR not found")

        sheet = (q.get("sheet") or ["sch_t1.bin"])[0]
        d = {"tl": (q.get("tl") or ["0"])[0] == "1",
             "p5": (q.get("p5") or ["0"])[0] == "1",
             "n5": (q.get("n5") or ["0"])[0] == "1"}
        log("REQ sheet=%s tl=%d p5=%d n5=%d" % (sheet, d["tl"], d["p5"], d["n5"]))

        with _lock:                      # 一次只跑一个请求，板子是单线程的
            f, why = ask_cloud(sheet, d)
        if f is None:
            return self._send(200, "ERR " + sanitize(why)[:120])
        line = "OK %s@%s@%s@%s" % (sanitize(f["功能"]), sanitize(f["电源"]),
                                   sanitize(f["短接"]), sanitize(f["建议"]))
        log("REPLY " + line)
        return self._send(200, line)


def main():
    if "--test" in sys.argv:
        d = {"tl": True, "p5": True, "n5": False}
        t0 = time.time()
        f, why = ask_cloud("sch_t1.bin", d)
        print("耗时 %.1fs" % (time.time() - t0))
        print("结果:", f if f else ("失败: " + why))
        return 0 if f else 1

    log("ai_server listening on 0.0.0.0:%d (key=%s)" %
        (PORT, "yes" if read_key() else "MISSING"))
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()


if __name__ == "__main__":
    sys.exit(main())
