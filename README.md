# 🏙️ 건물 변화 탐지 및 평가 시스템

이 프로젝트는 수치지도와 추론 결과를 바탕으로 건물의 변화 여부를 분석하고, 평가 리포트를 생성하는 파이프라인입니다.

---

## 📁 디렉터리 구조

```
DT/
├── config/
│   ├── config.json
│   └── last_selection.json
│
├── Data/
│   └── building/
│       ├── evaluation/
│       │   ├── evaluation result/
│       │   │   ├── evaluation of building change detection/
│       │   │   └── evaluation of building detection/
│       │   └── ground truth/
│       │       ├── building change detection GT/
│       │       └── building detection GT/
│       ├── input/
│       │   ├── building inference/
│       │   └── previous building digital map/
│       └── output/
│           └── building change detection result/
│
├── src/
│   ├── common/
│   │   ├── input_parameter.py
│   │   ├── path_config.py
│   │   ├── path_loader.py
│   │   └── pipeline_step_selector.py
│   ├── core/
│   │   ├── classify_dmap_error.py
│   │   ├── classify_dmap_error2.py
│   │   ├── create_change_detection_gt.py
│   │   ├── detect_building_change.py
│   │   ├── evaluate_building_change_detection.py
│   │   └── evaluate_building_detection.py
│   ├── utils/
│   │   ├── analysis_utils.py
│   │   ├── evaluation_utils.py
│   │   ├── polygon_matching_algorithm.py
│   │   ├── polygon_matching_utils.py
│   │   └── io.py
│   └── main2.py
│
├── requirements.txt
└── README.md
```

---

## 📢 파이프 라인

총 4개의 파이프라인으로 구성됩니다.

### Input: 과거 수치지도, 현재 건물 추론 결과

### 1. Evaluate Building Detection
### 2. Create Change Detection GT
### 3. Detect Building Change
### 4. Evaluate Building Change Detection

### Output: 변화탐지 결과(과거 및 현재)

---

## ⚙️ 설치 방법

Python 3.10으로 테스트하였습니다.

1. 가상환경 생성
```bash
python -m venv .venv_dt
source .venv_dt/Scripts/activate  # Windows
```

2. 라이브러리 설치
```bash
pip install -r requirements.txt
```

---

## 🚀 실행 방법

### 전체 파이프라인 실행

Sources root에서 실행

```bash
set PYTHONPATH=%cd%
python src/main2.py
```

이후 터미널에서 지역, 연도, 이전 연도를 입력하고 실행할 단계들을 선택하면 자동으로 파이프라인이 실행됩니다.

### 단일 파이프라인 실행 (예: GT 생성)

Sources root에서 실행

```bash
set PYTHONPATH=%cd%
python src/core/create_change_detection_gt.py --region suseo --year 2022 --previous_year 2020
```

옵션:
- `--region`: 대상 지역 (예: gangseo)
- `--year`: 기준 연도 (기본값: 2022)
- `--previous_year`: 과거 연도 (기본값: 2020)
- `--cut_threshold`: 그래프 컷 임계값 (기본값: 0.05)
- `--cd_threshold`: 건물 변화 판별 임계값 (기본값: 0.7) - (GT 생성 시 0.95)
- `--bd_threshold`: 건물 탐지 판별 임계값 (기본값: 0.6)

---

## ✅ 요구사항 (`requirements.txt`)

```
numpy==2.2.4
pandas==2.2.3
geopandas==1.0.1
networkx==3.4.2
rasterio==1.3.9
matplotlib==3.10.1
rasterio==1.4.3
```

