import pymupdf, re
doc = pymupdf.open(r"D:\RTT\sdk-bsp-ra8p1-titan-mini\docs\Titan_Mini_schematic_v1.0.pdf")
t = doc[4].get_text()          # p05 = USB_DEV
for pat in [r"(TS3USB\w*|USB221\w*|CH440\w*|FSUSB\w*|NL3S\w*|USB\w{2,8})", r"(J\d{1,2}\b)", r"(USBC?\w*_?CONN\w*)"]:
    print("pat", pat, "->", sorted(set(re.findall(pat, t)))[:10])
print("---- 含 USB 的行 ----")
for ln in t.splitlines():
    if re.search(r"USB|VBUS|D\+|D-|CH_SEL|CC1|CC2", ln): print("   ", ln.strip()[:95])
