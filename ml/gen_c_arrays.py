# -*- coding: utf-8 -*-
"""
把 Vela 编译后的 tflite 拆成固件要的 C 数组：
    pad_command_stream.c/h   命令流（COP1）
    pad_model_data.c/h       权重（read_only）
    pad_tensors.c/h          张量参数（地址/大小/量化 scale+zp）
    pad_invoke.c/h           Ethos-U 调用封装

依据：_vela.tflite 的 subgraph 张量
    t0 ethos_u_command_stream  buffer=1
    t1 read_only               buffer=2
    t2 scratch                 (arena)
    t3 input    int8 [1,96,96,3]
    t4 logits   int8 [1,2]
"""
import os

import numpy as np
from tensorflow.lite.python import schema_py_generated as schema

TFLITE = r"D:\RTT\ml\out_pcb\vela\pad_model_int8_vela.tflite"
OUT = r"D:\RTT\ml\out_pcb\c_arrays"

TYPES = {0: "float32", 1: "float16", 2: "int32", 3: "uint8", 4: "int64", 9: "int8"}


def arr_to_c(name, data, per_line=16):
    lines = [f"__attribute__((aligned(16))) const uint8_t {name}[{len(data)}] = {{"]
    for i in range(0, len(data), per_line):
        chunk = data[i:i + per_line]
        lines.append("    " + ", ".join(f"0x{b:02x}" for b in chunk) + ",")
    lines.append("};")
    return "\n".join(lines)


