import onnxruntime as ort
import numpy as np

session = ort.InferenceSession(r"D:\Work\01. Lab_project\DT\GeoDeep\model\building_2005_deepness.onnx")
input_name = session.get_inputs()[0].name
output_name = session.get_outputs()[0].name

# Dummy 입력 만들기 (예시)
dummy = np.random.rand(1, 3, 512, 512).astype(np.float32)
output = session.run(None, {input_name: dummy})

print("Output shape:", output[0].shape)
print("Unique values:", np.unique(output[0]))
