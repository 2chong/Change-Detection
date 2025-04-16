import pandas as pd
from itertools import chain, combinations
from shapely.ops import unary_union
import numpy as np
import geopandas as gpd


def all_nonempty_subsets(lst):
    return list(chain.from_iterable(combinations(lst, r) for r in range(1, len(lst)+1)))


def classify_relation(n1, n2):
    if n1 >= 1 and n2 == 0:
        return "1:0"
    elif n1 == 0 and n2 >= 1:
        return "0:1"
    elif n1 == 1 and n2 == 1:
        return "1:1"
    elif n1 == 1 and n2 > 1:
        return "1:N"
    elif n1 > 1 and n2 == 1:
        return "N:1"
    elif n1 > 1 and n2 > 1:
        return "N:N"
    else:
        return "Unknown"


def get_combination(p1_subset, p2_subset, full_p1, full_p2):
    p1_set = set(p1_subset)
    p2_set = set(p2_subset)

    # 1. 둘 다 하나짜리면 먼저 체크
    if len(p1_set) == 1 and len(p2_set) == 1:
        return 'single_pair'

    # 2. poly1 전체 + poly2 하나
    if p1_set == full_p1 and len(p2_set) == 1:
        return 'union_poly1'

    # 3. poly2 전체 + poly1 하나
    if p2_set == full_p2 and len(p1_set) == 1:
        return 'union_poly2'

    # 4. 양쪽 다 전체
    if p1_set == full_p1 and p2_set == full_p2:
        return 'union_both'

    # 5. 아무것도 해당 안 됨
    return ''


def generate_components_df(component_dict):
    rows = []

    for comp_idx, comp in component_dict.items():
        poly1_list = comp['poly1_set']
        poly2_list = comp['poly2_set']
        full_p1 = set(poly1_list)
        full_p2 = set(poly2_list)

        Relation = classify_relation(len(full_p1), len(full_p2))

        if len(full_p1) > 0 and len(full_p2) > 0:
            # 양쪽 모두 있을 경우: 조합 생성
            for p1_subset in all_nonempty_subsets(poly1_list):
                for p2_subset in all_nonempty_subsets(poly2_list):
                    combi = get_combination(p1_subset, p2_subset, full_p1, full_p2)
                    rows.append({
                        'comp_idx': comp_idx,
                        'Relation': Relation,
                        'poly1_set': p1_subset,
                        'poly2_set': p2_subset,
                        'combi': combi
                    })
        elif len(full_p1) == 0 and len(full_p2) > 0:
            # 0:1 관계
            for p2 in poly2_list:
                rows.append({
                    'comp_idx': comp_idx,
                    'Relation': Relation,
                    'poly1_set': (np.nan,),
                    'poly2_set': (p2,),
                    'combi': None
                })
        elif len(full_p1) > 0 and len(full_p2) == 0:
            # 1:0 관계
            for p1 in poly1_list:
                rows.append({
                    'comp_idx': comp_idx,
                    'Relation': Relation,
                    'poly1_set': (p1,),
                    'poly2_set': (np.nan,),
                    'combi': None
                })

    return pd.DataFrame(rows)


def compute_metrics_for_combi_df(df, poly1_gdf, poly2_gdf):
    iou_list = []
    ol1_list = []
    ol2_list = []

    for _, row in df.iterrows():
        poly1_ids = list(row['poly1_set'])
        poly2_ids = list(row['poly2_set'])

        # nan 포함 여부 체크
        if any(pd.isna(poly1_ids)) or any(pd.isna(poly2_ids)):
            iou_list.append(np.nan)
            ol1_list.append(np.nan)
            ol2_list.append(np.nan)
            continue

        # union
        geom1 = unary_union(poly1_gdf[poly1_gdf['poly1_idx'].isin(poly1_ids)].geometry)
        geom2 = unary_union(poly2_gdf[poly2_gdf['poly2_idx'].isin(poly2_ids)].geometry)

        if geom1 and geom2 and not geom1.is_empty and not geom2.is_empty:
            intersection = geom1.intersection(geom2)
            union = geom1.union(geom2)
            iou = intersection.area / union.area if union.area > 0 else 0
            ol1 = intersection.area / geom1.area if geom1.area > 0 else 0
            ol2 = intersection.area / geom2.area if geom2.area > 0 else 0
        else:
            iou = 0
            ol1 = 0
            ol2 = 0

        iou_list.append(iou)
        ol1_list.append(ol1)
        ol2_list.append(ol2)

    df['IoU'] = iou_list
    df['ol1'] = ol1_list
    df['ol2'] = ol2_list

    return df


