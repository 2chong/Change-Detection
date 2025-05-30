import os
import cv2
import numpy as np
import rasterio


def morphology_to_mask(original_tif_path, out_tif_path,
                              open_k=21, close_k=3, iterations=2):
    # with rasterio.open(original_tif_path) as src:
    #     mask = src.read(1)
    #     meta = src.meta.copy()

    open_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (open_k, open_k))
    close_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (close_k, close_k))

    opened = cv2.morphologyEx(mask, cv2.MORPH_OPEN, open_kernel, iterations=iterations)
    morphed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, close_kernel, iterations=iterations)

    # meta.update({"count": 1, "dtype": rasterio.uint8})
    # with rasterio.open(out_tif_path, 'w', **meta) as dst:
    #     dst.write(morphed.astype(np.uint8), 1)

    return morphed


# 경로 고정
# original_tif_path = r"D:\Work\01. Lab_project\DT\GeoDeep\output\building_result_jungrang.tif"
# output_dir = r"D:\Work\01. Lab_project\DT\GeoDeep\output"
#
# # 열림 커널만 변화시키면서 저장 파일명 다르게 생성
# for k in [21]:
#     out_tif_path = os.path.join(output_dir, f"building_result_morph_k{k}{k}.tif")
#     apply_morphology_to_mask(
#         original_tif_path,
#         out_tif_path=out_tif_path,
#         open_k=k,
#         close_k=3  # 항상 고정
#     )
#     print(f"✅ 저장 완료: {out_tif_path}")
