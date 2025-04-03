# -*- coding: utf-8 -*-
"""
Created on Thu Apr  3 13:10:54 2025

@author: Bohao Li
"""

import cv2
from osgeo import gdal
import pandas as pd
import numpy as np
from tqdm import tqdm
import matplotlib.pyplot as plt
import numpy.ma as ma
#we need to convert the reflectance to the range of 0-256
def Normalize_from_0_to_256(array):
    array1 = array.copy()
    array = array.astype(np.float32)
    array = (array - array.min())/(array.max()-array.min())
    array = array * 256
    array = array.astype(np.uint8)
    array[array1==0] = 0
    return array

def norm_to_org(a, array):
    array = array.astype(np.int32)
    a = (float(a) / 256) * (float(array.max())-float(array.min())) + float(array.min())
    return a
    
def write_image(out_path, array, xsize, ysize, gt, proj):
    #writing new raster data
    driver = gdal.GetDriverByName("GTiff")
    driver.Register()
    out_ds = driver.Create(out_path, xsize=xsize, ysize=ysize, bands=1, eType=gdal.GDT_Byte, options=["COMPRESS=LZW"])
    out_ds.SetGeoTransform(gt)
    out_ds.SetProjection(proj)
    out_band = out_ds.GetRasterBand(1)
    out_band.WriteArray(array)
    out_band.SetNoDataValue(-1)
    out_band.FlushCache()

    out_band = None
    out_ds = None
    
def M_OTSU(MNDWI, feature, out_path, gt, proj, f):
    # sampling from the feature according an equal proportion of "MNDWI>0" and "MNDWI<0"

    XSize = MNDWI.shape[1]
    YSize = MNDWI.shape[0]
    df = pd.DataFrame(columns=["feature", "MNDWI"])
    df["feature"] = feature.reshape(-1)
    df["MNDWI"] = MNDWI.reshape(-1)

    if len(df[df["MNDWI"]>0]) < len(df[df["MNDWI"]<0]):
        nonwater = np.array(df[df["MNDWI"]<0].sample(n=len(df[df["MNDWI"]>0]))["feature"])
        water = np.array(df[df["MNDWI"]>0]["feature"])
    else:
        nonwater = np.array(df[df["MNDWI"]<0]["feature"])
        water = np.array(df[df["MNDWI"]>0].sample(n=len(df[df["MNDWI"]<0]))["feature"])

    sampled = np.append(water, nonwater)
    df_sampled = pd.DataFrame(columns=["sample"])
    df_sampled["sample"] = sampled
    sampled = np.array(df_sampled.dropna())
    sampled = Normalize_from_0_to_256(sampled)
    
    th, img = cv2.threshold(sampled, 0 , 255, cv2.THRESH_OTSU)
    print(th)
    feature_norm = Normalize_from_0_to_256(feature)
    # plt.hist(feature_norm)
    result = feature_norm.copy()

    result[feature_norm>=th] = 1
    result[feature_norm<th] = 0
    write_image(out_path, result, XSize, YSize, gt, proj)
    th = norm_to_org(float(th), feature)
    return th

#setting the base variables
input_folder = "P:\\object-based clustering\\Clipped_converted\\LPY\\"
output_folder = "E:\\phd_l1\\微信公众号\\20250403_MOTSU\\"
features = ["MNDWI", "NDWI", "AWEI", "MBWI"]
#define a table to save the threshold
df_th = pd.DataFrame(columns=["feature", "threshold"])
df_th["feature"] = features
th_list = []

MNDWI = gdal.Open(input_folder + f"sentinel2_MNDWI_LPY.tif").ReadAsArray()
MNDWI[MNDWI==-32768] = 0

for f in tqdm(features):
    ds = gdal.Open(input_folder + f"sentinel2_{f}_LPY.tif")
    gt = ds.GetGeoTransform()
    proj = ds.GetProjection()
    feature = ds.ReadAsArray()
    feature = ma.masked_values(feature, -32768)
    
    th = M_OTSU(MNDWI, feature, output_folder+f"sentinel2_{f}_LPY_M-OTSU.tif", gt, proj, f)
    
    th_list.append(th)