def attach_metrics_to_polys(poly1, poly2, combi_df):
    poly1 = poly1.copy()
    poly2 = poly2.copy()

    # 새로운 컬럼 이름 매핑
    metric_cols = [
        'Relation',
        'comp_idx',
        'iou_1n', 'ol_pl1_1n', 'ol_pl2_1n',
        'iou_n1', 'ol_pl1_n1', 'ol_pl2_n1',
        'iou_11', 'ol_pl1_11', 'ol_pl2_11',
        'iou_nn', 'ol_pl1_nn', 'ol_pl2_nn',
    ]

    for col in metric_cols:
        if col not in poly1.columns:
            poly1[col] = None
        if col not in poly2.columns:
            poly2[col] = None

    for _, row in combi_df.iterrows():
        combi = row['combi']
        rel = row['Relation']
        comp = row['comp_idx']
        iou, ol1, ol2 = row['IoU'], row['ol1'], row['ol2']
        p1_set = row['poly1_set']
        p2_set = row['poly2_set']

        if combi == 'single_pair':
            if rel == 'N:N':
                continue
            for p1 in p1_set:
                poly1.loc[poly1['poly1_idx'] == p1, ['iou_nn', 'ol_pl1_nn', 'ol_pl2_nn']] = iou, ol1, ol2
                poly1.loc[poly1['poly1_idx'] == p1, ['comp_idx', 'Relation']] = comp, rel
            for p2 in p2_set:
                poly2.loc[poly2['poly2_idx'] == p2, ['iou_nn', 'ol_pl1_nn', 'ol_pl2_nn']] = iou, ol1, ol2
                poly2.loc[poly2['poly2_idx'] == p2, ['comp_idx', 'Relation']] = comp, rel

        elif combi == 'union_poly1':
            for p1 in p1_set:
                poly1.loc[poly1['poly1_idx'] == p1, ['iou_1n', 'ol_pl1_1n', 'ol_pl2_1n']] = iou, ol1, ol2
                poly1.loc[poly1['poly1_idx'] == p1, ['comp_idx', 'Relation']] = comp, rel
            for p2 in p2_set:
                poly2.loc[poly2['poly2_idx'] == p2, ['iou_1n', 'ol_pl1_1n', 'ol_pl2_1n']] = iou, ol1, ol2
                poly2.loc[poly2['poly2_idx'] == p2, ['comp_idx', 'Relation']] = comp, rel

        elif combi == 'union_poly2':
            for p2 in p2_set:
                poly2.loc[poly2['poly2_idx'] == p2, ['iou_n1', 'ol_pl1_n1', 'ol_pl2_n1']] = iou, ol1, ol2
                poly2.loc[poly2['poly2_idx'] == p2, ['comp_idx', 'Relation']] = comp, rel
            for p1 in p1_set:
                poly1.loc[poly1['poly1_idx'] == p1, ['iou_n1', 'ol_pl1_n1', 'ol_pl2_n1']] = iou, ol1, ol2
                poly1.loc[poly1['poly1_idx'] == p1, ['comp_idx', 'Relation']] = comp, rel

        elif combi == 'union_both':
            for p1 in p1_set:
                poly1.loc[poly1['poly1_idx'] == p1, ['iou_11', 'ol_pl1_11', 'ol_pl2_11']] = iou, ol1, ol2
                poly1.loc[poly1['poly1_idx'] == p1, ['comp_idx', 'Relation']] = comp, rel
            for p2 in p2_set:
                poly2.loc[poly2['poly2_idx'] == p2, ['iou_11', 'ol_pl1_11', 'ol_pl2_11']] = iou, ol1, ol2
                poly2.loc[poly2['poly2_idx'] == p2, ['comp_idx', 'Relation']] = comp, rel

    # 1:0, 0:1 관계도 comp_idx, Relation 넣어주기
    null_combis = combi_df[combi_df['combi'].isna()]
    for _, row in null_combis.iterrows():
        rel = row['Relation']
        comp = row['comp_idx']
        p1_set = row['poly1_set']
        p2_set = row['poly2_set']

        if rel == '1:0':
            for p1 in p1_set:
                if not pd.isna(p1):
                    poly1.loc[poly1['poly1_idx'] == p1, ['comp_idx', 'Relation']] = comp, rel
        elif rel == '0:1':
            for p2 in p2_set:
                if not pd.isna(p2):
                    poly2.loc[poly2['poly2_idx'] == p2, ['comp_idx', 'Relation']] = comp, rel

    # 열 순서 재정렬
    def reorder_columns(df):
        metric_cols_ordered = [
            'Relation', 'comp_idx',
            'iou_nn', 'ol_pl1_nn', 'ol_pl2_nn',
            'iou_1n', 'ol_pl1_1n', 'ol_pl2_1n',
            'iou_n1', 'ol_pl1_n1', 'ol_pl2_n1',
            'iou_11', 'ol_pl1_11', 'ol_pl2_11',
        ]
        cols = df.columns.tolist()
        geometry_col = 'geometry' if 'geometry' in cols else None
        others = [c for c in cols if c not in metric_cols_ordered + [geometry_col]]
        ordered = others + metric_cols_ordered
        if geometry_col:
            ordered += [geometry_col]
        return df[ordered]

    poly1 = reorder_columns(poly1)
    poly2 = reorder_columns(poly2)

    return poly1, poly2


