import sys, re
from pypdf import PdfReader
docs = {
 "datasheet": r"D:\RTT\sdk-bsp-ra8p1-titan-mini\docs\Titan_Mini_datasheet.pdf",
 "usermanual": r"D:\RTT\sdk-bsp-ra8p1-titan-mini\docs\Titan_Mini_user_manual.pdf",
}
for name, path in docs.items():
    try:
        r = PdfReader(path)
        txt = []
        for i, p in enumerate(r.pages):
            try:
                txt.append(p.extract_text() or "")
            except Exception:
                pass
        all_txt = "\n".join(txt)
        out = rf"D:\RTT\_re\{name}.txt"
        open(out, "w", encoding="utf-8").write(all_txt)
        print(f"{name}: pages={len(r.pages)} chars={len(all_txt)} -> {out}")
    except Exception as e:
        print(f"{name}: FAIL {e}")
