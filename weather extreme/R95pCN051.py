import os
import numpy as np
import rasterio
from tqdm import tqdm

# 📂 目录设置
pre_dir = r"F:\QTP_CN05.1_converted\pre"  # 降水数据目录
output_dir = r"F:\climate extremes\R95p"  # 结果输出目录
os.makedirs(output_dir, exist_ok=True)
prwn95_file = r"F:\climate extremes\PRwn95\PRwn95_1961-2014.tif"  # 已计算的 PRwn95 文件


# **加载 PRwn95**
with rasterio.open(prwn95_file) as src:
    prwn95 = src.read(1).astype(np.float32)  # (height, width)
    prwn95_meta = src.meta.copy()
    nodata_value = src.nodata  # 读取原始 NoData 值

# **计算 1961-2014 年的 R95p**
all_years = range(1961, 2014 + 1)  # 仅计算基准期 1961-2014

print("Computing R95p (annual total precipitation above PRwn95)...")
for year in tqdm(all_years):
    input_file = os.path.join(pre_dir, f"pre_{year}.tif")
    output_file = os.path.join(output_dir, f"R95p_{year}.tif")

    if not os.path.exists(input_file):
        print(f"Warning: {input_file} not found, skipping...")
        continue

    with rasterio.open(input_file) as src:
        meta = src.meta.copy()
        meta.update({"count": 1, "dtype": "float32", "compress": "lzw", "nodata": np.nan})  # 设定输出 nodata 为 NaN

        data = src.read().astype(np.float32)  # 读取所有天 (days, height, width)

        # **识别无效值区域**
        invalid_mask = np.isnan(data)  # 记录无效值区域

        # **湿日（降水 ≥ 1 mm）**
        wet_mask = data >= 1

        # **计算超过 PRwn95 的降水量**
        extreme_precip = np.where((wet_mask) & (data > prwn95), data - prwn95, 0)

        # **无效值区域设为 NaN**
        extreme_precip[invalid_mask] = np.nan

        # **计算 R95p（所有超出 PRwn95 的降水量之和）**
        r95p = np.nansum(extreme_precip, axis=0).astype(np.float32)  # (height, width)

        # **无效值区域设为 NaN（最终检查）**
        r95p[np.isnan(prwn95)] = np.nan

        # **保存 R95p 结果**
        with rasterio.open(output_file, "w", **meta) as dst:
            dst.write(r95p, 1)
            dst.set_band_description(1, f"R95p_{year}")

print("✅ R95p computation (1961-2014) completed. Results saved to:", output_dir)
