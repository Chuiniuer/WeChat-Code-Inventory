# -*- coding: utf-8 -*-
"""
Created on Tue Feb  6 13:08:05 2024

@author: Bohao Li
"""

import numpy as np
import netCDF4 as nc
from osgeo import gdal, osr, ogr
import os
# import glob
import re
import datetime
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor
import time

def img_resample(path, out_folder):
    ds = gdal.Open(path, gdal.OF_RASTER | gdal.OF_UPDATE)
    dsRes = gdal.Warp(out_folder + '\\' + path.split("\\")[-1].split('.')[0] + '.tif', ds, width=720, 
                      height=360, resampleAlg='bilinear', dstNodata=np.nan, outputBounds=(0, -90, 360, 90), creationOptions=["COMPRESS=LZW"])
    del ds
    del dsRes

def main():
    input_vars = ["tmin"]
                  # , "tas"]
    for _var in tqdm(input_vars):
        input_folder = "F:\\CN05.1\\00 - CN051-2021\\1961-2021"
        output_folder1 ="F:\\CN05.1_converted\\tmin"
        # nc_path_list = [input_folder + '\\' + d for d in os.listdir(input_folder) if d[-3:] == '.nc']
        # print(f'number of nc file:{len(nc_path_list)}')
        # print('**ss*****************************')
        # file_count = len(nc_path_list)
        # for path in nc_path_list:
        path = input_folder + "\\CN05.1_Tmin_1961_2021_daily_025x025.nc"
        data = nc.Dataset(path)
        lon = data.variables['lon'][:]
        lat = data.variables['lat'][:]
        # print(lon)
        miss_value = data.variables[_var].missing_value
        out_arr = np.asarray(data.variables[_var])#输入需要转换的波段名称
        out_arr[out_arr==int(miss_value)] = np.nan
        # print(out_arr.shape)
        # print(out_arr[0, 1, 1])
        # print(len(out_arr[:]))
        #影像的左上角和右下角坐标
        lonMin, latMax, lonMax, latMin = [lon.min(), lat.max(), lon.max(), lat.min()]

        #分辨率计算
        n_lat = len(lat)
        n_lon = len(lon)
        lon_res = (lonMax - lonMin)/(float(n_lon) - 1)
        lat_res = (latMax - latMin)/(float(n_lat) - 1)
        # print(lon_res)
        # print(lat_res)
        # print(data.variables['time'][:].data)
        # print(data.variables['time'].units)
        #读取时间信息
        time = list(nc.num2date(data.variables['time'][:], data.variables['time'].units,\
                            calendar=data.variables['time'].calendar).data)
        # time = list(data.variables['time'][:])

        # # 下面是转换过程
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
            out_tif_name = output_folder1 + '\\' + _var + "_" +\
                temp_time[0].split('-')[0] + '.tif'
            out_tif = driver.Create(out_tif_name, n_lon, n_lat, len(temp_time), gdal.GDT_Float32, options=["COMPRESS=LZW"])
            geotransform = (lonMin-0.5*lon_res, lon_res, 0, latMax+0.5*abs(lat_res), 0, -abs(lat_res))#GeoTransform存储了6个用于描述数据位置的参数，是GeoTiff非常重要的一个信息
            out_tif.SetGeoTransform(geotransform)

            #获取地理坐标系
            srs = osr.SpatialReference()
            srs.ImportFromEPSG(4326)#定义输出的坐标系统为WGS84
            out_tif.SetProjection(srs.ExportToWkt())#给新建图层创建投影信息
            for i in range(len(temp_time)):
                raster_band = out_tif.GetRasterBand(i + 1)
                raster_band.SetDescription(temp_time[i])
                raster_band.SetNoDataValue(np.nan)
                # arr[arr == miss_value] = np.nan
                # arr = arr * 1000

                raster_band.WriteArray(out_arr[count+i, ::-1, :])
            out_tif.FlushCache()
            del out_tif
            count += len(temp_time)
            for i in temp_time:
                time.remove(i)

                
                
                
        # print('---script ending---')
        
        # resampling file
        # input_folder = output_folder1
        # output_folder2 = "F:\\ERA5\\CIN_monthly_resampled\\"
        # images = [input_folder + '\\' + d for d in os.listdir(input_folder) if d[-4:] == '.tif']
        # # print(f'number of files:{len(images)}')
        # # print('********************************')
        # for path in images:
        #     img_resample(path, output_folder2)
            
        # #删除缓存文件
        # converted_images = [output_folder1 + "\\" + d for d in os.listdir(output_folder1)]
        # for image in converted_images:
        #     os.remove(image)
                
                        
if __name__ == '__main__':
    start = time.time()

    # input_vars = ["tasmax", "tas", "sfcwind", "rsds", "hurs"]
    main()
    end = time.time()
    print("----------script ending----------")
    print(f"time: {end - start}")