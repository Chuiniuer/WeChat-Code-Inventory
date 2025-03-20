import os
import numpy as np
import rasterio
from tqdm import tqdm
from datetime import datetime

# 输入数据路径
data_dir = r"F:\QTP_CN05.1_converted\tmax"
output_file = r"F:\climate extremes\TX90p\threshold\TXin90.tif"

# 目标基准期
start_year, end_year = 1961, 2014

# 确保输出目录存在
os.makedirs(os.path.dirname(output_file), exist_ok=True)

# 解析所有 GeoTIFF 文件路径
tif_files = [os.path.join(data_dir, f"tmax_{year}.tif") for year in range(start_year, end_year + 1)]

# 读取第一个文件以获取地理参考信息
with rasterio.open(tif_files[0]) as src:
    meta = src.meta.copy()  # 复制元数据
    height, width = src.height, src.width  # 栅格尺寸
    transform = src.transform  # 仿射变换
    crs = src.crs  # 坐标参考系

# 366 天数组（存储 TXin90）
txin90 = np.full((366, height, width), np.nan, dtype=np.float32)

# 读取所有数据并按日历日整理
all_data = {d: [] for d in range(366)}

for year, file in tqdm(zip(range(start_year, end_year + 1), tif_files), desc="Reading Data", total=len(tif_files)):
    with rasterio.open(file) as src:
        num_days = src.count  # 获取该年的天数（365 或 366）

        for band in range(1, num_days + 1):  # 1-based index in rasterio
            date_str = src.descriptions[band - 1]  # 读取日期，如 "1961-01-01"
            year, month, day = map(int, date_str.split("-"))
            day_of_year = (datetime(year, month, day) - datetime(year, 1, 1)).days  # 0-based

            data = src.read(band)  # 读取波段数据
            all_data[day_of_year].append(data)

# 计算 90 百分位数（使用 5 天滑动窗口）
for day in tqdm(range(366), desc="Computing TXin90"):
    window_data = []

    # 取 5 天滑动窗口的数据
    for offset in range(-2, 3):
        day_idx = (day + offset) % 366  # 确保循环计算
        window_data.extend(all_data[day_idx])

    if window_data:  # 避免空数据计算
        window_stack = np.stack(window_data, axis=0)
        txin90[day] = np.percentile(window_stack, 90, axis=0)

# 更新元数据以适应 366 天
meta.update({"count": 366, "dtype": "float32", "compress": "lzw"})

# 保存 TXin90 结果为 GeoTIFF
with rasterio.open(output_file, "w", **meta) as dst:
    for day in range(366):
        dst.write(txin90[day], day + 1)  # 1-based index
        dst.set_band_description(day + 1, f"Day-{day + 1}")

print("TXin90 calculation completed. Output saved to:", output_file)
