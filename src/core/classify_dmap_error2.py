from src.utils import io


def classify_dmap_error_pipeline(prev_dmap, cur_dmap, seg, image, output_path):
    prev_dmap = io.import_shapefile(prev_dmap, crs=5179)