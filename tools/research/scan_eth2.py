import fitz, re
p = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\docs\Titan_Mini_schematic_v1.0.pdf"
doc = fitz.open(p)
page = doc[8]           # 第 9 页
pix = page.get_pixmap(matrix=fitz.Matrix(2.4, 2.4))
out = r"D:\RTT\_re\titan_docs\sch_p9_eth.png"
pix.save(out)
print(f"  渲染: {out}  ({pix.width}x{pix.height})")
print("\n=== 第 9 页文本（过滤后）===")
lines = [l.strip() for l in page.get_text().splitlines() if l.strip()]
keys = ("RTL","RJ45","HR9","MAG","GND","+3V3","1V0","1V8","2V5","MDIO","MDC","RGMII","TXD","RXD","GTX","CLK","PHY","RESET","LED","ETH","LAN","SHIELD","Y","C","R","L")
seen = []
for l in lines:
    if re.match(r"^[A-Za-z0-9_+\-\.]{1,24}$", l):
        seen.append(l)
print("  ", " ".join(seen[:160]))
doc.close()
