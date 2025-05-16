import geopandas as gpd
import os

"""
1. import_building_footprint_file: Shapefile을 불러와 좌표계를 맞춤
2. filter_by_area: 지정된 면적 범위 밖에 있는 객체들을 필터링
3. filter_by_type: 선택된 분류 유형의 객체들을 필터링
4. export_shapefile: 필터링된 GeoDataFrame을 Shapefile로 저장
5. refined_digital_map_pipeline: 전체 파이프라인 실행, 면적과 유형 필터링 후 결과를 저장

<정제 유형>
{1: 정상, 2: 육안확인불가, 3: 그림자(일부), 4: 나무(일부), 5: 옥외주차장, 6: 옥상정원, 7: 부속건물, 8: 잘린건물, 9: 기타}
"""

def import_building_footprint_file(file_path, crs=5186):
    gdf = gpd.read_file(file_path)
    if gdf.crs != f"epsg:{crs}":
        gdf = gdf.to_crs(epsg=crs)
    return gdf


def filter_by_area(gdf, min_area=0, max_area=None):
    if min_area is not None and max_area is not None:
        gdf = gdf[(gdf['geometry'].area < min_area) | (gdf['geometry'].area > max_area)]
    return gdf


def filter_by_type(gdf, remove_types):
    if '분류' not in gdf.columns:
        return gdf

    if isinstance(remove_types, int):
        remove_types = [remove_types]
    gdf = gdf[~gdf['분류'].isin(remove_types)]
    return gdf


def export_shapefile(gdf, output_dir):
    output_filename = "refined_current_building_footprint_gt.shp"
    output_path = os.path.join(output_dir, output_filename)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    if gdf.crs is None:
        gdf = gdf.set_crs(epsg=EPSG_CODE)
    gdf.to_file(output_path, driver='ESRI Shapefile', encoding='euc-kr')


def refined_digital_map_pipeline(gt_path, min_area, max_area, remove_types, output_dir):
    gt_gdf = import_building_footprint_file(gt_path)
    initial_count = len(gt_gdf)
    area_filtered_gdf = gt_gdf[(gt_gdf['geometry'].area < min_area) | (gt_gdf['geometry'].area > max_area)]
    removed_by_area = initial_count - len(area_filtered_gdf)
    type_filtered_gdf = filter_by_type(area_filtered_gdf, remove_types)
    removed_by_type = len(area_filtered_gdf) - len(type_filtered_gdf)
    final_count = len(type_filtered_gdf)
    export_shapefile(type_filtered_gdf, output_dir)
