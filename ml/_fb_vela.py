import flatbuffers, numpy as np, os
from tensorflow.lite.python import schema_py_generated as schema
buf = open(r"D:\RTT\ml\out_pcb\vela\pad_model_int8_vela.tflite","rb").read()
m = schema.Model.GetRootAsModel(buf, 0)
sg = m.Subgraphs(0)
print("buffers:", m.BuffersLength(), " tensors:", sg.TensorsLength(), " operators:", sg.OperatorsLength())
op = sg.Operators(0)
oc = op.OpcodeIndex()
ocd = m.OperatorCodes(oc)
print("opcode builtin:", ocd.BuiltinCode(), " custom:", ocd.CustomCode())
print("custom_options len:", op.CustomOptionsLength())
co = bytes(op.CustomOptionsAsNumpy()) if op.CustomOptionsLength() else b""
print("custom_options hex:", co.hex())
for i in range(m.BuffersLength()):
    b = m.Buffers(i)
    if b.DataLength():
        d = b.DataAsNumpy()
        print(f"  buffer[{i}] size={b.DataLength()} head={bytes(d[:8]).hex()}")
