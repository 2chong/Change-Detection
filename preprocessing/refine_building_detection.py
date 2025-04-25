import pandas as pd
import geopandas as gpd
import os
import numpy as np

'''
1. import_shapefile: Shapefile을 불러와 좌표계를 맞추는 작업 수행
2. calculate_accuracy_by_attribute: 주어진 면적 이상인 건물 정보만 필터링하여 반환
3. export_shapefile: 필터링된 GeoDataFrame을 지정된 디렉토리에 Shapefile로 저장
4. building_extraction_evaluation_pipeline: 전체 파이프라인 실행, 필터링된 건물 정보 추출 및 저장
'''


def import_shapefile(file_path, crs=5186):
    gdf = gpd.read_file(file_path)
    if gdf.crs != f"epsg:{crs}":
        gdf = gdf.to_crs(epsg=crs)
    return gdf


def calculate_accuracy_by_attribute(building_inf, max_area=100):
    filtered_building_inf = building_inf[building_inf['geometry'].area >= max_area]
    return filtered_building_inf


def export_shapefile(gdf, output_dir, output_filename):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    output_path = os.path.join(output_dir, output_filename)
    gdf.to_file(output_path, driver='ESRI Shapefile', encoding='euc-kr')


def refine_building_detection(building_inf_path, output_path, max_area):
    building_inf = import_shapefile(building_inf_path)
    filtered_building_inf = calculate_accuracy_by_attribute(building_inf, max_area)
    export_shapefile(filtered_building_inf, output_path, 'refined_building_inference.shp')


