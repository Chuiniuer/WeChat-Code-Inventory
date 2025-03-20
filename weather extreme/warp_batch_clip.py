# -*- coding: utf-8 -*-
"""
Created on Sat Feb  8 21:42:44 2025

@author: Bohao Li
"""

import os
from osgeo import gdal

def batch_clip_raster_with_shapefile(input_folder, output_folder, mask_shapefile):
    """
    批量按掩膜提取栅格数据（裁剪）。

    参数：
    input_folder: str - 输入栅格文件夹路径
    output_folder: str - 输出文件夹路径
    mask_shapefile: str - 掩膜 Shapefile 文件路径
    """
    # 确保输出文件夹存在
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # 获取输入文件夹中的所有 .tif 文件
    tif_files = [f for f in os.listdir(input_folder) if f.endswith('.tif')]

    # 遍历所有 .tif 文件并进行裁剪
    for tif_file in tif_files:
        input_raster = os.path.join(input_folder, tif_file)
        output_raster = os.path.join(output_folder, tif_file)

        print(f"正在处理: {input_raster}")

        # 使用 gdal.Warp 进行裁剪
        gdal.Warp(
            output_raster,  # 输出文件路径
            input_raster,   # 输入文件路径
            outputBounds=(74.4552245904425689, 26.8719972341850593, 104.9324823737625536, 39.9207261153180610),
            xRes=0.25,
            yRes=0.25,
            resampleAlg="bilinear",
            cutlineDSName=mask_shapefile,  # 掩膜 Shapefile 文件路径
            cropToCutline=True,  # 裁剪到掩膜范围
            dstNodata=None  # 如果需要设置 NoData 值，可以指定
        )

        print(f"已保存到: {output_raster}")

    print("批量裁剪完成！")


# 示例用法
if __name__ == "__main__":
    input_folder = r"F:\CN05.1_converted\tmax"  # 输入栅格文件夹路径
    output_folder = r"F:\QTP_CN05.1_converted\tmax"  # 输出文件夹路径
    mask_shapefile = r"E:\CMIP5&6 comparison\QTP_region\regions\QTP.shp"  # 掩膜 Shapefile 文件路径

    # 调用函数进行批量裁剪
    batch_clip_raster_with_shapefile(input_folder, output_folder, mask_shapefile)