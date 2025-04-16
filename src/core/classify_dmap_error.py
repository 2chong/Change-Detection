import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import box
import numpy as np
import rasterio
import os
import pandas as pd
from rasterio.warp import calculate_default_transform, reproject, Resampling
import matplotlib as mpl
from matplotlib.ticker import ScalarFormatter


plt.rcParams['font.family'] = 'Malgun Gothic'  # ✅ 한글 폰트 설정
mpl.rcParams['axes.unicode_minus'] = False     # ✅ 음수 기호 깨짐 방지


def import_shapefile(file_path, image_crs):
    gdf = gpd.read_file(file_path)
    if gdf.crs != image_crs:
        gdf = gdf.to_crs(image_crs)
    return gdf


def import_tiffile(file_path):
    tif_files = [f for f in os.listdir(file_path) if f.lower().endswith('.tif')]
    file = os.path.join(file_path, tif_files[0])
    with rasterio.open(file) as src:
        image = src.read()
        bounds = src.bounds  # (minx, miny, maxx, maxy)
        crs = src.crs        # ✅ 좌표계 추가
    return image, (bounds.left, bounds.bottom, bounds.right, bounds.top), crs


def crop_image_by_bounds_direct(image, image_bounds, bounds):
    minx, miny, maxx, maxy = bounds
    img_minx, img_miny, img_maxx, img_maxy = image_bounds
    _, height, width = image.shape

    # 가로(x) 보간: col 방향
    col_start = int((minx - img_minx) / (img_maxx - img_minx) * width)
    col_end   = int((maxx - img_minx) / (img_maxx - img_minx) * width)

    # 세로(y) 보간: row 방향 (y는 위→아래)
    row_start = int((img_maxy - maxy) / (img_maxy - img_miny) * height)
    row_end   = int((img_maxy - miny) / (img_maxy - img_miny) * height)

    # 클램핑
    col_start = max(0, min(col_start, width))
    col_end   = max(0, min(col_end, width))
    row_start = max(0, min(row_start, height))
    row_end   = max(0, min(row_end, height))

    if row_end <= row_start or col_end <= col_start:
        return np.zeros((1, 1, image.shape[0])), bounds

    cropped = image[:, row_start:row_end, col_start:col_end]
    return np.transpose(cropped, (1, 2, 0)), (minx, maxx, miny, maxy)


