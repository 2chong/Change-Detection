import pandas as pd
import os

# 🔹 지역 리스트
regions = ['gangseo', 'dongjak', 'jungnang', 'jongno', 'junggu', 'yongsan', 'seodaemun', 'mapo', 'seocho']

# 🔹 기본 경로
base_dir = './Data/building/evaluation/evaluation result/evaluation of building detection'

# 🔹 모든 파일을 담을 리스트
all_dfs = []

for region in regions:
    file_path = os.path.join(base_dir, region, '2022', 'bd_anl_result.csv')
    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
        df['region'] = region  # 🔸 어디 지역인지 표시
        all_dfs.append(df)
    else:
        print(f"❌ {region} 파일 없음: {file_path}")

# 🔸 데이터 이어붙이기 (concat)
concat_df = pd.concat(all_dfs, ignore_index=True)

# 🔸 값 합치기 (class 열 기준)
sum_df = concat_df.groupby('class', as_index=False).sum(numeric_only=True)

# 🔸 파일 저장
output_path = os.path.join(base_dir, 'output.csv')
sum_output_path = os.path.join(base_dir, 'output_sum.csv')

concat_df.to_csv(output_path, index=False)
sum_df.to_csv(sum_output_path, index=False)

print("✅ 파일 저장 완료")
