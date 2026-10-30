import sys, time
from pyocd.core.helpers import ConnectHelper
from pyocd.core.target import Target

BP = int(sys.argv[1], 16)

def rd(t, addr, n=32):
    try:
        return bytes(t.read_memory_block8(addr, n))
    except Exception as e:
        return b"<%s>" % str(e).encode()[:20]

with ConnectHelper.session_with_chosen_probe(target_override="r7ka8p1kf") as s:
    t = s.target
    t.reset_and_halt()
    t.set_breakpoint(BP)
    t.resume()
    end = time.time() + 8
    while time.time() < end and t.get_state() != Target.State.HALTED:
        time.sleep(0.03)
    if t.get_state() != Target.State.HALTED:
        print("NOT HIT"); t.remove_breakpoint(BP); t.resume(); sys.exit(0)
    r0 = t.read_core_register("r0"); pc = t.read_core_register("pc")
    print(f"HIT PC=0x{pc:08X} dev=0x{r0:08X}")
    raw = rd(t, r0, 24)
    print("  dev first24:", raw.hex(" "))
    print("  dev name   :", raw[:8].split(b"\x00")[0].decode("ascii","replace"))
    print("  dev type   :", int.from_bytes(raw[8:10], "little"))
    print("  dev ptr in uart_obj?")
    t.remove_breakpoint(BP)
    t.resume()