def process_error_objects_split_view(current_gdf, past_gdf, seg_gdf, image, image_bounds, buffer_size):
    if 'err_list' not in current_gdf.columns:
        current_gdf['err_list'] = None

    visited_indices = set()

    # 1. 기본 후보군
    base_candidates = current_gdf[
        (current_gdf['cd_class'].isin(['신축', '갱신'])) |
        (current_gdf['Relation'].isin(['1:N', 'N:1', 'N:N']))
    ].copy()

    # 2. 추가 후보군 (1:1 & 변화없음 & seg_gdf와 겹치지 않는)
    extra_cond = (current_gdf['cd_class'] == '변화없음') & (current_gdf['Relation'] == '1:1')
    change_no_seg = current_gdf[extra_cond].copy()
    joined = gpd.sjoin(change_no_seg, seg_gdf[['geometry']], how='left', predicate='intersects')
    change_no_seg_filtered = joined[joined['index_right'].isna()].drop(columns='index_right')

    # 최종 후보군
    candidates = pd.concat([base_candidates, change_no_seg_filtered], ignore_index=False)

    for idx, row in candidates.iterrows():
        if idx in visited_indices:
            continue

        visited_indices.add(idx)
        geom = row['geometry']
        bbox = box(*geom.bounds).buffer(buffer_size)
        cropped_image, bounds = crop_image_by_bounds_direct(image, image_bounds, bbox.bounds)

        # 현재 그룹: 같은 poly2_idx
        poly2_val = row['poly2_idx']
        current_group = current_gdf[current_gdf['poly2_idx'] == poly2_val]
        visited_indices.update(current_group.index)

        # 과거 객체 매칭
        related_past = gpd.GeoDataFrame(columns=past_gdf.columns)
        primary_poly1 = row['poly1_idx']
        if pd.notna(primary_poly1):
            past_primary = past_gdf[past_gdf['poly1_idx'] == primary_poly1]
            if not past_primary.empty:
                poly2_match = past_primary.iloc[0]['poly2_idx']
                if pd.notna(poly2_match):
                    related_past = past_gdf[past_gdf['poly2_idx'] == poly2_match]
                    related_past = related_past.drop_duplicates(subset='poly1_idx')
                else:
                    related_past = past_primary

        # 결과 저장용
        user_input_result = {}

        def on_key(event):
            if event.key in ['1', '2', '3', '4']:
                user_input_result['val'] = int(event.key)
                plt.close()
            else:
                print("❌ 잘못된 키입니다. 1~4 중에서 선택하세요.")

        fig, axes = plt.subplots(1, 2, figsize=(12, 6))
        fig.canvas.mpl_connect('key_press_event', on_key)
        fig.suptitle(
            "1: Error1 (현재 영상과 현재 수치지도는 불일치, 과거 수치지도 객체는 일치하는 경우)\n"
            "2: Error2 (현재 영상과 현재 수치지도 및, 과거 수치지도 객체 모두 일치하지 않는 경우)\n"
            "3: Error3 (현재 영상에 건물이 없는데 현재 수치지도에 그려진 경우)\n"
            "4: 정상 (현재 영상과 현재 수치지도 객체가 일치할 경우)",
            fontsize=13
        )

        # 왼쪽: 현재 객체
        axes[0].imshow(cropped_image, extent=tuple(bounds))
        axes[0].set_xlim(bounds[0], bounds[1])
        axes[0].set_ylim(bounds[2], bounds[3])
        axes[0].ticklabel_format(style='plain', axis='both')
        axes[0].xaxis.set_major_formatter(ScalarFormatter(useOffset=False))
        axes[0].yaxis.set_major_formatter(ScalarFormatter(useOffset=False))
        gpd.GeoSeries(current_group['geometry']).plot(ax=axes[0], facecolor='none', edgecolor='red', linewidth=2)
        cd_class = row['cd_class']
        relation = row['Relation']
        axes[0].set_title(f"[현재 수치 지도] poly2_idx={poly2_val} | 유형: {cd_class} | 관계: {relation}")

        # 오른쪽: 과거 객체 + 현재 영상
        axes[1].imshow(cropped_image, extent=tuple(bounds))
        axes[1].set_xlim(bounds[0], bounds[1])
        axes[1].set_ylim(bounds[2], bounds[3])
        axes[1].ticklabel_format(style='plain', axis='both')
        axes[1].xaxis.set_major_formatter(ScalarFormatter(useOffset=False))
        axes[1].yaxis.set_major_formatter(ScalarFormatter(useOffset=False))

        if not related_past.empty:
            gpd.GeoSeries(related_past['geometry']).plot(ax=axes[1], facecolor='none', edgecolor='blue', linestyle='--', linewidth=2)
            axes[1].set_title("[현재 영상 + 과거 수치지도 객체]")
        else:
            axes[1].text(0.5, 0.5, "매칭되는 과거 수치지도가 없음", ha='center', va='center', fontsize=12)
            axes[1].set_title("[현재 영상 + 과거 수치지도 객체 없음]")

        plt.subplots_adjust(top=0.75)
        plt.show(block=True)

        # 결과 저장
        if 'val' in user_input_result:
            for i in current_group.index:
                current_gdf.at[i, 'err_list'] = user_input_result['val']
        else:
            print(f"⚠️ 객체 {idx}에 대해 유효한 입력이 없어 건너뜀")

    return current_gdf


