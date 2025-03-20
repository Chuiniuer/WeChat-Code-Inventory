import os
import numpy as np
import rasterio
from tqdm import tqdm

# 输入数据路径
data_dir = r"F:\QTP_CN05.1_converted\pre"
output_dir_rx1 = r"F:\climate extremes\RX1day"
output_dir_rx5 = r"F:\climate extremes\RX5day"

# 确保输出目录存在
os.makedirs(output_dir_rx1, exist_ok=True)
os.makedirs(output_dir_rx5, exist_ok=True)

# 目标计算年份
start_year, end_year = 1961, 2014

# 计算每年的 RX1day 和 RX5day
for year in tqdm(range(start_year, end_year + 1), desc="Computing RX1day & RX5day"):
    input_file = os.path.join(data_dir, f"pre_{year}.tif")

    with rasterio.open(input_file) as src:
        num_days = src.count  # 该年的天数（365 或 366）
        meta = src.meta.copy()
        meta.update({"count": 1, "dtype": "float32", "compress": "lzw"})  # 单波段输出

        # 读取所有日降水数据
        pre_data = src.read().astype(np.float32)  # 形状 (num_days, height, width)
        nan_mask = np.isnan(pre_data[0])  # 记录无效值区域

        # 计算 RX1day（最大日降水量）
        rx1day = np.nanmax(pre_data, axis=0)
        rx1day[nan_mask] = np.nan  # 处理无效值

        # 计算 RX5day（5 天滑动窗口累计降水量的最大值）
        rx5day = np.full_like(rx1day, np.nan, dtype=np.float32)  # 初始化 RX5day
        for d in range(num_days - 4):  # 仅能滑动到倒数第 5 天
            window_sum = np.nansum(pre_data[d:d+5], axis=0)  # 计算 5 天累积降水
            rx5day = np.nanmax(np.stack([rx5day, window_sum]), axis=0)  # 逐步取最大值
        rx5day[nan_mask] = np.nan  # 处理无效值

    # 保存 RX1day
    output_file_rx1 = os.path.join(output_dir_rx1, f"RX1day_{year}.tif")
    with rasterio.open(output_file_rx1, "w", **meta) as dst:
        dst.write(rx1day, 1)
        dst.set_band_description(1, f"RX1day_{year}")

    # 保存 RX5day
    output_file_rx5 = os.path.join(output_dir_rx5, f"RX5day_{year}.tif")
    with rasterio.open(output_file_rx5, "w", **meta) as dst:
        dst.write(rx5day, 1)
        dst.set_band_description(1, f"RX5day_{year}")

print("RX1day & RX5day calculation completed. Results saved.")
