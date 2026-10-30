from pyocd.core.helpers import ConnectHelper
for freq in (1000000, 500000):
    try:
        with ConnectHelper.session_with_chosen_probe(target_override="r7ka8p1kf", frequency=freq) as s:
            t=s.target; t.halt()
            d=bytes(t.read_memory_block8(0x68096080, 16))
            print(f"  {freq/1000:.0f} kHz: 读 SDRAM OK -> {d.hex(' ')}")
            t.resume()
            break
    except Exception as e:
        print(f"  {freq/1000:.0f} kHz: 失败 {type(e).__name__} {str(e)[:90]}")
