import os
import geopandas as gpd

# ✅ {region} 리스트 (이미지에서 가져온 텍스트 리스트)
regions = ["gangseo", "junggu", "jungrang", "mapo", "seocho", "songpa", "suseo", "yangcheon", "youngdeungpo"]

# ✅ 경로 템플릿
a_template = r"D:\DT\UOS\UOS\True_Ortho_Image\output\{region}_Drone_Image_2022"
b_template = r"D:\DT\UOS\UOS\DT\Data\4. refined building detection result(shp)\{region}\2022"
output_template = r"D:\DT\UOS\UOS\DT\Data\re_refined building detection result(shp)\{region}\2022"

# ✅ 모든 지역 반복 처리
for region in regions:
    # 폴더 경로 설정
    a_folder = a_template.format(region=region)
    b_folder = b_template.format(region=region)
    output_folder = output_template.format(region=region)

    # 결과 저장할 폴더가 없으면 생성
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # ✅ A와 B에서 .shp 파일 찾기
    a_files = [f for f in os.listdir(a_folder) if f.lower().endswith(".shp")] if os.path.exists(a_folder) else []
    b_files = [f for f in os.listdir(b_folder) if f.lower().endswith(".shp")] if os.path.exists(b_folder) else []

    if not a_files or not b_files:
        print(f"⚠️ {region}: Shapefile이 존재하지 않아 건너뜁니다.")
        continue

    a_shp = os.path.join(a_folder, a_files[0])  # 첫 번째 Shapefile 선택
    b_shp = os.path.join(b_folder, b_files[0])  # 첫 번째 Shapefile 선택
    output_shp = os.path.join(output_folder, f"{region}_cleaned.shp")  # 저장할 파일명

    print(f"🔹 처리 중: {region} ...")

    # ✅ A와 B 불러오기
    A = gpd.read_file(a_shp)
    B = gpd.read_file(b_shp)

    # ✅ 좌표계 확인 및 일치시키기
    if A.crs != B.crs:
        B = B.to_crs(A.crs)

    # ✅ A와 B의 공간 조인 수행 (겹치는 폴리곤 찾기)
    joined = B.sjoin(A, how="inner", predicate="intersects")

    # ✅ B 폴리곤별로 A와의 겹치는 영역 계산
    intersection_areas = joined.intersection(A.unary_union)  # A와 B의 교차 영역
    overlap_ratio = intersection_areas.area / joined.area  # B 기준 오버랩 비율

    # ✅ 10% 이상 겹치는 경우 제거
    joined["overlap_ratio"] = overlap_ratio
    to_remove = joined[joined["overlap_ratio"] >= 0.1].index  # 10% 이상 겹치는 폴리곤 인덱스

    # ✅ B에서 10% 이상 겹치는 폴리곤만 제거
    B_cleaned = B.drop(to_remove)

    # ✅ 새로운 Shapefile로 저장
    B_cleaned.to_file(output_shp, driver="ESRI Shapefile")

    print(f"✅ 완료: {region} → {output_shp}")

print("🎉 모든 지역 처리가 완료되었습니다!")
