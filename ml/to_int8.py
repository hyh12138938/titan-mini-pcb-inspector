# -*- coding: utf-8 -*-
"""
float32 tflite -> int8 tflite（ai-edge-quantizer, static_wi8_ai8）
并用真实数据评估量化前后精度。
"""
import os
import numpy as np
import tensorflow as tf
from ai_edge_quantizer import quantizer, recipe

FLOAT_TFLITE = r"D:\RTT\ml\out_pcb\int8\pad_model_single_float32.tflite"
INT8_TFLITE = r"D:\RTT\ml\out_pcb\pad_model_int8.tflite"
CALIB_DIR = r"D:\RTT\ml\calib"
DATA_DIR = r"D:\RTT\ml\data\pcb_bin"


def load_img(path):
    from PIL import Image
    im = Image.open(path).convert("RGB").resize((96, 96))
    a = np.asarray(im, dtype=np.float32) / 255.0
    a = (a - 0.5) / 0.5
    return a[None]                                  # 1,96,96,3 (NHWC)


def sig_info(path):
    it = tf.lite.Interpreter(model_path=path)
    it.allocate_tensors()
    sigs = it.get_signature_list()
    return it, sigs


def run_tflite(path, samples):
    it = tf.lite.Interpreter(model_path=path)
    it.allocate_tensors()
    inp = it.get_input_details()[0]
    out = it.get_output_details()[0]
    is_int8 = inp["dtype"] == np.int8
    scale, zp = inp["quantization"]
    preds = []
    for s in samples:
        if is_int8:
            q = np.clip(np.round(s / scale + zp), -128, 127).astype(np.int8) if scale else s.astype(np.int8)
        else:
            q = s.astype(np.float32)
        it.set_tensor(inp["index"], q)
        it.invoke()
        o = it.get_tensor(out["index"])[0]
        if o.dtype == np.int8:
            o = o.astype(np.float32) * out["quantization"][0] + out["quantization"][1]
        preds.append(int(np.argmax(o)))
    return preds


def main():
    # ---- 1) 量化 ----
    calib = [np.load(os.path.join(CALIB_DIR, f)) for f in sorted(os.listdir(CALIB_DIR)) if f.endswith(".npy")]
    print(f"[校准] {len(calib)} 张")

    it, sigs = sig_info(FLOAT_TFLITE)
    print(f"[签名] {sigs}")
    if sigs:
        key = list(sigs.keys())[0]
        in_name = list(sigs[key]["inputs"])[0]
    else:
        key = "serving_default"
        in_name = it.get_input_details()[0]["name"]
    print(f"[输入] signature={key} name={in_name}")

    qt = quantizer.Quantizer(FLOAT_TFLITE)
    qt.load_quantization_recipe(recipe.static_wi8_ai8())
    cal_res = qt.calibrate({key: [{in_name: c} for c in calib]})
    qt.quantize(calibration_result=cal_res, serialize_to_path=INT8_TFLITE)
    print(f"[量化] -> {INT8_TFLITE}  {os.path.getsize(INT8_TFLITE)/1024:.1f} KB")

    # ---- 2) 精度对比 ----
    samples, labels = [], []
    rng = np.random.default_rng(0)
    for ci, cname in enumerate(["defect", "good"]):
        files = sorted(os.listdir(os.path.join(DATA_DIR, cname)))
        pick = rng.choice(len(files), size=min(150, len(files)), replace=False)
        for i in pick:
            samples.append(load_img(os.path.join(DATA_DIR, cname, files[i])))
            labels.append(ci)

    pf = run_tflite(FLOAT_TFLITE, samples)
    pq = run_tflite(INT8_TFLITE, samples)
    acc_f = 100.0 * sum(a == b for a, b in zip(pf, labels)) / len(labels)
    acc_q = 100.0 * sum(a == b for a, b in zip(pq, labels)) / len(labels)
    agree = 100.0 * sum(a == b for a, b in zip(pf, pq)) / len(labels)
    print(f"[精度] float32 = {acc_f:.1f}%   int8 = {acc_q:.1f}%   两者一致率 = {agree:.1f}%   (样本 {len(labels)})")


if __name__ == "__main__":
    main()
