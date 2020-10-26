# ele200PUData_v11Geom_layer_,

import glob
import sys

import pandas as pd
import shutil

jobN = sys.argv[1] 
sample = sys.argv[2] 

layers = [1,3,5,7,9,11,13,15,17,19,21,23,25,27,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50]

totalEnergy = None


import os

for layer in layers:
    ##copy locally
    
    ## untar
    try:
        os.system(f'tar -zxf {sample}Data_v11Geom_layer_{layer}_job{jobN}.tgz')
    except:
        continue

    ##get data
    directory = f'{sample}Data_v11Geom_layer_{layer}'

    files = glob.glob(f'{sample}Data_v11Geom_layer_{layer}/*/SimEnergyTotal.csv')
    print(layer)
    for f in files:
        if totalEnergy is None:
            totalEnergy = pd.read_csv(f,index_col='entry')
        else:
            df = pd.read_csv(f,index_col='entry')
            df = totalEnergy.merge(df,left_index=True,right_index=True,how='outer').fillna(0)
            df['SimEnergyTotal'] = df.sum(axis=1)
            totalEnergy = df[['SimEnergyTotal']]
    try:
        shutil.rmtree(f'{sample}Data_v11Geom_layer_{layer}')
    except:
        continue

print(totalEnergy)
totalEnergy.to_csv("totalEventEnergy.csv")
