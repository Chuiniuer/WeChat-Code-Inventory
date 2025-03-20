import os
import numpy as np
import rasterio
from tqdm import tqdm

# 输入降水数据目录
pre_dir = r"F:\QTP_CN05.1_converted\pre"
# 输出目录
output_dir_r1mm = r"F:\climate extremes\R1mm"
output_dir_r10mm = r"F:\climate extremes\R10mm"
os.makedirs(output_dir_r1mm, exist_ok=True)
os.makedirs(output_dir_r10mm, exist_ok=True)

# 处理的年份范围（仅 1961-2014）
start_year, end_year = 1961, 2014

# 遍历每年的数据
for year in tqdm(range(start_year, end_year + 1), desc="Computing R1mm & R10mm"):
    input_file = os.path.join(pre_dir, f"pre_{year}.tif")
    output_file_r1mm = os.path.join(output_dir_r1mm, f"R1mm_{year}.tif")
    output_file_r10mm = os.path.join(output_dir_r10mm, f"R10mm_{year}.tif")

    if not os.path.exists(input_file):
        print(f"Warning: {input_file} not found, skipping...")
        continue

    with rasterio.open(input_file) as src:
        meta = src.meta.copy()
        meta.update({"count": 1, "dtype": "float32", "compress": "lzw"})  # 适配单波段输出

        r1mm_days = np.zeros((src.height, src.width), dtype=np.float32)  # 初始化为 0
        r10mm_days = np.zeros((src.height, src.width), dtype=np.float32)  # 初始化为 0

        # 逐天计算
        for band in range(1, src.count + 1):
            data = src.read(band)

            # 只统计非 NaN 区域
            valid_mask = ~np.isnan(data)
            r1mm_days[valid_mask] += (data[valid_mask] >= 1).astype(np.float32)   # 计算湿日数
            r10mm_days[valid_mask] += (data[valid_mask] >= 10).astype(np.float32)  # 计算大雨日数

        # 处理 NaN 值
        r1mm_days[~valid_mask] = np.nan
        r10mm_days[~valid_mask] = np.nan

        # 保存 R1mm 结果
        with rasterio.open(output_file_r1mm, "w", **meta) as dst:
            dst.write(r1mm_days, 1)
            dst.set_band_description(1, f"R1mm_{year}")

        # 保存 R10mm 结果
        with rasterio.open(output_file_r10mm, "w", **meta) as dst:
            dst.write(r10mm_days, 1)
            dst.set_band_description(1, f"R10mm_{year}")

print("R1mm & R10mm calculation completed for 1961-2014. Results saved to respective folders.")
