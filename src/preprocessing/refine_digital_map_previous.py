import geopandas as gpd
import os

'''
1. import_shapefiles: 두 개의 Shapefile을 불러와 좌표계를 맞춤
2. remove_small_areas: 지정된 면적보다 작은 폴리곤을 제거
3. remove_high_overlap_buildings: 이전 맵과 현재 맵에서 70% 이상 겹치는 건물 제거
4. export_shapefile: 결과를 Shapefile로 저장
5. refine_digital_map_current_pipeline: 전체 파이프라인, 위의 모든 단계를 실행하고 결과를 저장
'''

def import_shapefiles(prev_map_path, cur_map_path):
    """
    두 개의 Shapefile을 불러오는 함수.

    Args:
    - prev_map_path: 이전 원시 디지털 맵 파일 경로 (previous raw digital map)
    - cur_map_path: 수동으로 분류된 디지털 맵 파일 경로 (manually categorized digital map)

    Returns:
    - Tuple[GeoDataFrame, GeoDataFrame]: 두 개의 GeoDataFrame
    """
    prev_map = gpd.read_file(prev_map_path)
    cur_map = gpd.read_file(cur_map_path)
    prev_map = prev_map.to_crs(epsg=5186)
    cur_map = cur_map.to_crs(epsg=5186)
    return prev_map, cur_map

def remove_small_areas(gdf, max_area):
    """
    주어진 최소 면적보다 작은 폴리곤을 제거하는 함수.

    Args:
    - gdf: GeoDataFrame
    - min_area: 제거할 면적의 하한선 (0 이상의 실수)

    Returns:
    - GeoDataFrame: 필터링된 GeoDataFrame
    """
    gdf = gdf[gdf['geometry'].area >= max_area]
    return gdf


def remove_high_overlap_buildings(prev_map, cur_map, refine_categories, overlap_threshold=0.7):
    """
    선택된 정제 유형들에 따라 이전 맵과 현재 맵의 폴리곤이 모두 70% 이상 겹치는 경우 해당 폴리곤을 제거하는 함수.

    Args:
    - prev_map: 이전 원시 디지털 맵 GeoDataFrame
    - cur_map: 수동으로 분류된 디지털 맵 GeoDataFrame
    - refine_categories: 제거할 정제 유형들의 리스트 (1~8까지의 정수 리스트)
    - overlap_threshold: 겹치는 면적의 비율 임계값 (기본값: 0.7, 70%)

    Returns:
    - GeoDataFrame: 겹치는 비율이 높은 건물이 제거된 이전 디지털 맵 GeoDataFrame
    """
    # 선택된 정제 유형의 건물 필터링
    cur_map_filtered = cur_map[cur_map['분류'].isin(refine_categories)]

    def is_high_overlap(geom):
        for cur_geom in cur_map_filtered['geometry']:
            intersection_area = geom.intersection(cur_geom).area
            geom_area = geom.area
            cur_geom_area = cur_geom.area

            overlap_ratio_prev = intersection_area / geom_area
            overlap_ratio_cur = intersection_area / cur_geom_area

            if overlap_ratio_prev >= overlap_threshold and overlap_ratio_cur >= overlap_threshold:
                return True
        return False

    prev_map['is_high_overlap'] = prev_map['geometry'].apply(is_high_overlap)

    prev_map_cleaned = prev_map[~prev_map['is_high_overlap']].copy()
    prev_map_cleaned.drop(columns=['is_high_overlap'], inplace=True)

    return prev_map_cleaned


def export_shapefile(gdf, output_dir):
    """
    GeoDataFrame을 Shapefile로 내보내는 함수.

    Args:
    - gdf: 내보낼 GeoDataFrame
    - output_dir: 결과를 저장할 디렉토리 경로

    Returns:
    - None
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    output_filename = "refined_previous_digital_map.shp"
    output_path = os.path.join(output_dir, output_filename)
    gdf.to_file(output_path, driver='ESRI Shapefile', encoding='euc-kr')
    # print(f"Refined digital map saved to: {output_path}")


def refine_digital_map_current_pipeline(prev_map_path, cur_map_path, output_dir, refine_categories, max_area):
    """
    이전 디지털 맵을 정제하여 저장하는 파이프라인 함수.

    Args:
    - prev_map_path: 이전 원시 디지털 맵 파일 경로 (previous raw digital map)
    - cur_map_path: 수동으로 분류된 디지털 맵 파일 경로 (manually categorized digital map)
    - output_dir: 결과를 저장할 디렉토리 경로
    - refine_categories: 제거할 정제 유형들의 리스트 (1~8까지의 정수 리스트)
    - max_area: 제거할 면적의 하한선 (0 이상의 실수)

    Returns:
    - None
    """
    # 1. Shapefile 불러오기
    prev_map, cur_map = import_shapefiles(prev_map_path, cur_map_path)

    # 2. 면적 기준으로 제거
    prev_map = remove_small_areas(prev_map, max_area)

    # 3. 겹치는 비율이 70% 이상인 건물 제거
    prev_map = remove_high_overlap_buildings(prev_map, cur_map, refine_categories)

    # 4. 결과 내보내기
    export_shapefile(prev_map, output_dir)
