import os
import numpy as np
import rasterio
from tqdm import tqdm

# 输入数据路径
tmin_dir = r"F:\QTP_CN05.1_converted\tmin"  # TN
tmax_dir = r"F:\QTP_CN05.1_converted\tmax"  # TX
tmean_dir = r"F:\QTP_CN05.1_converted\tmean"  # TM（用于TFR）

# 输出目录
output_dirs = {
    "FD": r"F:\climate extremes\FD",
    "ID": r"F:\climate extremes\ID",
    "DTR": r"F:\climate extremes\DTR",
    "TFR": r"F:\climate extremes\TFR"
}
for d in output_dirs.values():
    os.makedirs(d, exist_ok=True)

# 目标基准期
start_year, end_year = 1961, 2014
TFR_max = 1000  # 设置最大允许的 TFR 值

# 计算每年的指数
for year in tqdm(range(start_year, end_year + 1), desc="Computing FD, ID, DTR, TFR"):
    tmin_file = os.path.join(tmin_dir, f"tmin_{year}.tif")
    tmax_file = os.path.join(tmax_dir, f"tmax_{year}.tif")
    tmean_file = os.path.join(tmean_dir, f"tm_{year}.tif")

    # 读取 TN（最低温度）
    with rasterio.open(tmin_file) as src:
        tn_data = src.read()
        meta = src.meta.copy()
        meta.update({"count": 1, "dtype": "float32", "compress": "lzw"})  # 适配单波段输出
        height, width = src.height, src.width

    # 读取 TX（最高温度）
    with rasterio.open(tmax_file) as src:
        tx_data = src.read()

    # 读取 TM（平均温度，用于TFR）
    with rasterio.open(tmean_file) as src:
        tm_data = src.read()

    # 初始化结果数组
    fd = np.zeros((height, width), dtype=np.float32)
    id = np.zeros((height, width), dtype=np.float32)
    dtr = np.zeros((height, width), dtype=np.float32)
    thaw_index = np.zeros((height, width), dtype=np.float32)  # 解冻指数
    freeze_index = np.zeros((height, width), dtype=np.float32)  # 冻结指数

    # 遍历所有像元
    for i in range(height):
        for j in range(width):
            tn_series = tn_data[:, i, j]  # TN 时间序列
            tx_series = tx_data[:, i, j]  # TX 时间序列
            tm_series = tm_data[:, i, j]  # TM 时间序列

            # 处理无效值
            if np.any(np.isnan(tn_series)) or np.any(np.isnan(tx_series)) or np.any(np.isnan(tm_series)):
                fd[i, j] = np.nan
                id[i, j] = np.nan
                dtr[i, j] = np.nan
                thaw_index[i, j] = np.nan
                freeze_index[i, j] = np.nan
                continue

            # 计算 FD（霜冻日数）
            fd[i, j] = np.sum(tn_series < 0)

            # 计算 ID（冰冻日数）
            id[i, j] = np.sum(tx_series < 0)

            # 计算 DTR（日较差）
            dtr[i, j] = np.mean(tx_series - tn_series)

            # 计算解冻指数（温度 > 0°C 的累积绝对值）
            thaw_index[i, j] = np.sum(tm_series[tm_series > 0])

            # 计算冻结指数（温度 < 0°C 的累积绝对值）
            print(tm_series[tm_series < 0].shape)
            freeze_index[i, j] = np.abs(np.sum(tm_series[tm_series < 0]))

    # 计算 TFR（解冻指数 / 冻结指数）
    tfr = np.divide(thaw_index, freeze_index, out=np.full_like(thaw_index, np.nan), where=freeze_index != 0)

    # **异常值处理**
    tfr[freeze_index < 1] = np.nan  # 避免极端高值
    tfr[tfr > TFR_max] = np.nan  # 设定最大阈值，避免异常高值

    # 输出结果
    output_files = {
        "FD": os.path.join(output_dirs["FD"], f"FD_{year}.tif"),
        "ID": os.path.join(output_dirs["ID"], f"ID_{year}.tif"),
        "DTR": os.path.join(output_dirs["DTR"], f"DTR_{year}.tif"),
        "TFR": os.path.join(output_dirs["TFR"], f"TFR_{year}.tif"),
    }

    for key, data in zip(output_files.keys(), [fd, id, dtr, tfr]):
        with rasterio.open(output_files[key], "w", **meta) as dst:
            dst.write(data, 1)
            dst.set_band_description(1, f"{key}_{year}")

print("FD, ID, DTR, TFR calculation completed.")
