#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""打包 PC 侧一键安装包。

产物：dist/Titan-Mini-PCB-Inspector-Installer-v<ver>.zip
      解压后双击 install.cmd 即可。
"""
import shutil
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
INST = REPO / "installer"
PAYLOAD = INST / "payload"
DIST = REPO / "dist"
VER = "1.0.0"

# 装进 payload 的东西：PC 侧真正要跑的文件
PAYLOAD_ITEMS = [
    (REPO / "tools" / "helper", "*.py"),
    (REPO / "tools" / "helper", "*.bat"),
    (REPO / "tools" / "board-scripts", "*.py"),
]


def build() -> int:
    if PAYLOAD.exists():
        shutil.rmtree(PAYLOAD)
    PAYLOAD.mkdir(parents=True)

    n = 0
    for src, pattern in PAYLOAD_ITEMS:
        if not src.exists():
            continue
        for f in sorted(src.glob(pattern)):
            if f.name.startswith("api_key"):
                continue
            shutil.copy2(f, PAYLOAD / f.name)
            n += 1
    # 卸载脚本也要进安装目录
    if (INST / "uninstall.ps1").exists():
        shutil.copy2(INST / "uninstall.ps1", PAYLOAD / "uninstall.ps1")
        n += 1

    DIST.mkdir(exist_ok=True)
    out = DIST / f"Titan-Mini-PCB-Inspector-Installer-v{VER}.zip"
    if out.exists():
        out.unlink()

    files = [INST / "install.cmd", INST / "install.ps1"]
    files += [p for p in PAYLOAD.rglob("*") if p.is_file()]

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for p in files:
            if not p.exists():
                print(f"  跳过缺失: {p}")
                continue
            z.write(p, p.relative_to(INST) if PAYLOAD in p.parents or p.parent == INST
                    else Path("payload") / p.name)

    size = out.stat().st_size
    print("=== 安装包已生成 ===")
    print(f"  {out}")
    print(f"  payload 文件数 {n}   压缩包 {size/1024/1024:.2f} MB")
    with zipfile.ZipFile(out) as z:
        names = z.namelist()
    print(f"  包内条目 {len(names)} 个：")
    for nm in names[:20]:
        print(f"    {nm}")
    if len(names) > 20:
        print(f"    ... 其余 {len(names)-20} 个")
    return 0


if __name__ == "__main__":
    sys.exit(build())
