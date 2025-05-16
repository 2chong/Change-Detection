from src.utils import io
from src.core.polygon_matching import polygon_matching_utils, polygon_matching_algorithm


def assign_class(poly, threshold):
    poly = polygon_matching_utils.assign_cd_class(poly, threshold, "cd")
    poly = polygon_matching_utils.assign_class_10(poly, "cd")

    return poly


def cd_pipeline(dmap_path, seg_path, dmap_output_path, seg_output_path, cut_threshold, cd_threshold):
    _, dmap, seg = (polygon_matching_algorithm.algorithm_pipeline
                          (dmap_path, seg_path, seg_path, cut_threshold))
    dmap = assign_class(dmap, cd_threshold)
    seg = assign_class(seg, cd_threshold)
    dmap = polygon_matching_utils.bd_result_attach(dmap, seg)
    dmap = dmap.rename(columns={"Relation": "rel_cd"})
    seg = seg.rename(columns={"Relation": "rel_cd"})
    io.export_file(dmap, dmap_output_path, 'dmap')
    io.export_file(seg, seg_output_path, 'seg')