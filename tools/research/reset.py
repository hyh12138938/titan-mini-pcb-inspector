from pyocd.core.helpers import ConnectHelper
import time
with ConnectHelper.session_with_chosen_probe(target_override="r7ka8p1kf") as s:
    t=s.target
    t.reset_and_halt()
    time.sleep(0.2)
    t.resume()
    print("  reset done")
