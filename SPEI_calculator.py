# -*- coding: utf-8 -*-
"""
Created on Wed Jan 17 12:43:50 2024

@author: Bohao Li
"""

import numpy as np
import pandas as pd
from osgeo import gdal
from climate_indices import indices
from climate_indices import compute
import matplotlib.pyplot as plt
from tqdm import tqdm
from datetime import datetime
import netCDF4 as nc

def cal_pet(tas_time_series, lat, data_start_year):
    """
    

    Parameters
    ----------
    tas_time_series : TYPE
        DESCRIPTION.
    lat_time_series : TYPE
        DESCRIPTION.
    data_start_year : TYPE
        DESCRIPTION.

    Returns
    -------
    pet_data : TYPE
        Return pet time series.

    """
    pet_data = indices.pet(temperature_celsius=tas_time_series,
                           latitude_degrees=lat,
                           data_start_year=data_start_year
        )
    return pet_data

def cal_spei(prcp_time_series, pet_time_series, scale, data_start_year, calibration_year_initial, calibration_year_final):
    '''

    Parameters
    ----------
    prcp_time_series : TYPE
        DESCRIPTION.
    pet_time_series : TYPE
        DESCRIPTION.
    scale : TYPE
        DESCRIPTION.
    data_start_year : TYPE
        DESCRIPTION.
    calibration_year_initial : TYPE
        DESCRIPTION.
    calibration_year_final : TYPE
        DESCRIPTION.

    Returns
    -------
    spei : TYPE
        Return time series

    '''
    spei = indices.spei(precips_mm=prcp_time_series,
                        pet_mm=pet_time_series,
                        scale=scale,
                        distribution=indices.Distribution.gamma,
                        periodicity=compute.Periodicity.monthly,
                        data_start_year=data_start_year,
                        calibration_year_initial=calibration_year_initial,
                        calibration_year_final=calibration_year_final
        )
    # spei[np.isnan(spei)] = -99
    return spei

    
def write_nc(path: str, arr: np.ndarray, main_var: str, nodata: float):
    newfile = nc.Dataset(path, 'w', format='NETCDF4')

    #define dimensions
    lon = newfile.createDimension("longitude", size=3601)
    lat = newfile.createDimension("latitude", size=1801)
    times = newfile.createDimension("time", size=None)

    # define variables for storing data
    lon = newfile.createVariable("lon", np.float32, dimensions="longitude")
    lat = newfile.createVariable("lat", np.float32, dimensions="latitude")
    time = newfile.createVariable("times", "S19", dimensions="time")
    crucial_var = newfile.createVariable(main_var, np.int16, dimensions=("time", "latitude", "longitude"))
    date_range = pd.date_range(datetime(1951, 1, 15), datetime(2022, 12, 31), freq="1m")

    # add data to variables
    lon[:] = np.arange(-179.99999977, 180.00164697+0.05, 0.10000045742818514)
    lat[:] = np.arange(89.99999977, 90.05, -0.10000045742818514)
    crucial_var[:, :, :] = (arr * 1000)
    crucial_var[np.isnan(crucial_var)] = nodata
    crucial_var = crucial_var.astype(np.int16)
    for i in range(arr.shape[0]):
        time[i] = date_range[i].strftime("%Y-%m-%d")
    print(date_range[0].strftime("%Y-%m-%d"))
    print(time)
    # add attributes
    # add global attributes
    newfile.title = f"monthly {main_var} data"
    newfile.start_time = time[i]
    newfile.times = time.shape[0]
    newfile.history = "Created" + datetime(2023, 1, 17).strftime("%Y-%m-%d")

    # add local attributes to variable
    lon.description = "longitude, range from -180 to 180"
    lon.units = "degrees"

    lat.description = "latitude, south is negative"
    lat.units = "degrees north"

    time.description = "time, unlimited dimension"
    time.units = "time since {0:s}".format(time[0])

    crucial_var.description = f"The time scaler is 3 month. The scaler of value is 1000"
    # crucial_var.units = unit
    crucial_var.missing_value = nodata
    # close file
    newfile.close()

def main():

    input_tas_folder = "/work/home/bjsfdxlbh/Bohao/ecosystem_productivity/era5-land/ERA5_tas_Monthly/"
    input_pr_folder = "/work/home/bjsfdxlbh/Bohao/ecosystem_productivity/era5-land/ERA5_tas_Monthly/"
    
    ref_ds = gdal.Open(input_tas_folder+"ERA5_tas_Monthly_1951_1.tif")
    ref_arr = ref_ds.ReadAsArray()
    gt = ref_ds.GetGeoTransform()
    proj = ref_ds.GetProjection()
    
    tempa_data = np.zeros((72*12, ref_arr.shape[0], ref_arr.shape[1]), dtype=np.float32)
    count = 0
    for y in range(1951, 2023):
        for m in range(1, 13):
            tempa_data[count] = gdal.Open(input_tas_folder+f"ERA5_tas_Monthly_{y}_{m}.tif").ReadAsArray()
            count += 1
    tempa_data[tempa_data==-32768] = np.nan
    tempa_data = tempa_data - 273.15
    
    prcp_data = np.zeros((72*12, ref_arr.shape[0], ref_arr.shape[1]), dtype=np.float32)
    count = 0
    for y in range(1951, 2023):
        for m in range(1, 13):
            prcp_data[count] = gdal.Open(input_tas_folder+f"ERA5_pr_Monthly_{y}_{m}.tif").ReadAsArray()
            count += 1
    prcp_data[prcp_data==-32768] = np.nan
    prcp_data = prcp_data * 1000
    
    lat_data = r"/work/home/bjsfdxlbh/Bohao/ecosystem_productivity/era5-land/latmask.tif"
    out_folder = "/work/home/bjsfdxlbh/Bohao/ecosystem_productivity/era5-land/SPEI/"

    lat_ds = gdal.Open(lat_data)
    lat_array = lat_ds.ReadAsArray()
    
    gt = lat_ds.GetGeoTransform()
    proj = lat_ds.GetProjection()
    
    pet = tempa_data.copy()
    
    for i in tqdm(range(tempa_data.shape[1])):
        for j in range(tempa_data.shape[2]):
            pet[:, i, j] = cal_pet(tempa_data[:, i, j], lat_array[i, j], 1951)
            
    print("___SPEI caculating___")
    #scale of spei
    for s in tqdm([3]):
        spei = tempa_data.copy()
        for i in range(tempa_data.shape[1]):
            for j in range(tempa_data.shape[2]):
                spei[:, i, j] = cal_spei(prcp_data[:, i, j], pet[:, i, j], s, 1951, 1951, 2014)
        write_nc(out_folder + f"SPEI_{s}.nc", spei, "SPEI_3", -32768)

if __name__ == "__main__":
    main()
