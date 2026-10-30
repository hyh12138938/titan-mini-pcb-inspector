P = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\project\Titan_Mini_pad_inspect\src\hal_entry.c"
s = open(P, "r", encoding="utf-8", errors="surrogateescape").read()
s = s.replace("#define GAIN_R16   36          /* 2.25x = 2.00 * 1.125 */",
              "#define GAIN_R16   38          /* 2.38x = 2.00 * 1.19  */")
open(P, "w", encoding="utf-8", errors="surrogateescape").write(s)
print("GAIN_R16 -> 38")
