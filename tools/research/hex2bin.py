import sys
hexf = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\project\Titan_Mini_display_camera_mipi_csi\rtthread.hex"
base = 0x02000000
limit = 0x02100000          # 只取 MRAM 1MB 窗口
mem = {}
upper = 0
for line in open(hexf):
    line = line.strip()
    if not line.startswith(':'): continue
    n = int(line[1:3],16); addr = int(line[3:7],16); typ = int(line[7:9],16)
    data = bytes.fromhex(line[9:9+2*n])
    if typ == 0x04: upper = int.from_bytes(data,'big') << 16
    elif typ == 0x00:
        a = upper + addr
        for i,b in enumerate(data):
            if base <= a+i < limit: mem[a+i] = b
if not mem:
    print("no data in flash window"); sys.exit(1)
lo, hi = min(mem), max(mem)
out = bytearray(hi-lo+1)
for a,b in mem.items(): out[a-lo] = b
open(hexf.replace('.hex','.bin'),'wb').write(out)
print(f"bin: start=0x{lo:08X} end=0x{hi:08X} size={len(out)} bytes ({len(out)/1024:.1f} KB)")
print("first8:", out[:8].hex(' ').upper())
