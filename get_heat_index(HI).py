# -*- coding: utf-8 -*-
"""
Created on Sat Aug 13 21:58:12 2022

@author: Bohao Li
"""

import pandas as pd
import numpy as np
import netCDF4 as nc
from datetime import datetime
from osgeo import gdal, osr
import os
from tqdm import tqdm
import glob
import matplotlib.pyplot as plt
import xarray as xr
import time
from concurrent.futures import ProcessPoolExecutor
# os.environ['PROJ_LIB'] = r'C:\ProgramData\Anaconda3\envs\geoplot\Lib\site-packages\pyproj\proj_dir\share\proj'
# os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'
"""
The HI output is scaled up by a scaler of 10 and converted to an integer.
"""

def unit_convert_tas(array):
    """
    K -> ℃
    :param array:
    :return:
    """

    array[array == 1e20] = -10000
    array = array - 273.15
    array[array < -9999] = -9999
    # array = array.astype(np.int16)
    return array


def unit_convert_C2F(array):
    """
    ℃ ->℉
    :param array:
    :return:
    """

    array[array == 1e20] = -10000
    array = array * (9/5) + 32
    array[array < -9999] = -9999
    # array = array.astype(np.int16)
    return array


def write_3d_tif(output_path, array, gt):
    bands = array.shape[0]
    driver = gdal.GetDriverByName('GTiff')
    out_tif = driver.Create(output_path, array.shape[2], array.shape[1],
                            bands, gdal.GDT_Int16, options=["COMPRESS=LZW"])

    out_tif.SetGeoTransform(gt)

    # Get geographic coordinate system
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)  # Define the output coordinate system as WGS84
    out_tif.SetProjection(srs.ExportToWkt())  # Creating projection information for new layers

    for b in range(bands):

        # 数据写出 
        out_tif.GetRasterBand(b+1).WriteArray(array[b])
        out_tif.GetRasterBand(b+1).SetNoDataValue(-9999)
    out_tif.FlushCache()
    # print(f'output successfully')
    del out_tif



def heat_index(tasmax_folder, hurs_folder, year, month, output_folder):
    """
    Calculation of HI on a year-by-year basis Calculation methodology is the NWS2011 framework, reference website https://ehp.niehs.nih.gov/doi/full/10.1289/ehp.1206273
    In order to reduce storage space, the final result *10 is stored as type int16
    Parameters
    ----------
    tasmax_folder : TYPE
        DESCRIPTION.
    hurs_folder : TYPE
        DESCRIPTION.
    mode : TYPE
        DESCRIPTION.
    year : TYPE
        DESCRIPTION.
    out_folder : TYPE
        DESCRIPTION.

    Returns heat_index
    -------
    None.

    """

    tas_ds = gdal.Open(tasmax_folder + f"ERA5_T2mMax_Daily_{year}_{month}.tif")
    band = tas_ds.GetRasterBand(1)
    nodata_value = band.GetNoDataValue()
    tas = tas_ds.ReadAsArray()
    # Set all nodata value to -9999
    if np.isnan(nodata_value):
        tas[np.isnan(tas)] = -9999
    else:
        tas[tas==nodata_value] = -9999
    tas = unit_convert_tas(tas)
    tas = unit_convert_C2F(tas)
    
    hurs_ds = gdal.Open(hurs_folder + f"RHmin_{year}-{month}.tif")
    band = hurs_ds.GetRasterBand(1)
    nodata_value = band.GetNoDataValue()
    hurs = hurs_ds.ReadAsArray()
    # Set all nodata value to -9999
    if np.isnan(nodata_value):
        nodata_mask = np.isnan(hurs)
        # hurs = hurs / 100
        hurs[nodata_mask] = -9999
    else:
        nodata_mask = (hurs==nodata_value)
        # hurs = hurs / 100
        hurs[nodata_mask] = -9999 
    
    
    result = np.full(tas.shape, -9999, dtype=np.int16)
    result[tas <= 40] = tas[tas <= 40] * 10

    A = -10.3 + (1.1 * tas) + (0.047 * hurs)
    result[(A < 79) * (tas > 40)] = A[(A < 79) * (tas > 40)] * 10

    B = -42.379 + (2.04901523 * tas) + (10.14333127 * hurs) - (0.22475541 * tas * hurs) - (6.83783 * 0.001
                                                                                           * tas * tas) - (5.481717 * 0.01 * hurs * hurs) + (1.22874 * 0.001 * tas * tas * hurs) + (8.5282 * 0.0001
                                                                                                                                                                                    * tas * hurs * hurs) - (1.99 * 0.000001 * tas * tas * hurs * hurs)

    result[(hurs <= 13) * (tas >= 80) * (tas <= 112) * (A >= 79) * (tas > 40)] = (B - (((13-hurs)/4) *
                                                                          np.sqrt((17-np.abs(tas-95))/17)))[(hurs <= 13) * (tas >= 80) * (tas <= 112) * (A >= 79) * (tas > 40)] * 10

    result[(hurs > 85) * (tas >= 80) * (tas <= 87) * (A >= 79) * (tas > 40) ] = (B + 0.02 *
                                                                   ((hurs-85) * (87-tas)))[(hurs > 85) * (tas >= 80) * (tas <= 87) * (A >= 79) * (tas > 40)] * 10

    result[(result==-9999) * (tas!=-9999)] = B[(result==-9999) * (tas!=-9999)] * 10

    result[tas == -9999] = -9999
    return result



if __name__ == "__main__":
    
    output_folder = "E:\\l3\\HI_test\\"
    tasmax_folder = "E:\\l3\\Tmax_clipped\\"
    hurs_folder = "E:\\l3\RHmin_clipped\\"
    year = 2000
    month = 7
    
    gt = gdal.Open(hurs_folder + r"RHmin_2000-7.tif").GetGeoTransform()
    
    hi = heat_index(tasmax_folder, hurs_folder, year, month, output_folder)
    write_3d_tif(output_folder+f"HI_{year}_{month}.tif", hi, gt)
