from src.utils import io


def suspect_1():
    a = 1


def evaluate_bd_pipeline(cd_gt_prev_path, cd_gt_cur_path, seg_path, img_path,  output_path):
    cd_gt_prev = io.import_shapefile(cd_gt_prev_path)
    cd_gt_cur = io.import_shapefile(cd_gt_cur_path)
    seg = io.import_shapefile(seg_path)
    img, crs, meta = io.import_tif(img_path)
