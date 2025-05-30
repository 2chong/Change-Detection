import rasterio
import rasterio.features
import json
import numpy as np
from .detection import preprocess
import logging
import cv2
import geopandas as gpd
from shapely.geometry import shape
from rasterio.features import shapes
from rasterio.warp import transform
from shapely.geometry import Polygon
from shapely.geometry import MultiPolygon
from shapely.ops import unary_union
logger = logging.getLogger("geodeep")

def postprocess(model_output, config):
    model_output[model_output<config['seg_thresh']] = 0
    mask = np.argmax(model_output, axis=1).astype(np.float32)
    return mask

def execute_segmentation(images, session, config):
    images = preprocess(images)
    outs = session.run(None, {config['input_name']: images})
    out = outs[0]
    building_conf = out[0, 0, :, :]
    # 🔢 unique 값 추출 및 출력
    return building_conf


def rect_intersect(rect1, rect2):
    """
    Given two rectangles, compute the intersection rectangle and return 
    its coordinates in the coordinate system of both rectangles.
    
    Each rectangle is represented as (x, y, width, height).

    Returns:
    - (r1_x, r1_y, iw, ih): Intersection in rect1's local coordinates
    - (r2_x, r2_y, iw, ih): Intersection in rect2's local coordinates
    """
    x1, y1, w1, h1 = rect1
    x2, y2, w2, h2 = rect2

    ix = max(x1, x2)  # Left boundary
    iy = max(y1, y2)  # Top boundary
    ix2 = min(x1 + w1, x2 + w2)  # Right boundary
    iy2 = min(y1 + h1, y2 + h2)  # Bottom boundary

    # Compute intersection
    iw = max(0, ix2 - ix)
    ih = max(0, iy2 - iy)

    # If no intersection
    if iw == 0 or ih == 0:
        return None, None

    # Compute local coordinates
    r1_x = ix - x1
    r1_y = iy - y1
    r2_x = ix - x2
    r2_y = iy - y2

    return (r1_x, r1_y, iw, ih), (r2_x, r2_y, iw, ih)


