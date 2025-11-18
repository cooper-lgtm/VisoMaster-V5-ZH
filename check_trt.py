import onnxruntime as ort

print("=== 当前可用 Providers ===")
print(ort.get_available_providers())

sess_options = ort.SessionOptions()

model_path = r"D:\demo0\VisoMaster-ZH\model_assets\inswapper_128.fp16.onnx"

# 指定优先顺序：TensorRT > CUDA > CPU
sess = ort.InferenceSession(
    model_path,
    sess_options,
    providers=[
        ("TensorrtExecutionProvider", {}),
        ("CUDAExecutionProvider", {}),
        ("CPUExecutionProvider", {})
    ]
)

print("=== 当前实际使用 Providers ===")
print(sess.get_providers())
