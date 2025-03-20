import os
import numpy as np
import rasterio
from tqdm import tqdm

# 📂 目录设置
pre_dir = r"F:\QTP_CN05.1_converted\pre"  # 降水数据目录
output_dir = r"F:\climate extremes\PRCPTOT"  # 结果输出目录
os.makedirs(output_dir, exist_ok=True)

# **计算 1961-2014 年的 PRCPTOT**
all_years = range(1961, 2014 + 1)

print("Computing PRCPTOT (annual total precipitation on wet days)...")
for year in tqdm(all_years):
    input_file = os.path.join(pre_dir, f"pre_{year}.tif")
    output_file = os.path.join(output_dir, f"PRCPTOT_{year}.tif")

    if not os.path.exists(input_file):
        print(f"Warning: {input_file} not found, skipping...")
        continue

    with rasterio.open(input_file) as src:
        meta = src.meta.copy()
        meta.update({"count": 1, "dtype": "float32", "compress": "lzw", "nodata": np.nan})  # 设定输出 nodata 为 NaN

        data = src.read().astype(np.float32)  # 读取所有天 (days, height, width)

        # **识别无效值区域**
        invalid_mask = np.isnan(data)

        # **湿日（降水 ≥ 1 mm）**
        wet_mask = data >= 1

        # **计算 PRCPTOT（所有湿日的降水总量）**
        prcptot = np.nansum(np.where(wet_mask, data, 0), axis=0).astype(np.float32)  # (height, width)

        # **保持无效区域为 NaN**
        prcptot[invalid_mask[0]] = np.nan

        # **保存 PRCPTOT 结果**
        with rasterio.open(output_file, "w", **meta) as dst:
            dst.write(prcptot, 1)
            dst.set_band_description(1, f"PRCPTOT_{year}")

print("✅ PRCPTOT computation (1961-2014) completed. Results saved to:", output_dir)
