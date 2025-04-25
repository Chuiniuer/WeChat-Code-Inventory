# -*- coding: utf-8 -*-
"""
Created on Wed Mar 19 19:32:55 2025

@author: DELL
"""
import os
import numpy as np
import rasterio
from rasterio.transform import Affine
from datetime import datetime, timedelta
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
    # 1. 读取数据
    input_dir = r"P:\climate data\ERA5_land_total_precipitation_clipped"
    output_dir = r"P:\climate data\WAP_results_nob"
    os.makedirs(output_dir, exist_ok=True)
    
    years = range(2010, 2021)
    all_data = []
    
    print("正在读取数据...")
    for year in tqdm(years):
        file_path = os.path.join(input_dir, f"era5-land-pr-{year}.tif")
        with rasterio.open(file_path) as src:
            # 读取所有波段（每天一个波段）
            data = src.read()  # 形状: (bands, height, width)
            # 处理无效值和缩放
            data = data.astype(np.float32)
            data[data == -9999] = np.nan
            data /= 10.0  # 还原真实值（原数据×10）
            all_data.append(data)
    
    # 沿时间轴拼接（得到形状: (total_days, height, width)）
    precip_stack = np.concatenate(all_data, axis=0)
    
    # 2. 计算WAP（跨年连续计算）
    print("计算WAP...")
    wap_result = calculate_daily_wap(precip_stack)
    
    # 3. 按年分割结果并输出
    print("输出结果...")
    day_counter = 0
    
    for i, year in enumerate(tqdm(years)):
        # 获取该年的天数（原文件波段数）
        n_days = all_data[i].shape[0]
        year_wap = wap_result[day_counter : day_counter + n_days]
        day_counter += n_days
        
        # 使用第一个文件的元数据作为模板
        with rasterio.open(os.path.join(input_dir, f"era5-land-pr-{year}.tif")) as src:
            meta = src.meta.copy()
        
        # 更新元数据
        meta.update({
            'count': n_days,
            'dtype': 'float32',
            'nodata': np.nan
        })
        
        # 输出为GeoTIFF
        output_path = os.path.join(output_dir, f"era5-land-wap-{year}.tif")
        with rasterio.open(output_path, 'w', **meta) as dst:
            dst.write(year_wap)
    
    print("处理完成！结果已保存至:", output_dir)