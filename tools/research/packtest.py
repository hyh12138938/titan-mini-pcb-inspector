import glob, os, traceback
base = r"C:\Users\hyh7758521\AppData\Local\cmsis-pack-manager\cmsis-pack-manager\Renesas\RA_DFP"
packs = glob.glob(os.path.join(base, "**", "*.pack"), recursive=True)
print("pack files:", len(packs))
for p in packs: print("  ", p, f"{os.path.getsize(p)/1024/1024:.1f} MB")

from pyocd.target.pack.cmsis_pack import CmsisPack
for p in packs:
    print("\n== trying", os.path.basename(p))
    try:
        pk = CmsisPack(p)
        devs = getattr(pk, "devices", None)
        print("   loaded OK, devices:", (len(devs) if devs is not None else "?"))
        # 找 R7KA8P1KF 并强制构建 flash 区（这一步在 Studio 里就崩了）
        cand = None
        if devs:
            for d in (devs if isinstance(devs, (list, tuple)) else devs.values()):
                name = getattr(d, "part_number", None) or getattr(d, "name", "")
                if "R7KA8P1KF" in str(name).upper():
                    cand = d; break
        print("   matched device:", getattr(cand, "part_number", cand))
        if cand is not None:
            try:
                mm = cand.memory_map
                print("   memory_map OK, regions:", len(mm))
                for r in mm:
                    print("      ", r)
            except Exception as e:
                print("   !! memory_map FAILED:", type(e).__name__, e)
    except Exception as e:
        print("   !! load FAILED:", type(e).__name__, e)
