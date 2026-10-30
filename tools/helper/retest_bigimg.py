#!/usr/bin/env python3
"""retest_bigimg.py - one-command big-image retest for Titan Mini + DeepSeek cloud.

What it does (no GUI, no clicking):
  1. finds the CH340 console port (auto, or --port),
  2. serves D:\\RTT\\ai_images over HTTP on <lan-host>:8000 so the board can
     download the image itself (vlm_url path),
  3. sets the board clock (TLS needs a valid date) and re-applies the API key,
  4. runs `vlm_url <url> <question>` and captures the whole board log,
  5. judges the log: upload complete? chunked decoded? JSON parsed? answer text?

Usage:
  python D:\\RTT\\apps\\retest_bigimg.py --check            # environment only, no serial
  python D:\\RTT\\apps\\retest_bigimg.py                    # default 232 KB original
  python D:\\RTT\\apps\\retest_bigimg.py --image probe_128k.jpg
  python D:\\RTT\\apps\\retest_bigimg.py --port COM4 --question "describe this board"

Exit code: 0 = pass, 1 = fail, 2 = environment problem.
"""
import argparse
import datetime
import http.server
import os
import re
import socket
import sys
import threading
import time

IMG_DIR = r"D:\RTT\ai_images"
KEY_FILE = r"D:\RTT\apps\api_key.txt"
LOG_DIR = r"D:\RTT\_tmp"
DEFAULT_IMAGE = "img_20261022_124200_0.jpg"   # 237895 B original
DEFAULT_QUESTION = "describe this image in detail"
PROMPT_RE = re.compile(r"msh\s*/>\s*$")


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def read_key():
    try:
        with open(KEY_FILE, "r", encoding="utf-8", errors="replace") as f:
            k = f.read().strip()
        return k if k.startswith("sk-") else ""
    except OSError:
        return ""


def list_ports():
    from serial.tools import list_ports
    return list(list_ports.comports())


def pick_port():
    """Prefer a USB-UART bridge (CH340/CP210x/FTDI), never the DAP-Link CDC."""
    ports = list_ports()

    def score(p):
        d = (p.description or "").upper()
        s = 0
        if "CH340" in d or "CH341" in d:
            s += 20
        if "CP210" in d or "FTDI" in d or "USB-SERIAL" in d or "USB SERIAL" in d:
            s += 10
        if "DAP" in d or "CMSIS" in d or "DEBUG" in d:
            s -= 50
        return s

    if not ports:
        return None, ""
    ports.sort(key=score, reverse=True)
    best = ports[0]
    return best.device, best.description or ""


def pc_ip_for_board():
    """The ICS adapter address the board can reach; fall back to detection."""
    import subprocess
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command",
                              "Get-NetIPAddress -AddressFamily IPv4 | "
                              "Where-Object {$_.IPAddress -like '192.168.137.*'} | "
                              "Select-Object -First 1 -ExpandProperty IPAddress"],
                             capture_output=True, text=True, timeout=20).stdout.strip()
        if out:
            return out.splitlines()[0].strip()
    except Exception:
        pass
    return "192.168.137.1"


def port_is_free(host, port):
    s = socket.socket()
    s.settimeout(1.0)
    try:
        s.connect((host, port))
        return False
    except OSError:
        return True
    finally:
        s.close()


class QuietHTTP(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=IMG_DIR, **kw)

    def log_message(self, *a):
        pass


def start_http(port=8000):
    """Return (server, thread) or (None, None) if the port is already served."""
    try:
        httpd = http.server.ThreadingHTTPServer(("0.0.0.0", port), QuietHTTP)
    except OSError as e:
        print(f"[net] cannot bind 0.0.0.0:{port} ({e}) - assuming it is already served")
        return None, None
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    print(f"[net] serving {IMG_DIR} on 0.0.0.0:{port}")
    return httpd, t


