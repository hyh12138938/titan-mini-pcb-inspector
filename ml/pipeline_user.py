# -*- coding: utf-8 -*-
"""
一条龙：ONNX -> float tflite -> int8(校准) -> Vela 编译 -> C 数组

用法：
    python pipeline_user.py --onnx D:\\RTT\\ml\\out_user\\pad_model.onnx \
                            --data D:\\RTT\\ml\\data\\pad_user \
                            --work D:\\RTT\\ml\\out_user
"""
import argparse
import glob
import os
import random
import shutil
import subprocess
import sys

import numpy as np
import onnx
from PIL import Image

VENV = r"D:\RTT\ml\venv\Scripts"
IMG = 96


def step(msg):
    print(f"\n===== {msg} =====", flush=True)


def inline_onnx(src, dst):
    m = onnx.load(src)
    onnx.save(m, dst, save_as_external_data=False)
    print(f"  {os.path.getsize(dst)} bytes -> {dst}")


def to_float_tflite(onnx_path, out_dir):
    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)
    cmd = [sys.executable, "-m", "onnx2tf", "-i", onnx_path, "-o", out_dir]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    fb = glob.glob(os.path.join(out_dir, "*float32*.tflite"))
    if not fb:
        print(r.stdout[-1500:]); print(r.stderr[-1500:])
        raise SystemExit("onnx2tf 失败，没有 float32 tflite")
    print(f"  {os.path.basename(fb[0])}  {os.path.getsize(fb[0])/1024:.1f} KB")
    return fb[0]


def make_calib(data_dir, calib_dir, n=150):
    os.makedirs(calib_dir, exist_ok=True)
    for f in os.listdir(calib_dir):
        os.remove(os.path.join(calib_dir, f))
    files = []
    for c in sorted(os.listdir(data_dir)):
        p = os.path.join(data_dir, c)
        if os.path.isdir(p):
            files += [os.path.join(p, f) for f in os.listdir(p) if f.lower().endswith((".jpg", ".jpeg", ".png"))]
    random.seed(0)
    random.shuffle(files)
    for i, f in enumerate(files[:n]):
        im = Image.open(f).convert("RGB").resize((IMG, IMG))
        a = np.asarray(im, dtype=np.float32) / 255.0
        a = (a - 0.5) / 0.5
        np.save(os.path.join(calib_dir, f"{i:03d}.npy"), a[None].astype(np.float32))
    print(f"  {min(n, len(files))} 张校准图 -> {calib_dir}")


def quantize(float_tflite, calib_dir, int8_path):
    import tensorflow as tf
    from ai_edge_quantizer import quantizer, recipe

    it = tf.lite.Interpreter(model_path=float_tflite)
    it.allocate_tensors()
    sigs = it.get_signature_list()
    key = list(sigs.keys())[0] if sigs else "serving_default"
    in_name = list(sigs[key]["inputs"])[0] if sigs else it.get_input_details()[0]["name"]

    calib = [np.load(os.path.join(calib_dir, f)) for f in sorted(os.listdir(calib_dir)) if f.endswith(".npy")]
    qt = quantizer.Quantizer(float_tflite)
    qt.load_quantization_recipe(recipe.static_wi8_ai8())
    res = qt.calibrate({key: [{in_name: c} for c in calib]})
    qt.quantize(calibration_result=res, serialize_to_path=int8_path)
    print(f"  {os.path.getsize(int8_path)/1024:.1f} KB -> {int8_path}")


