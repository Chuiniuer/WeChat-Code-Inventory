# -*- coding: utf-8 -*-
"""
Created on Tue Mar 18 13:25:40 2025

@author: Bohao Li
"""

import numpy as np
import netCDF4 as nc
from osgeo import gdal, osr, ogr
import os
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor
import time
import matplotlib.pyplot as plt
import math
import re
    
def mkdir(path):
 
	folder = os.path.exists(path)
 
	if not folder:                   #判断是否存在文件夹如果不存在则创建为文件夹
		os.makedirs(path)            #makedirs 创建文件时如果路径不存在会创建这个路径
		print("---  new folder...  ---")
		print("---  OK  ---")
 
	else:
		print("---  There is this folder!  ---")

def pr_unit_convert(array):
   """
   Kg/m3/s -> mm/day
   :param array:
   :return:
   """
   array = (array * 86400)
   array[array<0] = np.nan
   return array


def main(m):
    input_vars = ["pr"]     
    lon_min_qtp, lon_max_qtp = 74.455225, 104.932482
    lat_min_qtp, lat_max_qtp = 26.871997, 39.920726

    for _var in tqdm(input_vars):
        input_folder = "H:\\NEX_Data_Update\\prv1.1\\" + m
        output_folder ='Q:\\QTP_Climate_extremes\\QTP_NEX_converted\\' + _var + "\\" + m
        mkdir(output_folder)
        nc_path_list = [input_folder + '\\' + d for d in os.listdir(input_folder) if d[-3:] == '.nc']
        print(f'number of nc file:{len(nc_path_list)}')
        print('********************************')
        file_count = len(nc_path_list)
        
        for path in nc_path_list:
            data = nc.Dataset(path)
            lon = data.variables['lon'][:]
            lat = data.variables['lat'][:]
            out_arr = np.asarray(data.variables[_var])#输入需要转换的波段名称
            #影像的最边缘像元的中心坐标
            lonMin, latMax, lonMax, latMin = [lon.min(), lat.max(), lon.max(), lat.min()]
            
            #分辨率计算
            n_lat = len(lat)
            n_lon = len(lon)
            lon_res = (lonMax - lonMin)/(float(n_lon) - 1)
            lat_res = (latMax - latMin)/(float(n_lat) - 1)
            
            #根据输入的研究区的最大范围进行数据切片
            x_offset = int((lon_min_qtp - (lonMin-0.5*lon_res))/lon_res)  #裁剪中国区域
            y_offset = int((lat_min_qtp - (latMin-0.5*lat_res))/lat_res)
            x_offset_max = int((lon_max_qtp - (lonMin-0.5*lon_res))/lon_res)+1
            y_offset_max = int((lat_max_qtp - (latMin-0.5*lat_res))/lat_res)+1
            
            out_arr = out_arr[:, y_offset:y_offset_max, x_offset:x_offset_max]
            
            #读取时间信息
            time = list(nc.num2date(data.variables['time'][:], data.variables['time'].units,\
                               calendar=data.variables['time'].calendar).data)
            # 下面是转换过程
            # 将原始异常值替换为np.nan
            out_arr[out_arr[:, :] == data.variables[_var]._FillValue] = np.nan
            
            #单位转换并上下翻转
            out_arr = pr_unit_convert(out_arr)[:, ::-1, :]
            
            match = re.search(r"historical|ssp\d{3,4}", path)
            if match:
                scenario = match.group()
            
            
            #将年份信息提取为字符串
            for t in range(len(time)):
                time[t] = str(time[t]).split()[0]
            count = 0
            while time != []:
                temp_time = []
                for i in range(len(time)):
                    if temp_time == []:
                        temp_time.append(time[i])
                    elif time[i].split('-')[0] == temp_time[0].split('-')[0]:
                        temp_time.append(time[i]) 
                driver = gdal.GetDriverByName('GTiff')
                out_tif_name = output_folder + '\\' + m + "_" +  _var + '_' + scenario + "_" +\
                    temp_time[0].split('-')[0] + '.tif'
                out_tif = driver.Create(out_tif_name, out_arr.shape[2], out_arr.shape[1], len(temp_time), gdal.GDT_Float32, options=["COMPRESS=LZW"])
                #设置仿射变换函数
                
                #数组切片只能存储0.25的整数倍的空间范围，所以这里存储数据时需要进行转化
                lon_min_qtp_gt = math.floor(lon_min_qtp / 0.25) * 0.25
                lat_max_qtp_gt = math.ceil(lat_max_qtp / 0.25) * 0.25
                
                geotransform = (lon_min_qtp_gt, lon_res, 0, lat_max_qtp_gt, 0, -lat_res)
                out_tif.SetGeoTransform(geotransform)
                
                #获取地理坐标系
                srs = osr.SpatialReference()
                srs.ImportFromEPSG(4326)#定义输出的坐标系统为WGS84
                out_tif.SetProjection(srs.ExportToWkt())#给新建图层创建投影信息
                for i in range(len(temp_time)):
                    raster_band = out_tif.GetRasterBand(i + 1)
                    raster_band.SetDescription(temp_time[i])
                    raster_band.WriteArray(out_arr[count + i, :, :])
                    raster_band.SetNoDataValue(np.nan)
                out_tif.FlushCache()
                del out_tif
                count += len(temp_time)
                for i in temp_time:
                    time.remove(i)
    
    print('---script ending---')    
                
                        
if __name__ == '__main__':
    start = time.time()
    mode_list = ["ACCESS-CM2"]
    for m in mode_list:
        main(m)
    # with ThreadPoolExecutor(max_workers=9) as pool:
    #     pool.map(main, mode_list)
    end = time.time()
    print("----------script ending----------")
    print(f"time: {end - start}")