# --------------------------------------------------------------------------- #
# board console
# --------------------------------------------------------------------------- #
class Board:
    def __init__(self, port, baud=115200, verbose=True):
        import serial
        self.ser = serial.Serial(port, baud, timeout=0.2)
        self.buf = ""
        self.verbose = verbose
        self.log = []

    def _pump(self, secs):
        end = time.time() + secs
        while time.time() < end:
            chunk = self.ser.read(8192)
            if not chunk:
                continue
            text = chunk.decode("utf-8", "replace")
            self.buf += text
            self.log.append(text)
            if self.verbose:
                sys.stdout.write(text)
                sys.stdout.flush()

    def send(self, line):
        if self.verbose:
            print(f"\n>>> {line}")
        self.ser.write((line + "\r").encode("utf-8"))

    def run(self, line, timeout=15.0, settle=0.3):
        """Send one msh command and wait for the prompt to come back."""
        start = len(self.buf)
        self.send(line)
        deadline = time.time() + timeout
        while time.time() < deadline:
            self._pump(0.2)
            tail = self.buf[start:]
            if PROMPT_RE.search(tail):
                break
        self._pump(settle)
        return self.buf[start:]

    def wait_prompt(self, timeout=10.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            self._pump(0.2)
            if PROMPT_RE.search(self.buf):
                return True
        return False

    def close(self):
        try:
            self.ser.close()
        except Exception:
            pass


# --------------------------------------------------------------------------- #
# judging
# --------------------------------------------------------------------------- #
def judge(log, img_bytes):
    """Return (passed: bool, findings: list[str])."""
    f = []
    ok = True

    m = re.search(r"\[llm\] POST (\S+)\s+model=(\S+)\s+body=(\d+) B", log)
    if m:
        f.append(f"request: {m.group(1)} model={m.group(2)} body={m.group(3)} B")
    else:
        ok = False
        f.append("request: no '[llm] POST' line - command did not run")

    m = re.search(r"\[llm\] HTTP (\d+)\s+\((\d+) ms\)", log)
    if m:
        status = int(m.group(1))
        f.append(f"http: {status} in {m.group(2)} ms")
        if status != 200:
            ok = False
    else:
        ok = False
        f.append("http: no '[llm] HTTP' line")

    if "post body incomplete" in log:
        ok = False
        f.append("upload: FAIL - 'post body incomplete' seen")
    else:
        f.append("upload: no 'post body incomplete' marker")

    m = re.search(r"\[llm\] body received=(\d+) B", log)
    if m:
        got = int(m.group(1))
        f.append(f"response body: {got} B")
        if got == 0:
            ok = False
            f.append("response: FAIL - 0 B received")
    else:
        ok = False
        f.append("response: no 'body received' line")

    if "[llm] de-chunked -> " in log:
        m = re.search(r"\[llm\] de-chunked -> (\d+) B", log)
        f.append(f"chunked: fallback decode used -> {m.group(1)} B (webclient header path still missed)")
    else:
        f.append("chunked: fallback decode not needed")

    if "JSON parse failed" in log:
        ok = False
        f.append("json: FAIL - parse failed")

    if "[llm] empty response" in log:
        ok = False

    # answer text: "A: ..." printed by the firmware
    m = re.search(r"\nA: (.*?)(?:\nmsh\s*/>|\Z)", log, re.S)
    if m:
        ans = m.group(1).strip()
        f.append(f"answer: {len(ans)} chars")
        f.append("answer preview: " + (ans[:160].replace("\n", " ") + ("..." if len(ans) > 160 else "")))
        if not ans:
            ok = False
            f.append("answer: FAIL - empty")
    else:
        ok = False
        f.append("answer: FAIL - no 'A:' line in log")

    return ok, f


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default=None, help="serial port, e.g. COM4 (default: auto)")
    ap.add_argument("--image", default=DEFAULT_IMAGE, help="image file name inside D:\\RTT\\ai_images")
    ap.add_argument("--question", default=DEFAULT_QUESTION)
    ap.add_argument("--timeout", type=float, default=120.0, help="seconds to wait for the answer")
    ap.add_argument("--host", default=None, help="IP the board should use to reach this PC")
    ap.add_argument("--skip-key", action="store_true", help="do not re-send llm_key")
    ap.add_argument("--check", action="store_true", help="environment check only, no serial")
    args = ap.parse_args()

    os.makedirs(LOG_DIR, exist_ok=True)

    # ---- environment -------------------------------------------------------
    img_path = os.path.join(IMG_DIR, args.image)
    print("=" * 70)
    print("Titan Mini <-> DeepSeek  big-image retest")
    print("=" * 70)
    print(f"image   : {img_path}")
    print(f"exists  : {os.path.isfile(img_path)}")
    if not os.path.isfile(img_path):
        print("FAIL: image not found (add it under D:\\RTT\\ai_images)")
        return 2
    img_bytes = os.path.getsize(img_path)
    print(f"size    : {img_bytes} B  ({img_bytes/1024:.1f} KB)")

    key = read_key()
    print(f"api key : {'(set, ' + key[:6] + '...' + str(len(key)) + ' chars)' if key else 'MISSING ' + KEY_FILE}")

    port, desc = (args.port, "from --port") if args.port else pick_port()
    print(f"serial  : {port or '(none found)'}  {desc}")
    if args.check:
        print(f"http    : port 8000 {'free (will start)' if port_is_free('127.0.0.1', 8000) else 'already in use'}")
        print(f"board ip: {args.host or pc_ip_for_board()}")
        print("check done (no serial opened)")
        return 0 if port else 2

    if not port:
        print("FAIL: no serial port found - is the CH340 (COM4) cable plugged in?")
        return 2
    if not key and not args.skip_key:
        print(f"FAIL: no API key ({KEY_FILE}); board would answer HTTP 401")
        return 2

    host = args.host or pc_ip_for_board()
    url = f"http://{host}:8000/{args.image}"
    print(f"url     : {url}")
    httpd, _ = start_http(8000)

    # ---- drive the board ---------------------------------------------------
    board = Board(port)
    result_code = 1
    try:
        print("\n--- opening console ---")
        if not board.wait_prompt(3.0):
            board.send("")            # nudge
            if not board.wait_prompt(5.0):
                print("FAIL: no 'msh />' prompt (port busy? board not booted? wrong port?)")
                return 2

        print("\n--- llm_info ---")
        info = board.run("llm_info", timeout=10)
        key_ok = "(set)" in info or "key: set" in info.lower()

        print("\n--- date ---")
        now = datetime.datetime.now()
        board.run(now.strftime("date %Y %m %d %H %M %S"), timeout=10)

        if key and not args.skip_key:
            print("\n--- llm_key ---")
            board.run("llm_key " + key, timeout=10)
        elif not key_ok:
            print("\nWARN: key not set on board and no key file; response will be 401")

        print(f"\n--- vlm_url ({img_bytes} B, timeout {args.timeout:.0f} s) ---")
        board.run(f"vlm_url {url} {args.question}", timeout=args.timeout, settle=1.0)

        log = "".join(board.log)
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = os.path.join(LOG_DIR, f"retest_bigimg_{stamp}.log")
        with open(log_path, "w", encoding="utf-8", errors="replace") as f:
            f.write(log)
        print(f"\nlog saved: {log_path}")

        passed, findings = judge(log, img_bytes)
        print("\n" + "=" * 70)
        print("VERDICT:", "PASS" if passed else "FAIL")
        for line in findings:
            print("  -", line)
        print("=" * 70)
        result_code = 0 if passed else 1
    except KeyboardInterrupt:
        print("\ninterrupted")
        result_code = 2
    finally:
        board.close()
        if httpd:
            httpd.shutdown()
    return result_code


if __name__ == "__main__":
    sys.exit(main())
