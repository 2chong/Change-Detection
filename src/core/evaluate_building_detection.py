import argparse
import pandas as pd
from src.utils import io
from src.utils import analysis_utils
from src.utils import polygon_matching_utils
from src.utils import polygon_matching_algorithm
from src.common.path_loader import load_building_paths


def assign_class(dmap, seg, bd_threshold):
    dmap = polygon_matching_utils.assign_bd_class_gt(dmap, bd_threshold)
    seg = polygon_matching_utils.assign_bd_class_seg(seg, bd_threshold)
    dmap = polygon_matching_utils.assign_class_bd_10(dmap, prefix="bd")
    seg = polygon_matching_utils.assign_class_bd_10(seg, prefix="bd")
    return dmap, seg


def evaluate_bd(dmap, seg, bd_threshold):
    # dmap 기반 계산 (Recall 기준)
    dmap_tp = (dmap['bd_class'] == 'TP').sum()
    dmap_fn = (dmap['bd_class'] == 'FN').sum()
    gt_total = dmap_tp + dmap_fn
    recall = dmap_tp / gt_total if gt_total > 0 else 0

    # seg 기반 계산 (Precision 기준)
    seg_tp = (seg['bd_class'] == 'TP').sum()
    seg_fp = (seg['bd_class'] == 'FP').sum()
    pred_total = seg_tp + seg_fp
    precision = seg_tp / pred_total if pred_total > 0 else 0

    # F1-score 계산
    if precision + recall > 0:
        f1_score = 2 * (precision * recall) / (precision + recall)
    else:
        f1_score = 0

    # 결과 DataFrame
    result = pd.DataFrame([{
        "GT 수": gt_total,
        "Pred 수": pred_total,
        "TP": dmap_tp,
        "FN": dmap_fn,
        "FP": seg_fp,
        "재현율": round(recall, 3),
        "정밀도": round(precision, 3),
        "F1-score": round(f1_score, 3),
        "Threshold": bd_threshold
    }])

    return result


def evaluate_bd_pipeline(dmap_path, seg_path, dmap_output_path, seg_output_path, anl_output_path, cut_threshold, bd_threshold):
    _, dmap, seg = (polygon_matching_algorithm.algorithm_pipeline
                             (dmap_path, seg_path, anl_output_path, cut_threshold))
    dmap, seg = assign_class(dmap, seg, bd_threshold)
    result = evaluate_bd(dmap, seg, bd_threshold)
    anl_result = analysis_utils.report_bd(dmap, seg)
    utils.export_file(dmap, dmap_output_path, 'dmap')
    utils.export_file(seg, seg_output_path, 'seg')
    utils.export_file(anl_result, anl_output_path, 'bd_anl_result')
    utils.export_file(result, anl_output_path, 'bd_evaluate_result')


def main():
    parser = argparse.ArgumentParser(description="건물 변화 탐지 프로세스")
    parser.add_argument("--region", type=str, required=True, help="지역 이름 (예: gangseo)")
    parser.add_argument("--year", type=str, default=2022, help="기준 연도")
    parser.add_argument("--previous_year", type=str, default=2020, help="이전 연도")
    parser.add_argument("--cut_threshold", type=float, default=0.05, help="그래프 컷 임계값")
    parser.add_argument("--bd_threshold", type=float, default=0.6, help="탐지 판별 임계값")

    args = parser.parse_args()

    paths = load_building_paths(args.region, args.year, args.previous_year)

    evaluate_bd_pipeline(
        dmap_path=paths["GT_of_building_detection"],
        seg_path=paths["building_inference"],
        dmap_output_path=paths["evaluation_of_building_detection_gt"],
        seg_output_path=paths["evaluation_of_building_detection_predict"],
        anl_output_path=paths["evaluation_of_building_detection_anl"],
        cut_threshold=args.cut_threshold,
        bd_threshold=args.bd_threshold
    )


if __name__ == "__main__":
    main()
    print("end")
