import os
import numpy as np
import rasterio
from tqdm import tqdm

# 输入温度数据路径
tmean_dir = r"F:\QTP_CN05.1_converted\tmean"

# 输出文件夹
freeze_index_dir = r"F:\climate extremes\Freeze_Index"
thaw_index_dir = r"F:\climate extremes\Thaw_Index"

# 创建输出文件夹
os.makedirs(freeze_index_dir, exist_ok=True)
os.makedirs(thaw_index_dir, exist_ok=True)

# 目标基准期
start_year, end_year = 1961, 2014

# 计算冻结指数（FI）和融化指数（TI）
for year in tqdm(range(start_year, end_year + 1), desc="Computing Freeze and Thaw Index"):
    input_file = os.path.join(tmean_dir, f"tm_{year}.tif")

    # 读取数据
    with rasterio.open(input_file) as src:
        num_days = src.count
        meta = src.meta.copy()
        meta.update({"count": 1, "dtype": "float32", "compress": "lzw"})  # 适配单波段输出

        freeze_index = np.zeros((src.height, src.width), dtype=np.float32)
        thaw_index = np.zeros((src.height, src.width), dtype=np.float32)
        nan_mask = np.zeros((src.height, src.width), dtype=bool)

        for band in range(1, num_days + 1):
            data = src.read(band)
            nan_mask |= np.isnan(data)  # 记录无效值区域

            freeze_index += np.abs(data) * (data < 0)  # 冻结指数（负温度的绝对值累加）
            thaw_index += data * (data > 0)  # 融化指数（正温度累加）

        # 处理无效值
        freeze_index[nan_mask] = np.nan
        thaw_index[nan_mask] = np.nan

    # 输出冻结指数
    freeze_output_file = os.path.join(freeze_index_dir, f"Freeze_Index_{year}.tif")
    with rasterio.open(freeze_output_file, "w", **meta) as dst:
        dst.write(freeze_index, 1)
        dst.set_band_description(1, f"Freeze_Index_{year}")

    # 输出融化指数
    thaw_output_file = os.path.join(thaw_index_dir, f"Thaw_Index_{year}.tif")
    with rasterio.open(thaw_output_file, "w", **meta) as dst:
        dst.write(thaw_index, 1)
        dst.set_band_description(1, f"Thaw_Index_{year}")

print("冻结指数和融化指数计算完成，结果已保存。")
