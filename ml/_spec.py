import tensorflow as tf
it = tf.lite.Interpreter(model_path=r"D:\RTT\ml\out_pcb\int8\pad_model_single_float32.tflite")
it.allocate_tensors()
for d in it.get_input_details():  print("IN ", d["name"], d["shape"], d["dtype"])
for d in it.get_output_details(): print("OUT", d["name"], d["shape"], d["dtype"])
