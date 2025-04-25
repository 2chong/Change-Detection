# 🏙️ 건물 변화 탐지 및 평가 시스템

이 프로젝트는 수치지도와 추론 결과를 바탕으로 건물의 변화 여부를 분석하고, 평가 리포트를 생성하는 파이프라인입니다.

---

# 📁 프로젝트 디렉토리 구조
```
DT/
├── config/
│   ├── config.json             # 경로 설정 파일
│   └── last_selection.json     
├── Data/
│   ├── building/
│   │   ├── building_detection/
│   │   │   ├── eval/           
│   │   │   └── result/         
│   │   ├── change_detection/
│   │   │   ├── eval/           # 변화 탐지 평가 결과
│   │   │   └── result/         # 변화 탐지 결과
│   │   └── ground_truth/
│   │       ├── building_detection/    # 건물 탐지 GT
│   │       └── change_detection/      # 변화 탐지 GT
│   └── shared/
│       └── input/
│           ├── building_inference/    # 건물 추론 결과
│           └── previous_building_digital_map/   # 과거 수치지도
├── road/                     # 도로 관련 데이터 (dev-ing)
├── preprocessing/            # 전처리 모듈
├── report/
│   ├── building_detection/
│   ├── change_detection/
│   ├── map_validation/
│   └── summaries/            
│   src/
│   ├── common/                          
│   │   ├── input_parameter.py           
│   │   ├── path_config.py               
│   │   ├── path_loader.py               
│   │   └── pipeline_step_selector.py    
│   │
│   ├── core/                            
│   │   ├── building_change_detection/
│   │   │   ├── detect_building_change.py         
│   │   │   └── postprocess/                      
│   │   │
│   │   ├── map_validation/
│   │   │   ├── create_change_detection_gt.py     # 변화 탐지 GT
│   │   │   └── postprocess/                      
│   │   │
│   │   └── polygon_matching/
│   │       ├── polygon_matching_algorithm.py     # 폴리곤 매칭 알고리즘
│   │       └── polygon_matching_utils.py         # 매칭 관련 유틸
│   │
│   ├── evaluation/                      
│   │   ├── evaluate_building_change_detection.py # 건물 변화 탐지 평가
│   │   └── evaluate_building_detection.py        # 건물 탐지 평가
│   │
│   ├── utils/                           
│   │   ├── analysis_utils.py            # 분석 관련 유틸
│   │   ├── evaluation_utils.py          # 평가 관련 유틸
│   │   └── io.py                        # 입출력 관련 유틸
│   │
│   └── main.py                          
├── .gitignore
├── README.md
└── requirements.txt          # 의존성 목록
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
python src/main.py
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
```

