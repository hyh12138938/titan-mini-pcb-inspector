import sys, time, tkinter as tk
sys.path.insert(0, r"D:\RTT\apps")
import cam_view
root = tk.Tk()
root.title("cam_view selftest")
root.geometry("352x330")
panel = cam_view.CameraPanel(root)
panel.pack(fill="both", expand=True, padx=8, pady=8)
def shot():
    try:
        import pyautogui
    except Exception:
        pass
    root.destroy()
root.after(2500, shot)
root.mainloop()
print("panel rendered ok; has image =", panel._photo is not None)
