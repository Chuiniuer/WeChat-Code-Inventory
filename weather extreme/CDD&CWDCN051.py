import os
import numpy as np
import rasterio
from tqdm import tqdm

# 输入降水数据目录
pre_dir = r"F:\QTP_CN05.1_converted\pre"
# 输出目录
output_dir_cdd = r"F:\climate extremes\CDD"
output_dir_cwd = r"F:\climate extremes\CWD"
os.makedirs(output_dir_cdd, exist_ok=True)
os.makedirs(output_dir_cwd, exist_ok=True)

# 处理的年份范围（仅 1961-2014）
start_year, end_year = 1961, 2014

# 遍历每年的数据
for year in tqdm(range(start_year, end_year + 1), desc="Computing CDD & CWD"):
    input_file = os.path.join(pre_dir, f"pre_{year}.tif")
    output_file_cdd = os.path.join(output_dir_cdd, f"CDD_{year}.tif")
    output_file_cwd = os.path.join(output_dir_cwd, f"CWD_{year}.tif")

    if not os.path.exists(input_file):
        print(f"Warning: {input_file} not found, skipping...")
        continue

    with rasterio.open(input_file) as src:
        meta = src.meta.copy()
        meta.update({"count": 1, "dtype": "float32", "compress": "lzw"})  # 适配单波段输出

        cdd_max = np.zeros((src.height, src.width), dtype=np.float32)  # 最长干旱日数
        cwd_max = np.zeros((src.height, src.width), dtype=np.float32)  # 最长湿日数

        # 读取所有日降水数据
        precip_data = src.read()  # 形状为 (days, height, width)

        # 遍历每个像素
        for i in range(src.height):
            for j in range(src.width):
                pixel_precip = precip_data[:, i, j]

                if np.all(np.isnan(pixel_precip)):  # 跳过无效数据
                    cdd_max[i, j] = np.nan
                    cwd_max[i, j] = np.nan
                    continue

                # 计算 CDD（最长连续 <1 mm）
                cdd_count = 0
                max_cdd = 0
                cwd_count = 0
                max_cwd = 0

                for day in range(len(pixel_precip)):
                    if pixel_precip[day] < 1:
                        cdd_count += 1
                        max_cdd = max(max_cdd, cdd_count)
                        cwd_count = 0  # 断开湿日计数
                    else:
                        cwd_count += 1
                        max_cwd = max(max_cwd, cwd_count)
                        cdd_count = 0  # 断开干旱日计数

                cdd_max[i, j] = max_cdd
                cwd_max[i, j] = max_cwd

        # 保存 CDD 结果
        with rasterio.open(output_file_cdd, "w", **meta) as dst:
            dst.write(cdd_max, 1)
            dst.set_band_description(1, f"CDD_{year}")

        # 保存 CWD 结果
        with rasterio.open(output_file_cwd, "w", **meta) as dst:
            dst.write(cwd_max, 1)
            dst.set_band_description(1, f"CWD_{year}")

print("CDD & CWD calculation completed for 1961-2014. Results saved to respective folders.")
