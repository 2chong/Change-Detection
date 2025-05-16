# 🏗️ 건물 변화 탐지 웹 애플리케이션

본 프로젝트는 사용자가 업로드한 두 개의 공간 데이터(shapefile ZIP)를 기반으로 **건물 변화 탐지 알고리즘**을 실행하고,  
결과를 shapefile로 저장 후 압축하여 **웹에서 바로 다운로드**할 수 있는 FastAPI 기반 웹 애플리케이션입니다.

---

## 📁 프로젝트 구조

```
DT/
├── app/
│   ├── main.py                ← FastAPI 진입점
│   ├── templates/
│   │   └── upload.html        ← 업로드 및 결과 다운로드 페이지
│   └── static/
│       ├── uploads/           ← 사용자가 업로드한 ZIP 파일 저장
│       └── results/           ← 분석 결과(SHP, ZIP) 저장
│
├── src/
│   ├── core/                            
│   │   ├── building_change_detection/
│   │   │   ├── detect_building_change.py         
│   │   │   └── postprocess/                                      
│   │   │
│   │   └── polygon_matching/
│   │       ├── polygon_matching_algorithm.py     # 폴리곤 매칭 알고리즘
│   │       └── polygon_matching_utils.py         # 매칭 관련 유틸
│   │
│   ├── utils/                           
│   │   └── io.py 
│
├── requirements.txt
└── README.md
```

---

## ⚙️ 기능 요약

- 웹 기반 SHP ZIP 업로드 (과거 수치지도, 현재 추론 결과)
- 사용자가 직접 `cut_threshold`, `cd_threshold` 설정 가능
- 서버에서 변화 탐지 알고리즘 실행 
- 결과를 shapefile로 저장하고 자동 ZIP 압축
- 웹에서 결과 바로 다운로드 가능

---

## 🚀 실행 방법

### 1. 패키지 설치

```bash
pip install -r requirements.txt
```

### 2. FastAPI 앱 실행

```bash
uvicorn app.main:app --reload
```

→ 브라우저에서 [http://localhost:8000](http://localhost:8000) 접속

---

## 📦 requirements.txt

```
fastapi
uvicorn[standard]
jinja2
numpy==2.2.4
pandas==2.2.3
geopandas==1.0.1
networkx==3.4.2
rasterio==1.3.9
```

---


