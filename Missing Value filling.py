# -*- coding: utf-8 -*-
"""
Created on Fri Apr 18 16:29:17 2025

@author: Bohao Li
"""

# lightgbm continuous variables filling
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestRegressor
from lightgbm import LGBMClassifier
from lightgbm import LGBMRegressor
from sklearn.model_selection import cross_val_score


data = gpd.read_file(r"E:\l3\dynamic landslide prediction\training_points\training_datasets_extracted.shp")

# take a pandas dataframe (Here I just remove the "geometry" column)
data = data.iloc[:, :-1]

df = data[["dis2fault", "GEM_RT475y", "elevation", "slope", "TRI", "TWI", "TPI", "curvature", "plan_curva", "prof_curva", "dis2river", "NDVI", "pr"]]
# nodata value processing
df[df==-9999] = np.nan
df[df==-32768] = np.nan
df[df.loc[:, "pr"] == -999] = np.nan


# continuous variables filling
# 按照缺失值多少进行排序
X_missing_reg = df.copy()
removal_list = []
for c in range(len(list(df.columns))):
    if df.iloc[:, c].isnull().sum() == 0:
        removal_list.append(c)
sortindex = np.argsort(df.isnull().sum(axis=0)).values.tolist()

for i in removal_list:
    sortindex.remove(i)

for i in sortindex:
    #构建我们的新特征矩阵和新标签
    df = X_missing_reg
    fillc = df.iloc[:, i]
    df = df.iloc[:, df.columns != i]
    
    #在新的特征矩阵中，对含有缺失值的列，进行0的填补
    df_0 = SimpleImputer(missing_values=np.nan, strategy="constant", fill_value=0).fit_transform(df)
    
    #找出我们的训练集和测试集
    Ytrain = fillc[fillc.notnull()]
    Ytest = fillc[fillc.isnull()]
    Xtrain = df_0[Ytrain.index, :]
    Xtest = df_0[Ytest.index, :]
    
    #用随机森林回归来填补缺失值
    lgbR = LGBMRegressor(n_estimators=100, boosting_type='goss')
    lgbR = lgbR.fit(Xtrain, Ytrain)
    Ypredict = lgbR.predict(Xtest)
    
    #将填补好的特征返回到我们的原始的特征矩阵中
    X_missing_reg.iloc[X_missing_reg.iloc[:, i].isnull(), i] = Ypredict
    
    
# lightGBM categorical variables filling

dfc = data[["lithology", "landform", "soil_textu", "landcover"]]

# nodata value processing
dfc[dfc.loc[:, "landcover"] == 127] = np.nan
dfc[dfc.loc[:, "soil_textu"] == 0] = np.nan
dfc[dfc.loc[:, "landform"] == 0] = np.nan
dfc[dfc.loc[:, "lithology"] == 127] = np.nan
dfc[dfc==-9999] = np.nan
dfc[dfc==-32768] = np.nan

# 按照缺失值多少进行排序
X_missing_clf = dfc.copy()
removal_list = []
for c in range(len(list(dfc.columns))):
    if dfc.iloc[:, c].isnull().sum() == 0:
        removal_list.append(c)
sortindex = np.argsort(dfc.isnull().sum(axis=0)).values.tolist()

for i in removal_list:
    sortindex.remove(i)
    
for i in sortindex:
    #构建我们的新特征矩阵和新标签
    df = X_missing_clf
    fillc = df.iloc[:, i]
    df = df.iloc[:, df.columns != i]
    
    #在新的特征矩阵中，对含有缺失值的列，进行0的填补
    df_0 = SimpleImputer(missing_values=np.nan, strategy="constant", fill_value=0).fit_transform(df)
    
    #找出我们的训练集和测试集
    Ytrain = fillc[fillc.notnull()]
    Ytest = fillc[fillc.isnull()]
    Xtrain = df_0[Ytrain.index, :]
    Xtest = df_0[Ytest.index, :]
    
    #用随机森林回归来填补缺失值
    lgb = LGBMClassifier(n_estimators=100, boosting_type='goss')
    lgb = lgb.fit(Xtrain, Ytrain)
    Ypredict = lgb.predict(Xtest)
    
    #将填补好的特征返回到我们的原始的特征矩阵中
    X_missing_clf.iloc[X_missing_clf.iloc[:, i].isnull(), i] = Ypredict
    

# export the result
pd.concat([X_missing_reg, X_missing_clf, data.label], axis=1).to_excel(r"E:\l3\dynamic landslide prediction\feature_matrix\training_data_lgb_processed.xlsx")


