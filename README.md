# Building Change Detection & Evaluate System
이 프로젝트는 수치지도와 추론 결과를 바탕으로 건물의 변화 여부를 분석하고, 평가 리포트를 생성하는 파이프라인입니다.

## 📁 Directory
📦 DT/
├── config/
│   ├── config.json
│   └── last_selection.json
│
├── Data/
│   ├── evaluation/
│   │   ├── building detection GT
│   │   ├── change detection GT
│   │   ├── detect building evaluation
│   │   └── detect change evaluation
│   ├── input/
│   │   ├── building inference
│   │   └── previous building digital map
│   ├── output/
│   │   └── change detection result
│   └── true ortho image
│
├── src/
│   ├── common/
│   │   ├── input_parameter.py
│   │   ├── path_config.py
│   │   └── pipeline_step_selector.py
│   │
│   ├── core/
│   │   ├── cd_evaluate.py
│   │   ├── change_classify.py
│   │   ├── classify_dmap_error.py
│   │   ├── classify_dmap_error2.py
│   │   ├── dmap_vs_dmap.py
│   │   └── evaluate_building_detection.py
│   │
│   ├── utils/
│   │   ├── analysis_algorithm.py
│   │   ├── evaluation_utils.py
│   │   ├── polygon_matching_algorithm.py
│   │   ├── polygon_matching_utils.py
│   │   └── utils.py
│   │
│   └── main2.py
│
├── requirements.txt

