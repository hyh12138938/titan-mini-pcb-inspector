import onnx, os
src = r"D:\RTT\ml\out_pcb\pad_model.onnx"
m = onnx.load(src)                      # 会自动加载同目录 .onnx.data
onnx.save(m, r"D:\RTT\ml\out_pcb\pad_model_single.onnx", save_as_external_data=False)
print("inlined ->", os.path.getsize(r"D:\RTT\ml\out_pcb\pad_model_single.onnx"), "bytes")
print("inputs ", [(i.name, [d.dim_value for d in i.type.tensor_type.shape.dim]) for i in m.graph.input])
print("outputs", [(o.name, [d.dim_value for d in o.type.tensor_type.shape.dim]) for o in m.graph.output])
print("opset", m.opset_import[0].version, "| nodes", len(m.graph.node))
