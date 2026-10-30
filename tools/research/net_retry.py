# -*- coding: utf-8 -*-
"""带重试的 UDP 客户端：板子的 VIN 与网口时分复用，命令必须反复发才能撞上窗口。

用法:
  python net_retry.py <ip|auto> time <epoch>
  python net_retry.py <ip|auto> keyfile <path>
  python net_retry.py <ip|auto> ask "<question>"
  python net_retry.py auto discover
"""
import socket
import sys
import time

PORT = 8888


def sock():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    except OSError:
        pass
    s.bind(("", PORT))
    s.settimeout(0.4)
    return s


def discover(timeout=30.0):
    s = sock()
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            d, a = s.recvfrom(1500)
            if b"TITAN" in d:
                s.close()
                return a[0]
        except socket.timeout:
            pass
    s.close()
    return None


def send_retry(ip, msg, wait=60.0):
    """板子的 VIN 与网口时分复用：只有在它发信标的那一瞬间窗口是开的，
    所以等信标 -> 立刻发命令 -> 等回复。"""
    s = sock()
    t0 = time.time()
    tries = 0
    while time.time() - t0 < wait:
        try:
            d, _ = s.recvfrom(1500)
        except socket.timeout:
            # 没等到信标也盲发一次，撞窗口
            s.sendto(msg.encode("utf-8"), (ip, PORT))
            tries += 1
            continue

        if b"TITAN" not in d:
            continue

        # 刚收到信标：此刻一定在窗口里，立刻发
        s.sendto(msg.encode("utf-8"), (ip, PORT))
        tries += 1

        end = time.time() + 4.0
        while time.time() < end:
            try:
                d2, _ = s.recvfrom(4000)
            except socket.timeout:
                continue
            txt = d2.decode("utf-8", "replace").strip()
            if txt and txt != "TITAN alive":
                s.close()
                return txt, tries, time.time() - t0
    s.close()
    return None, tries, time.time() - t0


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2

    target, cmd = sys.argv[1], sys.argv[2]
    ip = None
    if target == "auto":
        ip = discover()
        if ip is None:
            print("!! 没有发现板子")
            return 1
        print(f"board = {ip}")
        if cmd == "discover":
            return 0
    else:
        ip = target

    if cmd == "time":
        msg = "time " + sys.argv[3]
    elif cmd == "keyfile":
        msg = "key " + open(sys.argv[3], encoding="utf-8").read().strip()
    elif cmd == "key":
        msg = "key " + sys.argv[3]
    else:
        msg = " ".join(sys.argv[2:])

    r, tries, dt = send_retry(ip, msg)
    if r is None:
        print(f"!! 无回复（试了 {tries} 次 / {dt:.1f}s）")
        return 1
    print(f"[{dt:.1f}s / {tries} tries] {r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
