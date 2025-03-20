import os
import numpy as np
import rasterio
from tqdm import tqdm

# 输入数据路径
tmax_dir = r"F:\QTP_CN05.1_converted\tmax"
tmin_dir = r"F:\QTP_CN05.1_converted\tmin"

# 输出目录
output_base_dir = r"F:\climate extremes"
output_dirs = {
    "TXx": os.path.join(output_base_dir, "TXx"),
    "TXn": os.path.join(output_base_dir, "TXn"),
    "TNx": os.path.join(output_base_dir, "TNx"),
    "TNn": os.path.join(output_base_dir, "TNn"),
}

# 确保每个输出目录存在
for folder in output_dirs.values():
    os.makedirs(folder, exist_ok=True)

# 目标计算年份
start_year, end_year = 1961, 2014

# 计算 TXx、TXn、TNx、TNn
for year in tqdm(range(start_year, end_year + 1), desc="Computing TXx, TXn, TNx, TNn"):
    tmax_file = os.path.join(tmax_dir, f"tmax_{year}.tif")
    tmin_file = os.path.join(tmin_dir, f"tmin_{year}.tif")

    if not os.path.exists(tmax_file) or not os.path.exists(tmin_file):
        print(f"Skipping {year}, missing data files.")
        continue

    # 读取 Tmax 数据
    with rasterio.open(tmax_file) as src:
        tmax_data = src.read()  # 形状 (天数, 高度, 宽度)
        meta = src.meta.copy()
        meta.update({"count": 1, "dtype": "float32", "compress": "lzw"})  # 适配单波段输出

    # 读取 Tmin 数据
    with rasterio.open(tmin_file) as src:
        tmin_data = src.read()

    # 计算 TXx, TXn, TNx, TNn
    txx = np.nanmax(tmax_data, axis=0)  # 每个像元的最大 Tmax
    txn = np.nanmin(tmax_data, axis=0)  # 每个像元的最小 Tmax
    tnx = np.nanmax(tmin_data, axis=0)  # 每个像元的最大 Tmin
    tnn = np.nanmin(tmin_data, axis=0)  # 每个像元的最小 Tmin

    # 处理无效值
    txx[np.isnan(txx)] = np.nan
    txn[np.isnan(txn)] = np.nan
    tnx[np.isnan(tnx)] = np.nan
    tnn[np.isnan(tnn)] = np.nan

    # 保存 TXx
    txx_file = os.path.join(output_dirs["TXx"], f"TXx_{year}.tif")
    with rasterio.open(txx_file, "w", **meta) as dst:
        dst.write(txx, 1)
        dst.set_band_description(1, f"TXx_{year}")

    # 保存 TXn
    txn_file = os.path.join(output_dirs["TXn"], f"TXn_{year}.tif")
    with rasterio.open(txn_file, "w", **meta) as dst:
        dst.write(txn, 1)
        dst.set_band_description(1, f"TXn_{year}")

    # 保存 TNx
    tnx_file = os.path.join(output_dirs["TNx"], f"TNx_{year}.tif")
    with rasterio.open(tnx_file, "w", **meta) as dst:
        dst.write(tnx, 1)
        dst.set_band_description(1, f"TNx_{year}")

    # 保存 TNn
    tnn_file = os.path.join(output_dirs["TNn"], f"TNn_{year}.tif")
    with rasterio.open(tnn_file, "w", **meta) as dst:
        dst.write(tnn, 1)
        dst.set_band_description(1, f"TNn_{year}")

print("TXx, TXn, TNx, TNn calculation completed. Results saved to respective folders.")