def add_component_sets_to_polys(poly1, poly2, components_dict):
    poly1 = poly1.copy()
    poly2 = poly2.copy()

    # 새로운 열 초기화
    poly1['poly1_set'] = None
    poly1['poly2_set'] = None
    poly2['poly1_set'] = None
    poly2['poly2_set'] = None

    # poly1에 붙이기
    for idx, row in poly1.iterrows():
        p1_id = row['poly1_idx']
        for comp in components_dict.values():
            if p1_id in comp['poly1_set']:
                poly1.at[idx, 'poly1_set'] = comp['poly1_set']
                poly1.at[idx, 'poly2_set'] = comp['poly2_set']
                break  # 하나의 component만 매칭되므로 break

    # poly2에 붙이기
    for idx, row in poly2.iterrows():
        p2_id = row['poly2_idx']
        for comp in components_dict.values():
            if p2_id in comp['poly2_set']:
                poly2.at[idx, 'poly1_set'] = comp['poly1_set']
                poly2.at[idx, 'poly2_set'] = comp['poly2_set']
                break

    # 열 순서 정리: comp_idx 다음에 poly1_set, poly2_set 붙이기
    def insert_after(df, after_col, insert_cols):
        cols = df.columns.tolist()
        idx = cols.index(after_col) + 1
        for col in insert_cols:
            if col in cols:
                cols.remove(col)
        for i, col in enumerate(insert_cols):
            cols.insert(idx + i, col)
        return df[cols]

    poly1 = insert_after(poly1, 'comp_idx', ['poly1_set', 'poly2_set'])
    poly2 = insert_after(poly2, 'comp_idx', ['poly1_set', 'poly2_set'])

    return poly1, poly2


def assign_class_10(poly, prefix="cd"):
    """
    Relation과 {prefix}_class를 바탕으로 class_10 그룹을 지정하는 함수.
    예: prefix="cd" → cd_class, cd_class_10 열 생성
    """
    class_col = f"{prefix}_class"
    class10_col = "class_10"

    def get_class(row):
        rel = row.get("Relation")
        cls = row.get(class_col)

        if rel == "1:0" and cls == "소멸":
            return "소멸"
        elif rel == "0:1" and cls == "신축":
            return "신축"
        elif rel == "1:1" and cls == "갱신":
            return "1:1 갱신"
        elif rel == "1:1" and cls == "변화없음":
            return "1:1 변화없음"
        elif rel == "1:N" and cls == "변화없음":
            return "1:N 변화없음"
        elif rel == "1:N" and cls == "갱신":
            return "1:N 갱신"
        elif rel == "N:1" and cls == "변화없음":
            return "N:1 변화없음"
        elif rel == "N:1" and cls == "갱신":
            return "N:1 갱신"
        elif rel == "N:N" and cls == "변화없음":
            return "N:N 변화없음"
        elif rel == "N:N" and cls == "갱신":
            return "N:N 갱신"
        else:
            return None  # 기타 처리 안 된 경우

    poly = poly.copy()
    poly[class10_col] = poly.apply(get_class, axis=1)

    relation_loc = poly.columns.get_loc("Relation")
    reordered = poly.pop(class10_col)
    poly.insert(loc=relation_loc + 1, column=class10_col, value=reordered)

    return poly


