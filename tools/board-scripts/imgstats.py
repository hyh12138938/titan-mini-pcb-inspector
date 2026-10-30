from PIL import Image, ImageStat
import sys
def stats(p, label):
    im = Image.open(p).convert("RGB")
    st = ImageStat.Stat(im)
    luma = 0.299*st.mean[0] + 0.587*st.mean[1] + 0.114*st.mean[2]
    print("%-28s %sx%s  meanRGB=(%.0f,%.0f,%.0f)  luma=%.1f  max=%s" %
          (label, im.width, im.height, st.mean[0], st.mean[1], st.mean[2], luma,
           tuple(round(v) for v in st.extrema[1])))
stats(r"C:\Users\hyh7758521\.dsh\attachments\v1\objects\d5\d58e05489caa84ccbdaf398498299dc12cb2dae747ff20102ef40ced9b012ed9", "phone(real scene)")
stats(r"D:\RTT\_tmp\cam_320.png", "board(camera)")
