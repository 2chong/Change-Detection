import rasterio
from rasterio.features import shapes
import geopandas as gpd
from shapely.geometry import shape


def vectorize_mask_array(mask_array, transform, crs, min_area=0.0):
    geoms = []
    values = []
    for geom, value in shapes(mask_array, mask=(mask_array != 0), transform=transform):
        s = shape(geom)
        if value != 0 and (min_area == 0.0 or s.area >= min_area):
            geoms.append(s)
            values.append(value)
    return gpd.GeoDataFrame({"value": values, "geometry": geoms}, crs=crs)


original_tif_path = r'D:\Work\01. Lab_project\DT\GeoDeep\output\building_result_morph_k2121.tif'
with rasterio.open(original_tif_path) as src:
    mask = src.read(1)
    meta = src.meta.copy()


vectorize_mask_array(mask_array, transform, crs, min_area=0.0)