def assign_cd_class(poly, threshold, prefix="cd"):
    class_col_name = f"{prefix}_class"  # 자동으로 열 이름 생성

    cd_class = np.full(len(poly), np.nan, dtype=object)

    cd_class[np.where(poly['Relation'] == '0:1')[0]] = '신축'
    cd_class[np.where(poly['Relation'] == '1:0')[0]] = '소멸'

    cd_class[np.where((poly['Relation'] == '1:1') & (poly['iou_nn'] > threshold))[0]] = '변화없음'
    cd_class[np.where((poly['Relation'] == '1:1') & (poly['iou_nn'] <= threshold))[0]] = '갱신'

    cd_class[np.where((poly['Relation'] == '1:N') & (poly['iou_n1'] > threshold))[0]] = '변화없음'
    cd_class[np.where((poly['Relation'] == '1:N') & (poly['iou_n1'] <= threshold))[0]] = '갱신'

    cd_class[np.where((poly['Relation'] == 'N:1') & (poly['iou_1n'] > threshold))[0]] = '변화없음'
    cd_class[np.where((poly['Relation'] == 'N:1') & (poly['iou_1n'] <= threshold))[0]] = '갱신'

    cd_class[np.where((poly['Relation'] == 'N:N') & (poly['iou_11'] > threshold))[0]] = '변화없음'
    cd_class[np.where((poly['Relation'] == 'N:N') & (poly['iou_11'] <= threshold))[0]] = '갱신'

    if class_col_name in poly.columns:
        poly = poly.drop(columns=[class_col_name])

    relation_loc = poly.columns.get_loc('Relation')
    poly.insert(loc=relation_loc + 1, column=class_col_name, value=cd_class)

    return poly


def mark_cut_links(poly1, poly2, cut_links):
    cut_poly1_idxs = set(int(link["source"].replace("p1_", "")) for link in cut_links if link["source"].startswith("p1_"))
    cut_poly2_idxs = set(int(link["target"].replace("p2_", "")) for link in cut_links if link["target"].startswith("p2_"))

    poly1 = poly1.copy()
    poly2 = poly2.copy()

    poly1["cut_link"] = poly1["poly1_idx"].isin(cut_poly1_idxs)
    poly2["cut_link"] = poly2["poly2_idx"].isin(cut_poly2_idxs)

    return poly1, poly2


def outer_join(poly1, poly2, poly1_prefix="poly1", poly2_prefix="poly2"):
    left_join = gpd.sjoin(poly1, poly2, how='left', predicate='intersects')
    right_join = gpd.sjoin(poly2, poly1, how='left', predicate='intersects')
    left_join.columns = [
        col.replace('_left', '_poly1').replace('_right', '_poly2')
        for col in left_join.columns
    ]

    right_join.columns = [
        col.replace('_left', '_poly2').replace('_right', '_poly1')
        for col in right_join.columns
    ]

    joined = pd.merge(left_join, right_join, how='outer', on=list(set(left_join.columns) & set(right_join.columns)))
    subset_cols = [f"{poly1_prefix}_idx", f"{poly2_prefix}_idx"]
    joined = joined.drop_duplicates(subset=subset_cols)
    joined = joined.reset_index(drop=True)
    return joined


