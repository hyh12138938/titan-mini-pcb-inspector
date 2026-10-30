import subprocess, struct
P = r"D:\RTT\sdk-bsp-ra8p1-titan-mini\project\Titan_Mini_cam_bright"
NM = r"D:\tools\arm-gnu-toolchain-13.3.rel1-mingw-w64-i686-arm-none-eabi\bin\arm-none-eabi-nm.exe"
img = open(P + r"\_chk.bin", "rb").read()
out = subprocess.run([NM, P + r"\rtthread.elf"], capture_output=True, text=True).stdout
for line in out.splitlines():
    parts = line.split()
    if len(parts) >= 3 and parts[2].startswith("glcdc_gamma") and parts[2].endswith("_gain"):
        addr = int(parts[0], 16); size = int(parts[1], 16)
        # .text 起始 0x02000000
        off = addr - 0x02000000
        vals = struct.unpack_from("<16H", img, off)
        print(f"  {parts[2]}: addr=0x{addr:08X} size={size} 前16项={list(vals)}")