def merge_mask(tile_mask, mask, window, width, height, tiles_overlap=0, scale_factor = 1.0):
    w = window
    row_off = int(w.row_off // scale_factor) #int(np.round(w.row_off / scale_factor))
    col_off = int(w.col_off // scale_factor) #int(np.round(w.col_off / scale_factor))
    tile_w, tile_h = tile_mask.shape

    pad_x = int(tiles_overlap * tile_w) // 2
    pad_y = int(tiles_overlap * tile_h) // 2

    pad_l = 0
    pad_r = 0
    pad_t = 0
    pad_b = 0

    if w.col_off > 0:
        pad_l = pad_x
    if w.col_off + w.width < width:
        pad_r = pad_x
    if w.row_off > 0:
        pad_t = pad_y
    if w.row_off + w.height < height:
        pad_b = pad_y
    
    row_off += pad_t
    col_off += pad_l
    tile_w -= pad_l + pad_r
    tile_h -= pad_t + pad_b

    tile_mask = tile_mask[np.newaxis, :, :]  # shape: (1, 512, 512)
    tile_mask = tile_mask[:,pad_t:pad_t+tile_h,pad_l:pad_l+tile_w]
    tr, sr = rect_intersect((col_off, row_off, tile_w, tile_h), (0, 0, mask.shape[1], mask.shape[0]))
    if tr is not None and sr is not None:
        mask[sr[1]:sr[1]+sr[3], sr[0]:sr[0]+sr[2]] = tile_mask[:, tr[1]:tr[1]+tr[3], tr[0]:tr[0]+tr[2]]
        # mask[sr[1]:sr[1]+sr[3], sr[0]:sr[0]+sr[2]] *= (idx + 1)
    else:
        logger.warning(f"Cannot merge segmentation tile {w}")
        

def mask_to_geojson(raster, mask, config, scale_factor=1.0):
    transform = list(raster.transform * rasterio.Affine.scale(scale_factor, scale_factor))

    class_mask = np.isin(mask, config['classes']) if len(config['classes']) > 0 else None
    shapes = list(rasterio.features.shapes(source=mask, mask=class_mask, transform=transform))
    if not len(shapes):
        return json.dumps({
            "type": "FeatureCollection",
            "features": []
        }, indent=2)

    coords = []
    coordsIdx = []

    def traverse(item, action):
        if isinstance(item, tuple) or isinstance(item, int):
            return action(item)
        elif isinstance(item, list):
            return [traverse(it, action) for it in item]
        else:
            raise Exception(f"Invalid item in traverse: {item}")

    def gather_coords(item):
        idx = len(coords)
        coords.append(item)
        return idx

    for geom, _ in shapes:
        coordsIdx.append(traverse(geom.get('coordinates'), gather_coords))

    xs, ys = zip(*coords)
    tx, ty = rasterio.warp.transform(raster.crs, "EPSG:4326", xs, ys)
    feats = []

    for i, (_, cid) in enumerate(shapes):
        cls = config['class_names'].get(str(int(cid)), 'unknown')
        coordinates = traverse(coordsIdx[i], lambda idx: (tx[idx], ty[idx]))

        feats.append({
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": coordinates
                },
                "properties": {
                    "class": cls
                }
            })

    return json.dumps({
        "type": "FeatureCollection",
        "features": feats
    }, indent=2)


def save_mask_to_raster(geotiff, mask, outfile):
    with rasterio.open(geotiff, "r") as src:
        p = src.profile
        p['width'] = mask.shape[1]
        p['height'] = mask.shape[0]
        p['count'] = 1
        p['dtype'] = 'uint8'
        p['transform'] *= rasterio.Affine.scale(src.profile['width'] / p['width'], src.profile['height'] / p['height'])

        with rasterio.open(outfile, "w", **p) as dst:
            scaled_mask = (mask * 255).astype(np.uint8)
            # 이거 return 하게 만들어서, 래스터
            dst.write(scaled_mask, 1)


def filter_small_segments(mask, config):
    # Better matches the logic from Deepness
    # where the parameter refers to the dilation/erode size
    # (sieve counts the number of pixels)
    ss = (config['seg_small_segment'] * 2) ** 2
    if ss > 0:
        # Remove small polygons
        rasterio.features.sieve(mask, ss, out=mask)
    return mask


def morphology_to_mask(mask, open_k=21, close_k=3, iterations=2):
    open_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (open_k, open_k))
    close_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (close_k, close_k))

    opened = cv2.morphologyEx(mask, cv2.MORPH_OPEN, open_kernel, iterations=iterations)
    morphed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, close_kernel, iterations=iterations)
    return morphed


def mask_to_gdf(raster, mask, config, scale_factor=1.0):

    affine = raster.transform * rasterio.Affine.scale(scale_factor, scale_factor)

    values = np.unique(mask)
    values = values[values != 0]  # 0 제외

    if len(values) == 0:
        print("❗ 추론된 건물 없음")
        return gpd.GeoDataFrame(columns=['class', 'geometry'], crs="EPSG:5186")
    elif len(values) > 1:
        print(f"⚠️ 클래스가 여러 개 있습니다: {values} → 첫 번째 값만 사용합니다.")

    target_value = values[0]

    geometries = []
    for geom, val in shapes(source=mask, mask=(mask == target_value), transform=affine):
        s = shape(geom)
        if s.is_valid and not s.is_empty:
            xs, ys = zip(*s.exterior.coords[:])
            x_new, y_new = transform(raster.crs, "EPSG:5186", xs, ys)
            projected_geom = shape({
                "type": "Polygon",
                "coordinates": [list(zip(x_new, y_new))]
            })
            geometries.append(projected_geom)

    return gpd.GeoDataFrame({'class': ['building'] * len(geometries), 'geometry': geometries}, crs="EPSG:5186")


def simplify_polygon(polygon, tolerance=1.0, preserve_topology=True):

    return polygon.simplify(tolerance, preserve_topology)