def assign_bd_class_gt(poly, threshold):
    bd_class = np.full(len(poly), np.nan, dtype=object)

    # 2. 조건별 분류
    bd_class[np.where(poly['Relation'] == '1:0')[0]] = 'FN'

    bd_class[np.where((poly['Relation'] == '1:1') & (poly['ol_pl1_nn'] > threshold))[0]] = 'TP'
    bd_class[np.where((poly['Relation'] == '1:1') & (poly['ol_pl1_nn'] <= threshold))[0]] = 'FN'

    bd_class[np.where((poly['Relation'] == '1:N') & (poly['ol_pl1_n1'] > threshold))[0]] = 'TP'
    bd_class[np.where((poly['Relation'] == '1:N') & (poly['ol_pl1_n1'] <= threshold))[0]] = 'FN'

    bd_class[np.where((poly['Relation'] == 'N:1') & (poly['ol_pl1_1n'] > threshold))[0]] = 'TP'
    bd_class[np.where((poly['Relation'] == 'N:1') & (poly['ol_pl1_1n'] <= threshold))[0]] = 'FN'

    bd_class[np.where((poly['Relation'] == 'N:N') & (poly['ol_pl1_11'] > threshold))[0]] = 'TP'
    bd_class[np.where((poly['Relation'] == 'N:N') & (poly['ol_pl1_11'] <= threshold))[0]] = 'FN'

    if 'bd_class' in poly.columns:
        poly = poly.drop(columns=['bd_class'])

    relation_loc = poly.columns.get_loc('Relation')
    poly.insert(loc=relation_loc + 1, column='bd_class', value=bd_class)
    return poly


def assign_bd_class_seg(poly, threshold):
    bd_class = np.full(len(poly), np.nan, dtype=object)

    # 2. 조건별 분류
    bd_class[np.where(poly['Relation'] == '0:1')[0]] = 'FP'

    bd_class[np.where((poly['Relation'] == '1:1') & (poly['ol_pl1_nn'] > threshold))[0]] = 'TP'
    bd_class[np.where((poly['Relation'] == '1:1') & (poly['ol_pl1_nn'] <= threshold))[0]] = 'FP'

    bd_class[np.where((poly['Relation'] == '1:N') & (poly['ol_pl1_n1'] > threshold))[0]] = 'TP'
    bd_class[np.where((poly['Relation'] == '1:N') & (poly['ol_pl1_n1'] <= threshold))[0]] = 'FP'

    bd_class[np.where((poly['Relation'] == 'N:1') & (poly['ol_pl1_1n'] > threshold))[0]] = 'TP'
    bd_class[np.where((poly['Relation'] == 'N:1') & (poly['ol_pl1_1n'] <= threshold))[0]] = 'FP'

    bd_class[np.where((poly['Relation'] == 'N:N') & (poly['ol_pl1_11'] > threshold))[0]] = 'TP'
    bd_class[np.where((poly['Relation'] == 'N:N') & (poly['ol_pl1_11'] <= threshold))[0]] = 'FP'

    if 'bd_class' in poly.columns:
        poly = poly.drop(columns=['bd_class'])

    relation_loc = poly.columns.get_loc('Relation')
    poly.insert(loc=relation_loc + 1, column='bd_class', value=bd_class)
    return poly


def assign_class_bd_10(poly, prefix="bd"):
    """
    Relation과 {prefix}_class를 바탕으로 class_10 그룹을 지정하는 함수.
    예: prefix="cd" → cd_class, cd_class_10 열 생성
    """
    class_col = f"{prefix}_class"
    class10_col = "cls_10"

    def get_class(row):
        rel = row.get("Relation")
        cls = row.get(class_col)

        if rel == "1:0" and cls == "FN":
            return "FN"
        elif rel == "0:1" and cls == "FP":
            return "FP"
        elif rel == "1:1" and cls == "FN":
            return "1:1 FN"
        elif rel == "1:1" and cls == "FP":
            return "1:1 FP"
        elif rel == "1:1" and cls == "TP":
            return "1:1 TP"
        elif rel == "1:N" and cls == "FN":
            return "1:N FN"
        elif rel == "1:N" and cls == "FP":
            return "1:N FP"
        elif rel == "1:N" and cls == "TP":
            return "1:N TP"
        elif rel == "N:1" and cls == "FN":
            return "N:1 FN"
        elif rel == "N:1" and cls == "FP":
            return "N:1 FP"
        elif rel == "N:1" and cls == "TP":
            return "N:1 TP"
        elif rel == "N:N" and cls == "FN":
            return "N:N FN"
        elif rel == "N:N" and cls == "FP":
            return "N:N FP"
        elif rel == "N:N" and cls == "TP":
            return "N:N TP"
        else:
            return None  # 기타 처리 안 된 경우

    poly = poly.copy()
    poly[class10_col] = poly.apply(get_class, axis=1)

    relation_loc = poly.columns.get_loc("Relation")
    reordered = poly.pop(class10_col)
    poly.insert(loc=relation_loc + 1, column=class10_col, value=reordered)

    return poly