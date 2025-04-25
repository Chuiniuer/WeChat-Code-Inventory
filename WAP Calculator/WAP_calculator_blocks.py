import os
import numpy as np
import rasterio
from rasterio.transform import Affine
from datetime import datetime, timedelta
from rasterio.windows import Window
import calendar
from tqdm import tqdm

def calculate_daily_wap(precipitation_data, a=0.9, max_n=44):
    """
    计算加权平均降水 (WAP)，严格遵循Lu (2009)公式
    
    参数：
    precipitation_data: 3D数组 (days, height, width)，日降水数据（mm）
    a: 衰减系数（默认0.9）
    max_n: 最大回溯天数（默认44）
    
    返回：
    daily_wap: 3D数组，每日WAP值
    """
    days, height, width = precipitation_data.shape
    daily_wap = np.zeros_like(precipitation_data, dtype=np.float32)
    
    # 生成权重：从当前日向过去衰减 [a^0, a^1, ..., a^44]
    weights = (1 - a) * (a ** np.arange(max_n + 1))  # 权重存储
    
    for day in range(days):
        n_back = min(day, max_n)
        # 取最近n_back+1天的数据（时间顺序：从旧到新）
        window_data = precipitation_data[day - n_back : day + 1]  # 形状 (n_back+1, H, W)
        # 对齐权重：最后n_back+1个权重（a^0最新，a^n_back最旧）
        daily_wap[day] = np.sum(weights[:n_back + 1][::-1][:, None, None] * window_data, axis=0)
    
    return daily_wap

if __name__ == "__main__":
    # 配置路径
    input_dir = r"P:\climate data\ERA5_land_total_precipitation_clipped"
    output_dir = r"P:\climate data\WAP_results"
    os.makedirs(output_dir, exist_ok=True)
    years = range(2010, 2021)

    # 1. 初始化（获取元数据和分块参数）
    with rasterio.open(os.path.join(input_dir, "era5-land-pr-2010.tif")) as src:
        meta = src.meta.copy()
        meta.update({'dtype': 'float32', 'nodata': np.nan})
        height, width = src.height, src.width

    # 2. 分块处理（每次处理64行）
    chunk_size = 64  # 根据内存调整
    for chunk_idx in tqdm(range((height + chunk_size - 1) // chunk_size), desc="处理分块"):
        row_start = chunk_idx * chunk_size
        row_end = min(row_start + chunk_size, height)
        window = Window(0, row_start, width, row_end - row_start)

        # 2.1 加载十年数据（当前块）
        precip_chunk = []
        for year in years:
            file_path = os.path.join(input_dir, f"era5-land-pr-{year}.tif")
            with rasterio.open(file_path) as src:
                data = src.read(window=window).astype(np.float32)
                data[data == -9999] = np.nan
                data /= 10.0  # 解除缩放
                precip_chunk.append(data)
        precip_stack = np.concatenate(precip_chunk, axis=0)  # (total_days, chunk_h, width)

        # 2.2 计算当前块的WAP
        wap_chunk = calculate_daily_wap(precip_stack)
        del precip_stack  # 立即释放内存

        # 2.3 按年写入结果
        day_counter = 0
        for year in years:
            with rasterio.open(os.path.join(input_dir, f"era5-land-pr-{year}.tif")) as src:
                n_days = src.count
            year_meta = meta.copy()
            year_meta.update({'count': n_days})  # 动态更新波段数

            output_path = os.path.join(output_dir, f"era5-land-wap-{year}.tif")
            with rasterio.open(output_path, 'w' if chunk_idx == 0 else 'r+', **year_meta) as dst:
                dst.write(
                    wap_chunk[day_counter : day_counter + n_days],
                    window=Window(0, row_start, width, row_end - row_start)
                )
            day_counter += n_days

    print("处理完成！结果已保存至:", output_dir)