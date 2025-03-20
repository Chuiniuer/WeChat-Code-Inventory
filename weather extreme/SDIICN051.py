import os
import numpy as np
import rasterio
from tqdm import tqdm

# 输入降水数据目录
pre_dir = r"F:\QTP_CN05.1_converted\pre"
# 输出 SDII 目录
output_dir = r"F:\climate extremes\SDII"
os.makedirs(output_dir, exist_ok=True)

# 处理的年份范围
start_year, end_year = 1961, 2014  # 适当调整

# 遍历每年的数据
for year in tqdm(range(start_year, end_year + 1), desc="Computing SDII"):
    input_file = os.path.join(pre_dir, f"pre_{year}.tif")
    output_file = os.path.join(output_dir, f"SDII_{year}.tif")

    if not os.path.exists(input_file):
        print(f"Warning: {input_file} not found, skipping...")
        continue

    with rasterio.open(input_file) as src:
        meta = src.meta.copy()
        meta.update({"count": 1, "dtype": "float32", "compress": "lzw"})  # 适配单波段输出

        total_precip = np.zeros((src.height, src.width), dtype=np.float32)
        wet_days = np.zeros((src.height, src.width), dtype=np.int32)

        # 逐天计算
        for band in range(1, src.count + 1):
            data = src.read(band)
            mask = data >= 1  # 计算湿日（降水 ≥ 1 mm）
            total_precip += np.where(mask, data, 0)  # 仅累加湿日降水量
            wet_days += mask  # 计算湿日天数

        # 计算 SDII，避免除以 0
        sdii = np.where(wet_days > 0, total_precip / wet_days, np.nan)

        # 保存 SDII 结果
        with rasterio.open(output_file, "w", **meta) as dst:
            dst.write(sdii, 1)
            dst.set_band_description(1, f"SDII_{year}")

print("SDII calculation completed. Results saved to:", output_dir)
