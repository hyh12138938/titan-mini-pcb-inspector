from pyocd.core.helpers import ConnectHelper
with ConnectHelper.session_with_chosen_probe(target_override="r7ka8p1kf") as s:
    t=s.target; t.halt()
    A=0x22020828; N=0x58
    d=bytes(t.read_memory_block8(A,N))
    print("_lcd dump:")
    for off in range(0,N,16):
        print(f"  +0x{off:02X}: {d[off:off+16].hex(' ')}")
    for off in range(0,N-3,4):
        v=int.from_bytes(d[off:off+4],"little")
        if 0x68000000 <= v <= 0x69000000:
            print(f"  --> SDRAM pointer at +0x{off:02X} = 0x{v:08X}")
    t.resume()