def evaluate(int8_path, data_dir, n=200):
    import tensorflow as tf
    it = tf.lite.Interpreter(model_path=int8_path)
    it.allocate_tensors()
    inp = it.get_input_details()[0]
    out = it.get_output_details()[0]
    scale, zp = inp["quantization"]

    classes = sorted([d for d in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, d))])
    rng = np.random.default_rng(0)
    ok = tot = 0
    for ci, c in enumerate(classes):
        p = os.path.join(data_dir, c)
        files = rng.choice(sorted(os.listdir(p)), size=min(n // len(classes), len(os.listdir(p))), replace=False)
        for f in files:
            im = Image.open(os.path.join(p, f)).convert("RGB").resize((IMG, IMG))
            a = (np.asarray(im, dtype=np.float32) / 255.0 - 0.5) / 0.5
            q = np.clip(np.round(a[None] / scale + zp), -128, 127).astype(np.int8)
            it.set_tensor(inp["index"], q)
            it.invoke()
            o = it.get_tensor(out["index"])[0]
            if o.dtype == np.int8:
                o = o.astype(np.float32) * out["quantization"][0] + out["quantization"][1]
            ok += int(np.argmax(o) == ci)
            tot += 1
    print(f"  int8 精度 {100.0*ok/tot:.1f}%  ({tot} 张，类别 {classes})")


def run_vela(int8_path, out_dir):
    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)
    vela = os.path.join(VENV, "vela.exe")
    cmd = [vela, int8_path, "--accelerator-config", "ethos-u55-256",
           "--memory-mode", "Shared_Sram", "--optimise", "Performance",
           "--output-dir", out_dir]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    vf = glob.glob(os.path.join(out_dir, "*_vela.tflite"))
    for line in (r.stdout or "").splitlines():
        if any(k in line for k in ("Total SRAM", "Total Off-chip", "CPU operators", "NPU operators", "MACs")):
            print("  " + line.strip())
    if not vf:
        print(r.stderr[-1500:])
        raise SystemExit("vela 失败")
    print(f"  {os.path.getsize(vf[0])/1024:.1f} KB -> {vf[0]}")
    return vf[0]


def write_c(vtflite, out_dir):
    from tensorflow.lite.python import schema_py_generated as schema
    os.makedirs(out_dir, exist_ok=True)
    buf = open(vtflite, "rb").read()
    m = schema.Model.GetRootAsModel(buf, 0)
    sg = m.Subgraphs(0)

    t = {}
    for i in range(sg.TensorsLength()):
        tt = sg.Tensors(i)
        shape = [int(x) for x in tt.ShapeAsNumpy()] if tt.ShapeLength() else []
        q = tt.Quantization()
        t[tt.Name().decode()] = dict(
            shape=shape, buffer=tt.Buffer(),
            scale=float(q.Scale(0)) if q and q.ScaleLength() else 0.0,
            zp=int(q.ZeroPoint(0)) if q and q.ZeroPointLength() else 0)

    cms = bytes(m.Buffers(t["ethos_u_command_stream"]["buffer"]).DataAsNumpy())
    wgt = bytes(m.Buffers(t["read_only"]["buffer"]).DataAsNumpy())
    arena = t["scratch"]["shape"][0]
    inp, outp = t["input"], t["logits"]
    ib = int(np.prod(inp["shape"])); ob = int(np.prod(outp["shape"]))

    def carr(name, data):
        out = [f"__attribute__((aligned(16))) const uint8_t {name}[{len(data)}] = {{"]
        for i in range(0, len(data), 16):
            out.append("    " + ", ".join(f"0x{b:02x}" for b in data[i:i+16]) + ",")
        out.append("};")
        return "\n".join(out)

    open(os.path.join(out_dir, "pad_command_stream.c"), "w", encoding="utf-8").write(
        '#include "pad_command_stream.h"\n\n'
        f"const size_t pad_cms_size = {len(cms)};\n\n" + carr("pad_cms", cms) + "\n")
    open(os.path.join(out_dir, "pad_command_stream.h"), "w", encoding="utf-8").write(
        "#ifndef PAD_CMS_H\n#define PAD_CMS_H\n#include <stddef.h>\n#include <stdint.h>\n"
        "extern const size_t pad_cms_size;\nextern const uint8_t pad_cms[];\n#endif\n")
    open(os.path.join(out_dir, "pad_model_data.c"), "w", encoding="utf-8").write(
        '#include "pad_model_data.h"\n\n'
        f"const size_t pad_model_data_size = {len(wgt)};\n\n" + carr("pad_model_data", wgt) + "\n")
    open(os.path.join(out_dir, "pad_model_data.h"), "w", encoding="utf-8").write(
        "#ifndef PAD_MODEL_DATA_H\n#define PAD_MODEL_DATA_H\n#include <stddef.h>\n#include <stdint.h>\n"
        "extern const size_t pad_model_data_size;\nextern const uint8_t pad_model_data[];\n#endif\n")
    open(os.path.join(out_dir, "pad_tensors.h"), "w", encoding="utf-8").write(
        f"""#ifndef PAD_TENSORS_H
#define PAD_TENSORS_H
#include <stdint.h>
/* 由 pipeline_user.py 从 Vela 结果生成，勿手改 */
#define PAD_INPUT_W        {inp['shape'][2]}
#define PAD_INPUT_H        {inp['shape'][1]}
#define PAD_INPUT_C        {inp['shape'][3]}
#define PAD_INPUT_BYTES    {ib}
#define PAD_OUTPUT_CLASSES {outp['shape'][1]}
#define PAD_OUTPUT_BYTES   {ob}
#define PAD_ARENA_BYTES    {arena}
#define PAD_INPUT_SCALE    {inp['scale']:.9f}f
#define PAD_INPUT_ZP       ({inp['zp']})
#define PAD_OUTPUT_SCALE   {outp['scale']:.9f}f
#define PAD_OUTPUT_ZP      ({outp['zp']})
#endif
""")
    open(os.path.join(out_dir, "pad_invoke.c"), "w", encoding="utf-8").write(
        """#include <stdint.h>
#include <stddef.h>
#include <string.h>

#include "pad_invoke.h"
#include "pad_tensors.h"
#include "pad_command_stream.h"
#include "pad_model_data.h"

#include "common_data.h"
#include "ethosu_driver.h"

__attribute__((aligned(16))) uint8_t pad_arena[PAD_ARENA_BYTES];
__attribute__((aligned(16))) int8_t  pad_input[PAD_INPUT_BYTES];
__attribute__((aligned(16))) int8_t  pad_output[PAD_OUTPUT_BYTES];

/* region0=权重 region1=arena region2=fast scratch region3=输入 region4=输出 */
int pad_invoke(void)
{
    uint64_t base_addrs[5];
    size_t   base_addrs_size[5];

    base_addrs[0]      = (uint64_t)(uintptr_t)pad_model_data;
    base_addrs_size[0] = pad_model_data_size;
    base_addrs[1]      = (uint64_t)(uintptr_t)pad_arena;
    base_addrs_size[1] = PAD_ARENA_BYTES;
    base_addrs[2]      = (uint64_t)(uintptr_t)pad_arena;
    base_addrs_size[2] = PAD_ARENA_BYTES;
    base_addrs[3]      = (uint64_t)(uintptr_t)pad_input;
    base_addrs_size[3] = PAD_INPUT_BYTES;
    base_addrs[4]      = (uint64_t)(uintptr_t)pad_output;
    base_addrs_size[4] = PAD_OUTPUT_BYTES;

    memset(pad_output, 0, PAD_OUTPUT_BYTES);

    return ethosu_invoke_v3(&g_ethosu0, (uint8_t *)pad_cms, (int)pad_cms_size,
                            base_addrs, base_addrs_size, 5, NULL);
}
""")
    open(os.path.join(out_dir, "pad_invoke.h"), "w", encoding="utf-8").write(
        """#ifndef PAD_INVOKE_H
#define PAD_INVOKE_H
#include <stdint.h>
#include "pad_tensors.h"
extern uint8_t pad_arena[PAD_ARENA_BYTES];
extern int8_t  pad_input[PAD_INPUT_BYTES];
extern int8_t  pad_output[PAD_OUTPUT_BYTES];
int pad_invoke(void);
#endif
""")
    open(os.path.join(out_dir, "SConscript"), "w", encoding="ascii").write(
        "import os\nfrom building import *\n\nsrc = []\nobjs = []\ncwd  = GetCurrentDir()\n"
        "CPPPATH = [cwd]\n\nsrc = Glob('*.c')\n\n"
        "objs = DefineGroup('PadModel', src, depend = [], CPPPATH = CPPPATH)\n\nReturn('objs')\n")
    print(f"  命令流 {len(cms)} B / 权重 {len(wgt)} B / arena {arena} B")
    print(f"  in scale={inp['scale']:.9f} zp={inp['zp']} | out scale={outp['scale']:.9f} zp={outp['zp']}")
    print(f"  -> {out_dir}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--onnx", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--work", required=True)
    a = ap.parse_args()

    os.makedirs(a.work, exist_ok=True)

    step("1/6 ONNX 内联")
    single = os.path.join(a.work, "model_single.onnx")
    inline_onnx(a.onnx, single)

    step("2/6 ONNX -> float tflite")
    fb = to_float_tflite(single, os.path.join(a.work, "fb"))

    step("3/6 生成校准数据")
    calib = os.path.join(a.work, "calib")
    make_calib(a.data, calib)

    step("4/6 int8 量化")
    i8 = os.path.join(a.work, "model_int8.tflite")
    quantize(fb, calib, i8)

    step("5/6 精度复核")
    evaluate(i8, a.data, n=300)

    step("6/6 Vela 编译 + 生成 C 数组")
    vt = run_vela(i8, os.path.join(a.work, "vela"))
    write_c(vt, os.path.join(a.work, "c_arrays"))
    print("\n完成。")


if __name__ == "__main__":
    main()
