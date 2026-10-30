from pyocd.core.helpers import ConnectHelper
# RA8: PORTS base 0x40400000, stride 0x20 -> PORT3 = 0x40400060
BASE = 0x40400060
with ConnectHelper.session_with_chosen_probe(target_override="r7ka8p1kf") as s:
    t = s.target
    t.halt()
    pcntr1 = t.read32(BASE + 0x00)
    pdr = pcntr1 & 0xFFFF
    podr = (pcntr1 >> 16) & 0xFFFF
    print(f"PORT3.PCNTR1 = 0x{pcntr1:08X}")
    print(f"  PDR  = 0x{pdr:04X}  (bit3 = {'OUTPUT' if pdr & (1<<3) else 'input'})")
    print(f"  PODR = 0x{podr:04X}  (bit3 = {'HIGH' if podr & (1<<3) else 'LOW'})")
    # PFS 区：P303 的 PMR
    try:
        pfs = t.read32(0x40400800 + 0x03 * 0x40 + 0x03 * 4)
        print(f"  P303.PFS(PmnPfs) = 0x{pfs:08X}  PMR(bit16)={'1 (peripheral)' if pfs & (1<<16) else '0 (GPIO)'}  PDR={'1' if pfs & (1<<8) else '0'}  PODR={'1' if pfs & (1<<12) else '0'}")
    except Exception as e:
        print("  PFS 读取失败:", e)
    t.resume()
