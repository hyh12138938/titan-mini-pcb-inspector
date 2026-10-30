P = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\project\Titan_Mini_pad_inspect\src\hal_entry.c"
s = open(P, "r", encoding="utf-8", errors="surrogateescape").read()
pairs = [
 ("#define BLACK_G    5", "#define BLACK_G    6"),
 ("#define GAIN_R16   38", "#define GAIN_R16   36"),
 ("#define GAIN_G16   33", "#define GAIN_G16   31"),
 ("#define GAIN_B16   34", "#define GAIN_B16   32"),
]
for a,b in pairs:
    assert a in s, a
    s = s.replace(a,b)
open(P, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("tuned v3")
