import pandas as pd
import warnings
import time
from src.common import path_config
from src.common import input_parameter
from src.common import pipeline_step_selector
from src.core import detect_building_change
from src.core import create_change_detection_gt
from src.core import evaluate_building_detection
from src.core import evaluate_building_change_detection
from src.core import classify_dmap_error
from src.common.path_config import load_paths

warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=pd.errors.SettingWithCopyWarning)


def run_pipeline(region, year, previous_year, selected_indices):
    # 경로 설정
    path_config.save_last_selection(region, year, previous_year)
    paths = path_config.load_paths(region, year, previous_year)

    def detect_building():
        print(f"\n▶ 지역: {region} 시작")
        start_time = time.time()
        evaluate_building_detection.evaluate_bd_pipeline(
            paths['GT_of_building_detection'],
            paths['building_inference'],
            paths['evaluation_of_building_detection_gt'],
            paths['evaluation_of_building_detection_predict'],
            paths['evaluation_of_building_detection_anl'],
            0.05,
            0.6
        )
        print(f"Evaluate Building Detection - 완료 ({time.time() - start_time:.2f}초)")

    def validate_change_detection():
        print(f"\n▶ 지역: {region} 시작")
        start_time = time.time()
        create_change_detection_gt.cd_pipeline(
            paths['previous_building_digital_map'],
            paths['GT_of_building_detection'],
            paths['GT_of_building_change_detection_prev'],
            paths['GT_of_building_change_detection_cur'],
            paths['GT_of_building_change_detection_anl'],
            0.05,
            0.95
        )
        print(f"Create Building Change Detection GT - 완료 ({time.time() - start_time:.2f}초)")

    def detect_change():
        print(f"\n▶ 지역: {region} 시작")
        start_time = time.time()
        detect_building_change.cd_pipeline(
            paths['previous_building_digital_map'],
            paths['evaluation_of_building_detection_predict'],
            paths['building_change_detection_result_prev'],
            paths['building_change_detection_result_cur'],
            paths['building_change_detection_result_anl'],
            0.05,
            0.7
        )
        print(f"Detect Change - 완료 ({time.time() - start_time:.2f}초)")

    def evaluate_change_detection():
        print(f"\n▶ 지역: {region} 시작")
        start_time = time.time()
        evaluate_building_change_detection.cd_evaluate_pipeline(
            paths['GT_of_building_change_detection_prev'],
            paths['GT_of_building_change_detection_cur'],
            paths['building_change_detection_result_prev'],
            paths['building_change_detection_result_cur'],
            paths['evaluation_of_building_change_detection']
        )
        print(f"Evaluate Change Detection - 완료 ({time.time() - start_time:.2f}초)")

    def classify_dmap_error2():
        start_time = time.time()
        classify_dmap_error.run_pipeline(
            paths['image'],
            paths['dmap_vs_dmap_current_result'],
            paths['dmap_vs_dmap_prev_result'],
            paths['change_classify_seg_result'],
            paths['dmap_error_result'],
            10
        )
        print(f"Detect Error - 완료 ({time.time() - start_time:.2f}초)")

    pipeline_steps = [
        ("Evaluate Building Detection", detect_building),
        ("Detect Change", detect_change),
        ("Evaluate Change Detection", evaluate_change_detection),
        ("Dmap vs Dmap", validate_change_detection),
        ("Detect Error", classify_dmap_error2)
    ]

    pipeline_step_selector.run_selected_pipeline_steps(pipeline_steps, selected_indices)


# ----------- 메인 실행부 -----------

last_selection = path_config.load_last_selection()
region = path_config.select_region()
year = path_config.select_year("연도를 입력하세요", last_selection, 'year')
previous_year = path_config.select_year("이전 연도를 입력하세요", last_selection, 'previous_year')

gt_min_area, gt_max_area, gt_refine_categories, detection_threshold, detection_area, change_detection_area_range = \
    input_parameter.get_multiple_inputs_with_defaults()

pipeline_steps = [
    ("Evaluate Building Detection", None),
    ("Detect Change", None),
    ("Evaluate Change Detection", None),
    ("Create Building Change Detection GT", None),
    ("Detect Error", None)
]
selected_indices = pipeline_step_selector.get_selected_pipeline_indices(pipeline_steps)

# 지역 처리
if region == "all":
    for r in path_config.regions:
        run_pipeline(r, year, previous_year, selected_indices)
else:
    run_pipeline(region, year, previous_year, selected_indices)
