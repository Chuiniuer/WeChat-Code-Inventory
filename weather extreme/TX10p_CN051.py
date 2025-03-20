import os
import numpy as np
import rasterio
from tqdm import tqdm
from datetime import datetime

# 输入数据路径（tmax）
data_dir = r"F:\QTP_CN05.1_converted\tmax"
txin10_file = r"F:\climate extremes\TX10p\threshold\TXin10.tif"
output_dir = r"F:\climate extremes\TX10p\yearly"

# 目标基准期
start_year, end_year = 1961, 2014

# 确保输出目录存在
os.makedirs(output_dir, exist_ok=True)

# 读取 TXin10（基准期第 10 百分位数）
with rasterio.open(txin10_file) as src:
    txin10 = src.read()  # 读取所有 366 天的 10 百分位数
    meta = src.meta.copy()  # 复制元数据
    meta.update({"count": 1, "dtype": "float32", "compress": "lzw"})  # 适配单波段输出

# 计算每年的 TX10p
for year in tqdm(range(start_year, end_year + 1), desc="Computing TX10p"):
    input_file = os.path.join(data_dir, f"tmax_{year}.tif")

    # 读取该年的最高温数据
    with rasterio.open(input_file) as src:
        num_days = src.count  # 该年的天数（365 或 366）
        tx10p = np.zeros((src.height, src.width), dtype=np.float32)  # 初始化 TX10p 计数数组
        valid_pixel_count = np.zeros((src.height, src.width), dtype=np.float32)  # 统计有效天数
        nan_mask = np.zeros((src.height, src.width), dtype=bool)  # 记录哪些像元应该是 NaN

        for band in range(1, num_days + 1):  # 1-based index
            date_str = src.descriptions[band - 1]  # 读取日期
            _, month, day = map(int, date_str.split("-"))
            day_of_year = (datetime(year, month, day) - datetime(year, 1, 1)).days  # 0-based

            data = src.read(band)  # 读取该天的数据
            invalid_mask = np.isnan(data)  # 无效值掩码
            nan_mask |= invalid_mask  # 记录该像元是否为无效值

            # 计算 TX10p
            tx10p += (data < txin10[day_of_year]).astype(np.float32)  # 低于 TXin10 计数
            valid_pixel_count += (~invalid_mask).astype(np.float32)  # 统计有效天数

        # 计算最终百分比
        valid_mask = valid_pixel_count > 0  # 仅在有数据的像元计算
        tx10p[valid_mask] /= valid_pixel_count[valid_mask]  # 计算 TX10p 百分比
        tx10p[~valid_mask] = np.nan  # 保持无效区域为 NaN

        # 调试输出
        print(f"Year {year}: Valid pixels count min={valid_pixel_count.min()}, max={valid_pixel_count.max()}")

    # 输出 TX10p 结果
    output_file = os.path.join(output_dir, f"TX10p_{year}.tif")
    with rasterio.open(output_file, "w", **meta) as dst:
        dst.write(tx10p, 1)  # 写入单波段
        dst.set_band_description(1, f"TX10p_{year}")

print("TX10p calculation completed. Results saved to:", output_dir)
