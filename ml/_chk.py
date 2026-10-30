import onnx, onnxruntime as ort, numpy as np
m = onnx.load(r"D:\RTT\ml\_smoke_out\pad_model.onnx")
onnx.checker.check_model(m)
s = ort.InferenceSession(r"D:\RTT\ml\_smoke_out\pad_model.onnx")
x = np.random.randn(1,3,96,96).astype(np.float32)
y = s.run(None, {"input": x})[0]
print("ONNX OK  input", x.shape, "-> output", y.shape, "probs", y.round(3))
