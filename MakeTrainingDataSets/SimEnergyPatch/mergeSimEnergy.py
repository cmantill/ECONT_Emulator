import pandas as pd
import os
import glob

import sys
import shutil

jobN=sys.argv[1]
sample=sys.argv[2]

df_totalEnergy = pd.read_csv('totalEventEnergy.csv',index_col='entry')

layers = [1,3,5,7,9,11,13,15,17,19,21,23,25,27,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50]

for layer in layers:
    ## untar
    if os.path.exists(f'tar -zxf {sample}Data_v11Geom_layer_{layer}_job{jobN}.tgz'):
        os.system(f'tar -zxf {sample}Data_v11Geom_layer_{layer}_job{jobN}.tgz')
    except:
        print(f'tar file not found, skipping layer {layer}')
        continue

    ##get data
    directory = f'{sample}Data_v11Geom_layer_{layer}'

    waferDirs = glob.glob(f'{sample}Data_v11Geom_layer_{layer}/*')
    print(layer)
    for f in waferDirs:
        try:
            df_CALQ = pd.read_csv(f'{f}/CALQ.csv',index_col='entry')
            df_SimEnergy = pd.read_csv(f'{f}/SimEnergyTotal.csv',index_col='entry')
        except:
            continue

        df_CALQ['SimEnergyTotal'] = df_SimEnergy['SimEnergyTotal']
        df_CALQ['EventSimEnergyTotal'] = df_totalEnergy['SimEnergyTotal']
        df_CALQ['SimEnergyFraction'] = df_SimEnergy['SimEnergyTotal'] / df_totalEnergy['SimEnergyTotal']


        df_CALQ.to_csv(f'{f}/CALQ.csv')

    os.system(f'tar -zcf {sample}Data_v11Geom_layer_{layer}_job{jobN}.tgz {sample}Data_v11Geom_layer_{layer}')

    shutil.rmtree(f'{sample}Data_v11Geom_layer_{layer}')
