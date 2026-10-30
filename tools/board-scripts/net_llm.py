# -*- coding: utf-8 -*-
"""PC 侧 UDP 客户端：发现板子 -> 下发 key -> 问模型。

用法:
  python net_llm.py --discover                 # 只听信标，打印板子 IP
  python net_llm.py --ip 192.168.137.x ping
  python net_llm.py --ip 192.168.137.x keyfile D:\\RTT\\apps\\api_key.txt
  python net_llm.py --ip 192.168.137.x ask "你好"
"""
import argparse
import os
import socket
import sys
import time

PORT = 8888


def make_sock():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    except OSError:
        pass
    s.bind(("", PORT))
    return s


def discover(timeout=30.0):
    s = make_sock()
    s.settimeout(1.0)
    t0 = time.time()
    while time.time() - t0 < timeout:
        try:
            d, a = s.recvfrom(1500)
        except socket.timeout:
            continue
        txt = d.decode("utf-8", "replace").strip()
        print(f"  packet from {a[0]}:{a[1]}  {txt[:60]}")
        if "TITAN" in txt:
            s.close()
            return a[0]
    s.close()
    return None


def talk(ip, msg, wait=30.0, quiet=False):
    s = make_sock()
    s.settimeout(1.0)
    s.sendto(msg.encode("utf-8"), (ip, PORT))
    t0 = time.time()
    while time.time() - t0 < wait:
        try:
            d, a = s.recvfrom(4000)
        except socket.timeout:
            continue
        txt = d.decode("utf-8", "replace")
        if txt.strip() == "TITAN alive":
            continue
        s.close()
        return txt
    s.close()
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ip", default=None)
    ap.add_argument("--discover", action="store_true")
    ap.add_argument("cmd", nargs="*", default=[])
    a = ap.parse_args()

    ip = a.ip
    if ip is None or a.discover:
        print("listening for the board beacon on udp/%d ..." % PORT)
        ip = discover()
        if ip is None:
            print("!! 没收到信标（防火墙？板子不在线？）")
            return 1
        print(f"board = {ip}")
        if a.discover and not a.cmd:
            return 0

    if not a.cmd:
        return 0

    if a.cmd[0] == "keyfile":
        key = open(a.cmd[1], encoding="utf-8").read().strip()
        r = talk(ip, "key " + key)
        print(f"  keyfile -> {r}")
        return 0

    msg = " ".join(a.cmd)
    t0 = time.time()
    r = talk(ip, msg, wait=90.0)
    dt = time.time() - t0
    if r is None:
        print("!! 没有回复")
        return 1
    print(f"  [{dt:.1f}s] {r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
