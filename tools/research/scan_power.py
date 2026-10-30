# -*- coding: utf-8 -*-
"""在官方 Titan Mini 用户手册/数据手册/原理图中检索供电相关内容。"""
import re
import sys

import fitz

DOCS = {
    "用户手册": r"D:\RTT\sdk-bsp-ra8p1-titan-mini\docs\Titan_Mini_user_manual.pdf",
    "数据手册": r"D:\RTT\sdk-bsp-ra8p1-titan-mini\docs\Titan_Mini_datasheet.pdf",
    "原理图": r"D:\RTT\sdk-bsp-ra8p1-titan-mini\docs\Titan_Mini_schematic_v1.0.pdf",
}

KEYS = ["供电", "电源", "USB", "Type-C", "TYPE-C", "VBUS", "5V", "3.3V", "3V3", "电池", "电流", "功耗", "POE", "DC-IN"]


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    for name, path in DOCS.items():
        if only and only not in name:
            continue
        try:
            doc = fitz.open(path)
        except Exception as e:
            print(f"  {name}: 打不开 ({e})")
            continue
        print(f"\n=== {name}  共 {doc.page_count} 页 ===")
        hits = 0
        for pno in range(doc.page_count):
            try:
                txt = doc[pno].get_text()
            except Exception:
                continue
            if not txt:
                continue
            found = [k for k in KEYS if k in txt]
            if not found:
                continue
            # 只打印含强关键词的页面
            if not any(k in txt for k in ("供电", "电源", "VBUS", "Type-C", "DC-IN")):
                continue
            hits += 1
            lines = [l.strip() for l in txt.splitlines() if l.strip()]
            keep = []
            for i, l in enumerate(lines):
                if any(k in l for k in KEYS):
                    ctx = lines[max(0, i - 1):i + 2]
                    keep.append(" | ".join(ctx))
            print(f"  --- 第 {pno + 1} 页 (命中关键词: {', '.join(found)})")
            for k in keep[:14]:
                print("      " + k[:180])
            if hits >= 12:
                print("  (已达 12 页上限)")
                break
        if hits == 0:
            print("  (未找到含供电关键词的文本页)")
        doc.close()


if __name__ == "__main__":
    main()