def main():
    os.makedirs(OUT, exist_ok=True)
    buf = open(TFLITE, "rb").read()
    m = schema.Model.GetRootAsModel(buf, 0)
    sg = m.Subgraphs(0)

    tensors = {}
    for i in range(sg.TensorsLength()):
        t = sg.Tensors(i)
        shape = [int(x) for x in t.ShapeAsNumpy()] if t.ShapeLength() else []
        q = t.Quantization()
        scale = float(q.Scale(0)) if q and q.ScaleLength() else 0.0
        zp = int(q.ZeroPoint(0)) if q and q.ZeroPointLength() else 0
        name = t.Name().decode() if t.Name() else f"t{i}"
        tensors[name] = dict(idx=i, shape=shape, type=TYPES.get(t.Type(), str(t.Type())),
                             buffer=t.Buffer(), scale=scale, zp=zp)

    # ---- 命令流 ----
    cms = bytes(m.Buffers(tensors["ethos_u_command_stream"]["buffer"]).DataAsNumpy())
    assert cms[:4] == b"COP1", cms[:4]
    # ---- 权重 ----
    mdata = bytes(m.Buffers(tensors["read_only"]["buffer"]).DataAsNumpy())
    # ---- arena ----
    arena = tensors["scratch"]["shape"][0]
    inp, outp = tensors["input"], tensors["logits"]
    in_bytes = int(np.prod(inp["shape"]))
    out_bytes = int(np.prod(outp["shape"]))

    with open(os.path.join(OUT, "pad_command_stream.c"), "w", encoding="utf-8") as f:
        f.write('#include "pad_command_stream.h"\n\n')
        f.write(f"const size_t pad_cms_size = {len(cms)};\n\n")
        f.write(arr_to_c("pad_cms", cms))
        f.write("\n")
    with open(os.path.join(OUT, "pad_command_stream.h"), "w", encoding="utf-8") as f:
        f.write('#ifndef PAD_CMS_H\n#define PAD_CMS_H\n#include <stddef.h>\n#include <stdint.h>\n'
                'extern const size_t pad_cms_size;\nextern const uint8_t pad_cms[];\n#endif\n')

    with open(os.path.join(OUT, "pad_model_data.c"), "w", encoding="utf-8") as f:
        f.write('#include "pad_model_data.h"\n\n')
        f.write(f"const size_t pad_model_data_size = {len(mdata)};\n\n")
        f.write(arr_to_c("pad_model_data", mdata))
        f.write("\n")
    with open(os.path.join(OUT, "pad_model_data.h"), "w", encoding="utf-8") as f:
        f.write('#ifndef PAD_MODEL_DATA_H\n#define PAD_MODEL_DATA_H\n#include <stddef.h>\n#include <stdint.h>\n'
                'extern const size_t pad_model_data_size;\nextern const uint8_t pad_model_data[];\n#endif\n')

    with open(os.path.join(OUT, "pad_tensors.h"), "w", encoding="utf-8") as f:
        f.write(f"""#ifndef PAD_TENSORS_H
#define PAD_TENSORS_H
#include <stdint.h>
#include <stddef.h>

/* 由 Vela 编译结果生成，勿手改 */
#define PAD_INPUT_W        {inp['shape'][2]}
#define PAD_INPUT_H        {inp['shape'][1]}
#define PAD_INPUT_C        {inp['shape'][3]}
#define PAD_INPUT_BYTES    {in_bytes}
#define PAD_OUTPUT_CLASSES {outp['shape'][1]}
#define PAD_OUTPUT_BYTES   {out_bytes}
#define PAD_ARENA_BYTES    {arena}

#define PAD_INPUT_SCALE    {inp['scale']:.9f}f
#define PAD_INPUT_ZP       ({inp['zp']})
#define PAD_OUTPUT_SCALE   {outp['scale']:.9f}f
#define PAD_OUTPUT_ZP      ({outp['zp']})

/* 类别顺序：0=defect 1=good（训练时 ImageFolder 字母序） */
#define PAD_CLASS_DEFECT   0
#define PAD_CLASS_GOOD     1

#endif
""")

    with open(os.path.join(OUT, "pad_invoke.h"), "w", encoding="utf-8") as f:
        f.write("""#ifndef PAD_INVOKE_H
#define PAD_INVOKE_H
#include <stdint.h>
#include "pad_tensors.h"

extern uint8_t  pad_arena[PAD_ARENA_BYTES];
extern int8_t   pad_input[PAD_INPUT_BYTES];
extern int8_t   pad_output[PAD_OUTPUT_BYTES];

int pad_invoke(void);
#endif
""")

    with open(os.path.join(OUT, "pad_invoke.c"), "w", encoding="utf-8") as f:
        f.write(f"""#include <stdint.h>
#include <stddef.h>
#include <string.h>

#include "pad_invoke.h"
#include "pad_tensors.h"
#include "pad_command_stream.h"
#include "pad_model_data.h"

#include "ethosu_driver.h"

#if defined(__ARMCC_VERSION)
#define ALIGN16 __attribute__((aligned(16)))
#else
#define ALIGN16 __attribute__((aligned(16)))
#endif

ALIGN16 uint8_t pad_arena[PAD_ARENA_BYTES];
ALIGN16 int8_t  pad_input[PAD_INPUT_BYTES];
ALIGN16 int8_t  pad_output[PAD_OUTPUT_BYTES];

extern void *g_ethosu0;

int pad_invoke(void)
{{
    uint64_t base_addrs[5];
    size_t   base_addrs_size[5];

    /* region0: 权重  region1: arena  region2: fast scratch  region3: 输入  region4: 输出 */
    base_addrs[0] = (uint64_t)(uintptr_t)pad_model_data;
    base_addrs_size[0] = pad_model_data_size;

    base_addrs[1] = (uint64_t)(uintptr_t)pad_arena;
    base_addrs_size[1] = PAD_ARENA_BYTES;

    base_addrs[2] = (uint64_t)(uintptr_t)pad_arena;
    base_addrs_size[2] = PAD_ARENA_BYTES;

    base_addrs[3] = (uint64_t)(uintptr_t)pad_input;
    base_addrs_size[3] = PAD_INPUT_BYTES;

    base_addrs[4] = (uint64_t)(uintptr_t)pad_output;
    base_addrs_size[4] = PAD_OUTPUT_BYTES;

    memset(pad_output, 0, PAD_OUTPUT_BYTES);

    return ethosu_invoke_v3(g_ethosu0, (uint8_t *)pad_cms, (int)pad_cms_size,
                            base_addrs, base_addrs_size, 5, NULL);
}}
""")

    print(f"[cms]  {len(cms)} B")
    print(f"[wgt]  {len(mdata)} B")
    print(f"[arena]{arena} B   input {in_bytes} B (shape {inp['shape']})   output {out_bytes} B")
    print(f"[quant] in scale={inp['scale']:.9f} zp={inp['zp']} | out scale={outp['scale']:.9f} zp={outp['zp']}")
    print(f"[out]  {OUT}")


if __name__ == "__main__":
    main()
