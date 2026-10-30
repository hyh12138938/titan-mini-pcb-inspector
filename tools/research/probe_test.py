from pyocd.core.helpers import ConnectHelper
try:
    with ConnectHelper.session_with_chosen_probe(target_override="r7ka8p1kf") as s:
        t=s.target
        t.halt()
        print("  halt OK, PC=0x%08X" % t.read_core_register("pc"))
        d=bytes(t.read_memory_block8(0x02000000, 16))
        print("  读 MRAM:", d.hex(" "))
        w=bytes(t.read_memory_block8(0x68096080, 16))
        print("  读 SDRAM:", w.hex(" "))
        t.resume()
        print("  基本读操作正常")
except Exception as e:
    print("  失败:", type(e).__name__, str(e)[:160])
