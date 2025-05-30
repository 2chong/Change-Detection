# GeoJSON 기반 건물 변화탐지 API

이 프로젝트는 GeoTIFF 영상과 과거 GeoJSON 형식의 건물 데이터를 기반으로, 최신 건물 객체를 추론하고 공간 변화 탐지를 수행하는 FastAPI 기반 웹 애플리케이션입니다.

## ✅ 주요 기능

- GeoTIFF 영상을 기반으로 ONNX 모델을 사용해 건물 마스크 추론
- 추론 결과를 벡터화하여 현재 건물 GeoJSON 생성
- 사용자가 업로드한 과거 GeoJSON과 비교하여 변화 탐지 수행
- 변화 유형에 따라 `dmap_result.geojson` 및 `seg_result.geojson`으로 출력

## 🗂️ 폴더 구조

```
app/
├── main.py                  # FastAPI 서버 로직
├── templates/
│   └── upload.html          # 웹 UI (파일 업로드 및 결과 시각화)
├── static/
│   ├── uploads/             # 업로드된 GeoTIFF 및 GeoJSON
│   └── results/             # 추론 및 변화탐지 결과 (.tif, .png, .geojson)
GeoDeep/
└── model/
    └── building_2005_deepness.onnx  # 사전 학습된 건물 추론 모델
```

## 🖼️ 웹 UI 사용 방법

1. 메인 페이지 (`http://127.0.0.1:8000`) 접속
2. GeoTIFF 영상과 과거 GeoJSON 파일 선택
3. 해상도 및 임계값 설정 후 "변화탐지 시작" 클릭
4. 결과 페이지에서 마스크 이미지와 GeoJSON 다운로드 가능

## ⚙️ 실행 방법

```bash
uvicorn app.main:app --reload
```

## 📦 요구사항

- Python >= 3.8
- FastAPI
- Uvicorn
- GeoPandas
- Rasterio, NumPy, PIL 등

```bash
pip install -r requirements.txt
```

## 🧠 모델 경로

모델은 `GeoDeep/model/building_2005_deepness.onnx` 경로에 고정되어 있으며, 사용자 입력 없이 자동 사용됩니다.

## 📤 입출력 형식

- 입력: `.tif` (GeoTIFF), `.geojson`
- 출력: `dmap_result.geojson`, `seg_result.geojson`, 마스크 이미지 (.png)

## 🙋 문의

기술적 문의는 프로젝트 관리자에게 연락해주세요.