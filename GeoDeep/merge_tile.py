import os
import re
import numpy as np
from PIL import Image
from tqdm import tqdm


def rect_intersect(a, b):
    # a, b: (x, y, w, h)
    ax1, ay1, aw, ah = a
    bx1, by1, bw, bh = b
    ax2, ay2 = ax1 + aw, ay1 + ah
    bx2, by2 = bx1 + bw, by1 + bh

    x1 = max(ax1, bx1)
    y1 = max(ay1, by1)
    x2 = min(ax2, bx2)
    y2 = min(ay2, by2)

    if x2 > x1 and y2 > y1:
        return (x1, y1, x2 - x1, y2 - y1), (x1 - ax1, y1 - ay1, x2 - x1, y2 - y1)
    return None, None


def merge_png_tiles_with_overlap(input_dir, output_path, tile_size=512, tiles_overlap=0.1, output_format='png'):
    pattern = re.compile(r"junggu_2022_(\d+)_(\d+)\.png")
    tiles = []

    for fname in os.listdir(input_dir):
        match = pattern.match(fname)
        if match:
            x = int(match.group(1))
            y = int(match.group(2))
            tiles.append((x, y, fname))

    if not tiles:
        print("No valid tiles found.")
        return

    # 전체 이미지 크기 계산
    max_x = max(x for x, _, _ in tiles)
    max_y = max(y for _, y, _ in tiles)
    full_width = max_x + tile_size
    full_height = max_y + tile_size
    print(f"Final merged size: {full_width} x {full_height}")

    # 병합용 캔버스
    merged_mask = np.zeros((full_height, full_width), dtype=np.uint8)

    pad = int(tile_size * tiles_overlap) // 2

    for x, y, fname in tqdm(tiles, desc="Merging tiles"):
        img = Image.open(os.path.join(input_dir, fname)).convert('L')
        tile = np.array(img)

        pad_l = pad if x > 0 else 0
        pad_r = pad if x + tile_size < full_width else 0
        pad_t = pad if y > 0 else 0
        pad_b = pad if y + tile_size < full_height else 0

        crop_tile = tile[pad_t:tile_size - pad_b, pad_l:tile_size - pad_r]

        col_off = x + pad_l
        row_off = y + pad_t
        h, w = crop_tile.shape

        # 교차 영역 계산 및 최대값 병합
        tr, sr = rect_intersect((col_off, row_off, w, h), (0, 0, full_width, full_height))
        if tr and sr:
            target_region = merged_mask[tr[1]:tr[1] + tr[3], tr[0]:tr[0] + tr[2]]
            source_region = crop_tile[sr[1]:sr[1] + sr[3], sr[0]:sr[0] + sr[2]]
            merged_mask[tr[1]:tr[1] + tr[3], tr[0]:tr[0] + tr[2]] = np.maximum(target_region, source_region)
        else:
            print(f"Tile {fname} is out of bounds and will be skipped.")

    # 결과 저장
    out_img = Image.fromarray(merged_mask)
    if output_format == 'png':
        out_img.save(output_path)
    elif output_format == 'tif':
        out_img.save(output_path, format='TIFF')

    print(f"Saved merged image to {output_path}")


merge_png_tiles_with_overlap(
    input_dir=r'D:\an_result_junggu',
    output_path=r'D:\merged_result\merged_junggu_mask.png',
    tile_size=512,
    tiles_overlap=0.01,  # 오버랩 비율 (예: 10%)
    output_format='png'
)
