P = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\project\Titan_Mini_pad_inspect\src\hal_entry.c"
s = open(P, "r", encoding="utf-8", errors="surrogateescape").read()
pairs = [
 ("#define BLACK_R    3", "#define BLACK_R    2"),
 ("#define BLACK_G    7", "#define BLACK_G    5"),
 ("#define BLACK_B    3", "#define BLACK_B    2"),
 ("#define GAIN_R16   34", "#define GAIN_R16   38"),
 ("#define GAIN_G16   29", "#define GAIN_G16   33"),
 ("#define GAIN_B16   30", "#define GAIN_B16   34"),
]
for a,b in pairs:
    assert a in s, a
    s = s.replace(a,b)
open(P, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("tuned")
