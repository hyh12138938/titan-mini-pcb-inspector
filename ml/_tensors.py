import numpy as np
from tensorflow.lite.python import schema_py_generated as schema
buf = open(r"D:\RTT\ml\out_pcb\vela\pad_model_int8_vela.tflite","rb").read()
m = schema.Model.GetRootAsModel(buf, 0)
sg = m.Subgraphs(0)
print("inputs:", list(sg.InputsAsNumpy()), " outputs:", list(sg.OutputsAsNumpy()))
for i in range(sg.TensorsLength()):
    t = sg.Tensors(i)
    shape = list(t.ShapeAsNumpy()) if t.ShapeLength() else []
    q = t.Quantization()
    sc = list(q.ScaleAsNumpy()) if q and q.ScaleLength() else []
    zp = list(q.ZeroPointAsNumpy()) if q and q.ZeroPointLength() else []
    nm = t.Name().decode() if t.Name() else ""
    print(f"  t[{i}] name={nm!r} type={t.Type()} shape={shape} buffer={t.Buffer()} scale={sc} zp={zp}")
