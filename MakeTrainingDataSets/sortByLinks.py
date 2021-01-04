import pandas as pd
import argparse
import re
import os

import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument('-i','--input', dest='input', required=True, help='input dir file name')
parser.add_argument('--name', dest='extraName', default="ttbar_v11_eolNoise", help='input dir file name')
parser.add_argument('-N', dest='NSplit', default=-1, type=int, help='number of output files to split into')
parser.add_argument('--job', dest='job', default=-1, type=int, help='job number of input/output')
args = parser.parse_args()

inputDir = args.input

waferInfo= inputDir.split('wafer_')[-1]
regex = re.compile('D(\d+)L(\d+)U(-?\d+)V(-?\d+)')
regex.match(waferInfo).groups()
subdet,layer,u,v = [int(i) for i in regex.match(waferInfo).groups()]
print(subdet,layer,u,v)

dfInput = pd.read_csv(f'{inputDir}/CALQ.csv')

if 'Orbit' in dfInput.columns:
    dfInput.set_index(['Orbit','BX'],inplace=True)
else:
    dfInput['index'] = np.arange(len(dfInput))
    dfInput.set_index('index',inplace=True)


#dfInput['entry'] = pd.read_csv(f'{inputDir}/EPORTRX_output.csv').entry.values
dfInput['subdet'] = subdet
dfInput['layer'] = layer
dfInput['waferu'] = u
dfInput['waferv'] = v

linkCount = pd.read_csv('Utils/ModuleLinkSummary.csv',index_col=['Layer','ModU','ModV'])

dfInput['HD_LD'] = linkCount.loc[layer,u,v].HD_LD
dfInput['ModType'] = linkCount.loc[layer,u,v].ModType

signalAllocation = [0,2,0,2,0,2,0,4,0,5,0,4,0,3,0,2,0,2,0,2,0,2,0,2,0,2,0,2,0,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2,2]

linkPUAllocation = int(linkCount.loc[layer,u,v].ECONT_eTX)
linkSignalAllocation = signalAllocation[layer]

mask = dfInput[[f'CALQ_{i}' for i in range(48)]].sum(axis=1)>0
print(f'Dropping {len(dfInput)-sum(mask)} out of {len(dfInput)} events for having 0 charge')
dfInput = dfInput[mask]

indexList = dfInput.index.values.copy()
np.random.shuffle(indexList)

columns = ['entry','CALQ_0','CALQ_1','CALQ_2','CALQ_3','CALQ_4','CALQ_5','CALQ_6','CALQ_7','CALQ_8','CALQ_9','CALQ_10','CALQ_11','CALQ_12','CALQ_13','CALQ_14','CALQ_15','CALQ_16','CALQ_17','CALQ_18','CALQ_19','CALQ_20','CALQ_21','CALQ_22','CALQ_23','CALQ_24','CALQ_25','CALQ_26','CALQ_27','CALQ_28','CALQ_29','CALQ_30','CALQ_31','CALQ_32','CALQ_33','CALQ_34','CALQ_35','CALQ_36','CALQ_37','CALQ_38','CALQ_39','CALQ_40','CALQ_41','CALQ_42','CALQ_43','CALQ_44','CALQ_45','CALQ_46','CALQ_47','SimEnergyTotal','EventSimEnergy','SimEnergyFraction','subdet','layer','waferu','waferv','HD_LD','ModType']

if linkPUAllocation>0:

    if args.NSplit==-1 or args.job!=-1:
        fName = f"{args.extraName}_TrainingData_PUAllocation/nElinks_{linkPUAllocation}/{args.extraName}_Layer{layer}_{linkPUAllocation}Links.csv"
        if args.job != -1:
            fName = f"{args.extraName}_TrainingData_PUAllocation/nElinks_{linkPUAllocation}/{args.extraName}_Layer{layer}_{linkPUAllocation}Links_{args.job}.csv"
        if not os.path.exists(fName):
            dfInput[columns].to_csv(fName,index=None)
        else:
            dfInput[columns].to_csv(fName,index=None,mode='a',header=None)
    else:

        eventsPerSplit = len(dfInput)/args.NSplit
        for i in range(args.NSplit):
            fName = f"{args.extraName}_TrainingData_PUAllocation/nElinks_{linkPUAllocation}/{args.extraName}_Layer{layer}_{linkPUAllocation}Links_{i+1}of{args.NSplit}.csv"

            events = indexList[int(i*eventsPerSplit):int((i+1)*eventsPerSplit)]
            if not os.path.exists(fName):
                dfInput[columns].loc[events].to_csv(fName,index=False)
            else:
                dfInput[columns].loc[events].to_csv(fName,index=None,mode='a',header=None)


if linkSignalAllocation>0:

    fName = f"{args.extraName}_TrainingData_SignalAllocation/nElinks_{linkSignalAllocation}/{args.extraName}_Layer{layer}_{linkSignalAllocation}Links.csv"

    if args.NSplit==-1 or args.job != -1:
        fName = f"{args.extraName}_TrainingData_SignalAllocation/nElinks_{linkSignalAllocation}/{args.extraName}_Layer{layer}_{linkSignalAllocation}Links.csv"
        if args.job != -1:
            fName = f"{args.extraName}_TrainingData_SignalAllocation/nElinks_{linkSignalAllocation}/{args.extraName}_Layer{layer}_{linkSignalAllocation}Links_{args.job}.csv"
        if not os.path.exists(fName):
            dfInput[columns].to_csv(fName,index=None)
        else:
            dfInput[columns].to_csv(fName,index=None,mode='a',header=None)
    else:
        eventsPerSplit = len(dfInput)/args.NSplit
        for i in range(args.NSplit):
            fName = f"{args.extraName}_TrainingData_SignalAllocation/nElinks_{linkSignalAllocation}/{args.extraName}_Layer{layer}_{linkSignalAllocation}Links_{i+1}of{args.NSplit}.csv"

            events = indexList[int(i*eventsPerSplit):int((i+1)*eventsPerSplit)]

            if not os.path.exists(fName):
                dfInput[columns].loc[events].to_csv(fName,index=False)
            else:
                dfInput[columns].loc[events].to_csv(fName,index=None,mode='a',header=None)
