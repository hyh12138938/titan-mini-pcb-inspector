import struct
from pyocd.core.helpers import ConnectHelper
A = 0x2206CE98
STAT = {0:"INIT",1:"READY",2:"SUSPEND",3:"RUNNING",4:"CLOSE"}
with ConnectHelper.session_with_chosen_probe(target_override="r7ka8p1kf") as s:
    t = s.target
    t.halt()
    d = bytes(t.read_memory_block8(A, 96))
    name = d[0:12].split(b"\x00")[0].decode("ascii","replace")
    print("thread name:", name)
    print("raw:", d[:96].hex(" "))
    # 常见布局：parent 24, sp(24) entry(28) param(32) stack_addr(36) stack_size(40) error(44) stat(48)
    for off in (24, 28, 32, 36, 40, 44, 48, 52):
        v = int.from_bytes(d[off:off+4], "little")
        tag = ""
        if off == 48 and v in STAT: tag = "  <- stat=" + STAT[v]
        print(f"  +{off:2d} = 0x{v:08X}{tag}")
    t.resume()
