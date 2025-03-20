import os
import numpy as np
import rasterio
from tqdm import tqdm

# 输入降水数据目录
pre_dir = r"F:\QTP_CN05.1_converted\pre"
# 输出 PRwn95 目录
output_dir = r"F:\climate extremes\PRwn95"
os.makedirs(output_dir, exist_ok=True)

# 基准期 1961-2014
start_year, end_year = 1961, 2014

# 初始化湿日降水数据列表
wet_days_data = []

# 读取基准期所有数据
for year in tqdm(range(start_year, end_year + 1), desc="Collecting wet day precipitation"):
    input_file = os.path.join(pre_dir, f"pre_{year}.tif")

    if not os.path.exists(input_file):
        print(f"Warning: {input_file} not found, skipping...")
        continue

    with rasterio.open(input_file) as src:
        precip_data = src.read()  # 形状 (days, height, width)
        wet_mask = precip_data >= 1  # 选出湿日（降水量 ≥ 1 mm）
        wet_precip = np.where(wet_mask, precip_data, np.nan)  # 仅保留湿日降水量

        wet_days_data.append(wet_precip)

# 叠加所有湿日数据
wet_days_data = np.concatenate(wet_days_data, axis=0)  # (days_total, height, width)

# 计算湿日降水量的 95% 百分位数
prwn95 = np.nanpercentile(wet_days_data, 95, axis=0)

# 读取任意一年数据作为模板
template_year = 1961
template_file = os.path.join(pre_dir, f"pre_{template_year}.tif")
with rasterio.open(template_file) as src:
    meta = src.meta.copy()
    meta.update({"count": 1, "dtype": "float32", "compress": "lzw"})  # 单波段输出

# 保存 PRwn95 结果
output_file = os.path.join(output_dir, "PRwn95_1961-2014.tif")
with rasterio.open(output_file, "w", **meta) as dst:
    dst.write(prwn95, 1)
    dst.set_band_description(1, "PRwn95 (1961-2014)")

print("PRwn95 calculation completed. Result saved to:", output_file)
