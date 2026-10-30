import re, collections
import fitz
p = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\docs\Titan_Mini_schematic_v1.0.pdf"
doc = fitz.open(p)
print(f"  原理图共 {doc.page_count} 页")
nets = collections.Counter()
pages = []
for i in range(doc.page_count):
    t = doc[i].get_text()
    pages.append(t)
    for tok in re.findall(r"[A-Z0-9_+\-/\.]{2,24}", t):
        u = tok.upper()
        if any(k in u for k in ("VBUS","VIN","5V","3V3","3.3V","VCC","GND","PWR","POWER","DC","BAT","USB")):
            nets[u] += 1
print("  与电源相关的网络名（按出现次数）:")
for k,v in nets.most_common(40):
    print(f"    {k:24s} {v}")
print("\n  每页前 3 个含电源词的片段:")
for i,t in enumerate(pages):
    lines=[l.strip() for l in t.splitlines() if l.strip()]
    hit=[l for l in lines if any(k in l.upper() for k in ("VBUS","VIN","5V","3V3","PWR","POWER","BAT","DC-","USB"))]
    if hit:
        print(f"    p{i+1}: " + " / ".join(hit[:3])[:150])
doc.close()
