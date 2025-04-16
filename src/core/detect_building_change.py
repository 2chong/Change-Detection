import argparse
from src.utils import utils
from src.utils import analysis_utils
from src.utils import polygon_matching_utils
from src.utils import polygon_matching_algorithm
from src.common.path_loader import load_building_paths


def assign_class(poly, threshold):
    poly = polygon_matching_utils.assign_cd_class(poly, threshold, "cd")
    poly = polygon_matching_utils.assign_class_10(poly, "cd")

    return poly


def cd_pipeline(dmap_path, seg_path, dmap_output_path, seg_output_path, anl_output_path, cut_threshold, cd_threshold):
    _, dmap, seg = (polygon_matching_algorithm.algorithm_pipeline
                          (dmap_path, seg_path, anl_output_path, cut_threshold))
    dmap = assign_class(dmap, cd_threshold)
    seg = assign_class(seg, cd_threshold)
    report = analysis_utils.analysis_pipeline(dmap, seg)
    utils.export_file(dmap, dmap_output_path, 'dmap')
    utils.export_file(seg, seg_output_path, 'seg')
    utils.export_file(report, anl_output_path, 'analysis_result')


def main():
    parser = argparse.ArgumentParser(description="건물 변화 탐지 프로세스")
    parser.add_argument("--region", type=str, required=True, help="지역 이름 (예: gangseo)")
    parser.add_argument("--year", type=str, default=2022, help="기준 연도")
    parser.add_argument("--previous_year", type=str, default=2020, help="이전 연도")
    parser.add_argument("--cut_threshold", type=float, default=0.05, help="그래프 컷 임계값")
    parser.add_argument("--cd_threshold", type=float, default=0.7, help="변화 판별 임계값")

    args = parser.parse_args()

    paths = load_building_paths(args.region, args.year, args.previous_year)

    cd_pipeline(
        dmap_path=paths["previous_building_digital_map"],
        seg_path=paths["building_inference"],
        dmap_output_path=paths["building_change_detection_result_prev"],
        seg_output_path=paths["building_change_detection_result_cur"],
        anl_output_path=paths["building_change_detection_result_anl"],
        cut_threshold=args.cut_threshold,
        cd_threshold=args.cd_threshold
    )


if __name__ == "__main__":
    main()
    print("end")
