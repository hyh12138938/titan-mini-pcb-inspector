import tensorflow as tf, numpy as np
p = r"D:\RTT\ml\out_pcb\vela\pad_model_int8_vela.tflite"
it = tf.lite.Interpreter(model_path=p)
it.allocate_tensors()
print("=== input ===")
for d in it.get_input_details():
    print(" name", d["name"], "shape", d["shape"], "dtype", d["dtype"], "quant", d["quantization"])
print("=== output ===")
for d in it.get_output_details():
    print(" name", d["name"], "shape", d["shape"], "dtype", d["dtype"], "quant", d["quantization"])
print("=== ops ===")
for o in it._get_ops_details():
    print(" ", o["op_name"], "inputs", o["inputs"], "outputs", o["outputs"])
print("=== tensor count ===", len(it.get_tensor_details()))