def process_past_error_objects_split_view(past_gdf, image, image_bounds, buffer_size):
    if 'err_list' not in past_gdf.columns:
        past_gdf['err_list'] = None

    past_candidates = past_gdf[past_gdf['cd_class'] == '소멸']

    for idx, row in past_candidates.iterrows():
        geom = row['geometry']
        bbox = box(*geom.bounds).buffer(buffer_size)
        cropped_image, bounds = crop_image_by_bounds_direct(image, image_bounds, bbox.bounds)

        user_input_result = {}

        def on_key(event):
            if event.key in ['1', '2', '3', '4']:
                user_input_result['val'] = int(event.key)
                plt.close()
            else:
                print("❌ 잘못된 키입니다. 1~4 중에서 입력하세요.")

        fig, axes = plt.subplots(1, 2, figsize=(12, 6))
        fig.canvas.mpl_connect('key_press_event', on_key)
        fig.suptitle(
            "1: Error1 (과거 수치지도 객체가 현재 영상과 형상이 일치하지 않는 경우)\n"
            "2: Error2 (과거 수치지도 객체가 현재 영상과 형상이 일치하는 경우)\n"
            "3: Error3\n"
            "4: 정상 (과거 수치지도 객체가 있는 곳에 건물이 존재하지 않는 경우)",
            fontsize=13
        )
        # 왼쪽: 현재 영상만
        axes[0].imshow(cropped_image, extent=tuple(bounds))
        axes[0].set_xlim(bounds[0], bounds[1])
        axes[0].set_ylim(bounds[2], bounds[3])
        axes[0].xaxis.set_major_formatter(ScalarFormatter(useOffset=False))
        axes[0].yaxis.set_major_formatter(ScalarFormatter(useOffset=False))
        axes[0].ticklabel_format(style='plain', axis='both')
        axes[0].set_title(f"[현재 영상] 과거 idx: {idx}")

        # 오른쪽: 현재 영상 + 과거 수치지도 객체(소멸)
        axes[1].imshow(cropped_image, extent=tuple(bounds))
        axes[1].set_xlim(bounds[0], bounds[1])
        axes[1].set_ylim(bounds[2], bounds[3])
        axes[1].xaxis.set_major_formatter(ScalarFormatter(useOffset=False))
        axes[1].yaxis.set_major_formatter(ScalarFormatter(useOffset=False))
        axes[1].ticklabel_format(style='plain', axis='both')
        gpd.GeoSeries([geom]).plot(ax=axes[1], facecolor='none', edgecolor='blue', linewidth=2)
        axes[1].set_title("[현재 영상 + 소멸 객체]")

        plt.subplots_adjust(top=0.75)
        plt.show(block=True)

        if 'val' in user_input_result:
            past_gdf.at[idx, 'err_list'] = user_input_result['val']
        else:
            print(f"⚠️ 과거 객체 {idx} → 입력값 없음. 건너뜀")

    return past_gdf


def process_new_buildings_view_only(seg_result, image, image_bounds, buffer_size=10):
    if 'err_list' not in seg_result.columns:
        seg_result['err_list'] = None

    candidates = seg_result[seg_result['cd_class'] == '신축']

    for idx, row in candidates.iterrows():
        geom = row['geometry']
        bbox = box(*geom.bounds).buffer(buffer_size)
        cropped_image, bounds = crop_image_by_bounds_direct(image, image_bounds, bbox.bounds)

        user_input_result = {}

        def on_key(event):
            if event.key in ['1', '2', '3', '4']:
                user_input_result['val'] = int(event.key)
                plt.close()
            else:
                print("❌ 잘못된 키입니다. 1~4 중에서 입력하세요.")

        fig, ax = plt.subplots(1, 1, figsize=(8, 8))
        fig.canvas.mpl_connect('key_press_event', on_key)
        fig.suptitle(
            "1: Error1\n"
            "2: Error2 (건물인 곳에 추론 결과가 있는 경우)\n"
            "3: Error3\n"
            "4: 정상 (건물이 아닌 곳에 추론 결과가 있는 경우)",
            fontsize=13
        )
        ax.imshow(cropped_image, extent=tuple(bounds))
        gpd.GeoSeries([geom]).plot(ax=ax, facecolor='none', edgecolor='red', linewidth=2)
        ax.set_title(f"[신축 객체] index: {idx}")
        ax.ticklabel_format(style='plain', axis='both')

        plt.subplots_adjust(top=0.75)
        plt.show(block=True)

        if 'val' in user_input_result:
            seg_result.at[idx, 'err_list'] = user_input_result['val']
        else:
            print(f"⚠️ 신축 객체 {idx} → 입력값 없음. 건너뜀")

    return seg_result


