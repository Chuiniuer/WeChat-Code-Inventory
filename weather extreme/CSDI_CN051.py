import os
import numpy as np
import rasterio
from tqdm import tqdm
from datetime import datetime

# 输入数据路径
data_dir = r"F:\QTP_CN05.1_converted\tmin"
tnin10_file = r"F:\climate extremes\TN10p\threshold\TNin10.tif"
output_dir = r"F:\climate extremes\CSDI\yearly"

# 目标基准期
start_year, end_year = 1961, 2014

# 确保输出目录存在
os.makedirs(output_dir, exist_ok=True)

# 读取 TNin10（基准期第 10 百分位数）
with rasterio.open(tnin10_file) as src:
    tnin10 = src.read()  # 读取所有 366 天的 10 百分位数
    meta = src.meta.copy()  # 复制元数据
    meta.update({"count": 1, "dtype": "float32", "compress": "lzw"})  # 适配单波段输出

# 记录上一年年尾的冷昼天数
prev_year_tail = np.zeros((meta["height"], meta["width"]), dtype=np.int32)

# 计算每年的 CSDI
for year in tqdm(range(start_year, end_year + 1), desc="Computing CSDI"):
    input_file = os.path.join(data_dir, f"tmin_{year}.tif")
    next_year_file = os.path.join(data_dir, f"tmin_{year + 1}.tif") if year < end_year else None

    # 读取该年的最低温数据
    with rasterio.open(input_file) as src:
        num_days = src.count  # 该年的天数（365 或 366）
        csdi = np.zeros((src.height, src.width), dtype=np.float32)  # 初始化 CSDI 计数数组
        nan_mask = np.zeros((src.height, src.width), dtype=bool)  # 记录无效值区域
        cold_wave_mask = np.zeros((num_days, src.height, src.width), dtype=bool)  # 仅当前年

        # 读取今年的数据
        for band in range(1, num_days + 1):  # 1-based index
            date_str = src.descriptions[band - 1]  # 读取日期
            _, month, day = map(int, date_str.split("-"))
            day_of_year = (datetime(year, month, day) - datetime(year, 1, 1)).days  # 0-based

            data = src.read(band)  # 读取该天的数据
            invalid_mask = np.isnan(data)  # 无效值掩码
            nan_mask |= invalid_mask  # 记录该像元是否为无效值

            # 标记低于 TNin10 的天数
            cold_wave_mask[band - 1] = (data < tnin10[day_of_year]) & (~invalid_mask)

        # 统计当前年的 CSDI
        year_end_tail = np.zeros((src.height, src.width), dtype=np.int32)  # 记录年尾冷昼
        for i in range(src.height):
            for j in range(src.width):
                if nan_mask[i, j]:  # 跳过无效值
                    continue

                cw_series = cold_wave_mask[:, i, j]
                count = 0  # 当前年的冷昼计数
                csdi_value = 0
                first_non_cold_day = False  # 是否遇到第一天的非冷昼

                for d in range(num_days):
                    if cw_series[d]:  # 该天是冷昼
                        count += 1
                    else:  # 遇到非冷昼
                        if prev_year_tail[i, j] > 0 and not first_non_cold_day:
                            csdi_value += count  # **无条件加上上一年的冷昼**
                            prev_year_tail[i, j] = 0  # **加完后清零**
                            first_non_cold_day = True  # 标记已经遇到第一天非冷昼
                            count = 0
                            continue
                        if count >= 6:
                            csdi_value += count  # 计入 CSDI
                        count = 0  # 重新开始计数

                # **暂存年末的冷昼天数**
                year_end_tail[i, j] = count

                # 今年的 CSDI 结果
                csdi[i, j] = csdi_value

        # 读取 **下一年年初的 Tmin 数据**
        if next_year_file and os.path.exists(next_year_file):
            with rasterio.open(next_year_file) as next_src:
                next_num_days = next_src.count
                next_cold_wave = np.zeros((min(6, next_num_days), src.height, src.width), dtype=bool)

                for band in range(1, min(7, next_num_days + 1)):  # 取最多 6 天
                    date_str = next_src.descriptions[band - 1]  # 读取日期
                    _, month, day = map(int, date_str.split("-"))
                    day_of_year = (datetime(year + 1, month, day) - datetime(year + 1, 1, 1)).days  # 0-based

                    data = next_src.read(band)  # 读取该天的数据
                    invalid_mask = np.isnan(data)
                    nan_mask |= invalid_mask  # 继续记录无效值

                    # 标记低于 TNin10 的天数
                    next_cold_wave[band - 1] = (data < tnin10[day_of_year]) & (~invalid_mask)

                # **如果年初仍然是冷昼，考虑与 year_end_tail 合并**
                prev_year_tail.fill(0)  # 先重置
                for i in range(src.height):
                    for j in range(src.width):
                        if nan_mask[i, j]:  # 跳过无效值
                            continue

                        # 计算下一年连续的冷昼天数
                        next_start_count = 0
                        for d in range(min(6, next_num_days)):
                            if next_cold_wave[d, i, j]:
                                next_start_count += 1
                            else:
                                break

                        # **判断 year_end_tail 和 next_start_count 之和是否 >= 6**
                        if year_end_tail[i, j] + next_start_count >= 6:
                            csdi[i, j] += year_end_tail[i, j]  # 今年 CSDI 先加上
                            prev_year_tail[i, j] = next_start_count  # 传递给下一年

        # 处理无效值
        csdi[nan_mask] = np.nan

        # 调试输出
        print(f"Year {year}: CSDI min={np.nanmin(csdi)}, max={np.nanmax(csdi)}")

    # 输出 CSDI 结果
    output_file = os.path.join(output_dir, f"CSDI_{year}.tif")
    with rasterio.open(output_file, "w", **meta) as dst:
        dst.write(csdi, 1)  # 写入单波段
        dst.set_band_description(1, f"CSDI_{year}")

print("CSDI calculation completed. Results saved to:", output_dir)