def collect_error_candidates(current_gdf, past_gdf, seg_gdf):
    # 1. 현재 수치지도: 신축, 갱신 또는 1:N, N:1, N:N
    current_cond = (
        current_gdf['cd_class'].isin(['신축', '갱신']) |
        current_gdf['Relation'].isin(['1:N', 'N:1', 'N:N'])
    )
    current_candidates = current_gdf[current_cond].copy()
    current_candidates['source'] = 'current'

    # 2. 과거 수치지도: 소멸
    past_candidates = past_gdf[past_gdf['cd_class'] == '소멸'].copy()
    past_candidates['source'] = 'past'

    # 3. seg 결과: 신축
    seg_candidates = seg_gdf[seg_gdf['cd_class'] == '신축'].copy()
    seg_candidates['source'] = 'seg'

    # 4. 하나로 합치기
    combined = pd.concat([current_candidates, past_candidates, seg_candidates], ignore_index=True)

    # 5. err_status 열 생성
    def determine_status(row):
        cd_class = row.get('cd_class', '')
        relation = row.get('Relation', '')
        ufid = row.get('UFID', None)

        if cd_class == '신축':
            if pd.notna(ufid):
                return '수치지도_신축'
            else:
                return '추론결과_신축'
        elif cd_class == '소멸':
            return '소멸'
        elif cd_class == '갱신':
            return '갱신'
        elif cd_class == '변화없음':
            return relation
        else:
            return '기타'

    combined['err_status'] = combined.apply(determine_status, axis=1)

    return combined


def export_shapefile(gdf, output_path, file_name):
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    full_path = os.path.join(output_path, file_name + '.shp')
    gdf.to_file(full_path, driver='ESRI Shapefile', encoding='euc-kr')


def run_pipeline(image_path, current_path, past_path, seg_path, output_path, buffer_size):
    image, image_bounds, image_crs = import_tiffile(image_path)

    current_gdf = import_shapefile(current_path, image_crs)
    past_gdf = import_shapefile(past_path, image_crs)
    seg_gdf = import_shapefile(seg_path, image_crs)

    error_suspect = collect_error_candidates(current_gdf, past_gdf, seg_gdf)
    export_shapefile(error_suspect, output_path, 'error_suspect')

    current_gdf = process_error_objects_split_view(current_gdf, past_gdf, seg_gdf, image, image_bounds, buffer_size)
    past_gdf = process_past_error_objects_split_view(past_gdf, image, image_bounds, buffer_size)
    seg_gdf = process_new_buildings_view_only(seg_gdf, image, image_bounds, buffer_size)

    current_err = current_gdf[current_gdf['err_list'].isin([1, 2, 3])]
    past_err = past_gdf[past_gdf['err_list'].isin([1, 2, 3])]
    seg_err = seg_gdf[seg_gdf['err_list'].isin([1, 2, 3])]
    all_errors = pd.concat([current_err, past_err, seg_err], ignore_index=True)

    export_shapefile(current_gdf, output_path, 'classified_error_current_dmap')
    export_shapefile(past_gdf, output_path, 'classified_error_past_dmap')
    export_shapefile(seg_gdf, output_path, 'classified_error_seg_result')
    export_shapefile(all_errors, output_path, 'classified_error_all_concat')
