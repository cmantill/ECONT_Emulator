import argparse
import os

import pandas as pd
import numpy as np
# import time

# import pickle

# import gc

from Utils.linkAllocation import linksPerLayer

saveIndex=False

from ASICBlocks.LoadData_ePortRX import loadMetaData, loadEportRXData, splitEportRXData
from ASICBlocks.MuxFixCalib import getMuxRegisters, Mux, FloatToFix, getCalibrationRegisters_Thresholds, Calibrate
from ASICBlocks.Algorithms import makeCHARGEQ, ThresholdSum, BestChoice, SuperTriggerCell, Repeater, Algorithms
from ASICBlocks.Formatter import Format_Threshold_Sum, Format_BestChoice, Format_SuperTriggerCell, Format_Repeater
from ASICBlocks.BufferBlock import Buffer


def runEmulator(inputDir, outputDir=None, ePortTx=-1, STC_Type=-1, Tx_Sync_Word='01100110011', nDropBits=-1, Use_Sum=False, StopAtAlgoBlock=False, AEMuxOrdering=False, SimEnergyFlag=False, MuxRegisters=None, CalRegisters=None, HDMFlag=None, ThresholdRegisters=None, Buff_T1=None, Buff_T2=None, Buff_T3=None):
    if inputDir[-1]=="/": inputDir = inputDir[:-1]
    subdet,layer,wafer,isHDM,geomVersion = loadMetaData(inputDir)
    df_ePortRxDataGroup, df_BX_CNT, df_SimEnergyStatus, df_linkReset = loadEportRXData(inputDir,SimEnergyFlag)

    if not HDMFlag is None:
        isHDM=False
        if HDMFlag in ['1',1,'True',True]:
            isHDM=True
    if outputDir is None:
        outputDir = inputDir

    if not os.path.exists(outputDir):
        os.mkdir(outputDir)
    print('MuxFixCalib')
    columns = [f'ePortRxDataGroup_{i}' for i in range(12)]
    df_Mux_in = splitEportRXData(df_ePortRxDataGroup[columns])
    Mux_Select = getMuxRegisters(AEMuxOrdering, MuxRegisters)
    df_Mux_out = Mux(df_Mux_in, Mux_Select)

    df_F2F = FloatToFix(df_Mux_out, isHDM)
    CALVALUE_Registers, THRESHV_Registers = getCalibrationRegisters_Thresholds(subdet, layer, wafer, geomVersion, tpgNtupleMapping=AEMuxOrdering, CalRegisters=CalRegisters, ThresholdRegisters=ThresholdRegisters)
    df_CALQ = Calibrate(df_F2F, CALVALUE_Registers)

    if SimEnergyFlag:
        df_CALQ = df_CALQ.merge(df_SimEnergyStatus,left_index=True, right_index=True,how='left')

        df_CALQ['SimEnergyFraction'] = df_CALQ['SimEnergyTotal']/df_CALQ['EventSimEnergy']

        df_CALQ.to_csv(f'{outputDir}/CALQ.csv',index=saveIndex)
        df_CALQ.drop('entry',axis=1,inplace=True)
        df_CALQ.drop('SimEnergyTotal',axis=1,inplace=True)
        df_CALQ.drop('EventSimEnergy',axis=1,inplace=True)
        df_CALQ.drop('SimEnergyFraction',axis=1,inplace=True)
    else:
        df_CALQ.to_csv(f'{outputDir}/CALQ.csv',index=saveIndex)

    pd.DataFrame([Mux_Select], columns=[f'MUX_SELECT_{i}' for i in range(48)],index=df_CALQ.index).to_csv(f'{outputDir}/Mux_Select.csv', index=saveIndex)
    pd.DataFrame([CALVALUE_Registers], columns=[f'CALVALUE_{i}' for i in range(48)],index=df_CALQ.index).to_csv(f'{outputDir}/CALVALUE.csv', index=saveIndex)
    pd.DataFrame([[int(isHDM)]], columns=['HIGH_DENSITY'],index=df_CALQ.index).to_csv(f'{outputDir}/HighDensity.csv', index=saveIndex)

    df_BX_CNT.to_csv(f'{outputDir}/BX_CNT.csv',index=saveIndex)
    df_ePortRxDataGroup.to_csv(f'{outputDir}/ePortRxDataGroup.csv',index=saveIndex)
    df_Mux_in.to_csv(f'{outputDir}/Mux_in.csv',index=saveIndex)
    df_Mux_out.to_csv(f'{outputDir}/Mux_out.csv',index=saveIndex)
    df_F2F.to_csv(f'{outputDir}/F2F.csv',index=saveIndex)
    del df_ePortRxDataGroup
    del df_Mux_in
    del df_Mux_out
    del df_F2F


    if StopAtAlgoBlock: return

    print('Algorithm')

    if nDropBits==-1:
        DropLSB=3 if isHDM else 1
    else:
        DropLSB = nDropBits

    TxSyncWord=int(Tx_Sync_Word,2)
    EPORTTX_NUMEN=ePortTx
    if EPORTTX_NUMEN==-1:
        if geomVersion in ['v11','v10']:
            u = int(round(wafer/100.))
            v = wafer-u*100
            linkCounts = pd.read_csv('Utils/ModuleLinkSummary.csv',index_col=['Layer','ModU','ModV'])
            EPORTTX_NUMEN = linkCounts.loc[layer,u,v].ECONT_eTX
            print(f'Using EPORTTX_NUMEN={EPORTTX_NUMEN}')
        else:
            print('EPORTTX_NUMEN must be specified for v9 geometry, cannot look up')
            print('Using EPORTTX_NUMEN=4')
            EPORTTX_NUMEN=4

    print(f'Using EPORTTX_NUMEN={EPORTTX_NUMEN}')
    if STC_Type==-1:
        STC_TYPE=0 if isHDM else 1
    else:
        STC_TYPE = STC_Type


    pd.DataFrame([THRESHV_Registers], columns=[f'THRESHV_{i}' for i in range(48)],index=df_CALQ.index).to_csv(f'{outputDir}/THRESHV.csv', index=saveIndex)
    pd.DataFrame([[DropLSB]], columns=['DROP_LSB'],index=df_CALQ.index).to_csv(f'{outputDir}/DropLSB.csv', index=saveIndex)
    pd.DataFrame([[TxSyncWord]], columns=['TXSYNCWORD'],index=df_CALQ.index).to_csv(f'{outputDir}/TxSyncWord.csv', index=saveIndex)
    pd.DataFrame([[EPORTTX_NUMEN]], columns=['EPORTTX_NUMEN'],index=df_CALQ.index).to_csv(f'{outputDir}/EPORTTX_NUMEN.csv', index=saveIndex)
    pd.DataFrame([[STC_TYPE]], columns=['STC_TYPE'],index=df_CALQ.index).to_csv(f'{outputDir}/STC_TYPE.csv', index=saveIndex)
    pd.DataFrame([[Use_Sum]], columns=['USE_SUM'],index=df_CALQ.index).to_csv(f'{outputDir}/Use_Sum.csv', index=saveIndex)

    if Buff_T1 is not None:
        BUFFER_THRESHOLD_T1 = Buff_T1
    else:
        BUFFER_THRESHOLD_T1 = EPORTTX_NUMEN*13*2
    if Buff_T2 is not None:
        BUFFER_THRESHOLD_T2 = Buff_T2
    else:
        BUFFER_THRESHOLD_T2 = EPORTTX_NUMEN*13*2-24
    if Buff_T3 is not None:
        BUFFER_THRESHOLD_T3 = Buff_T3
    else:
        BUFFER_THRESHOLD_T3 = 25



    pd.DataFrame([[int(BUFFER_THRESHOLD_T1)]], columns=['BUFFER_THRESHOLD_T1'],index=df_CALQ.index).to_csv(f'{outputDir}/Buffer_Threshold_T1.csv', index=saveIndex)
    pd.DataFrame([[int(BUFFER_THRESHOLD_T2)]], columns=['BUFFER_THRESHOLD_T2'],index=df_CALQ.index).to_csv(f'{outputDir}/Buffer_Threshold_T2.csv', index=saveIndex)
    pd.DataFrame([[int(BUFFER_THRESHOLD_T3)]], columns=['BUFFER_THRESHOLD_T3'],index=df_CALQ.index).to_csv(f'{outputDir}/Buffer_Threshold_T3.csv', index=saveIndex)


    df_Threshold_Sum, df_BestChoice, df_SuperTriggerCell, df_Repeater = Algorithms(df_CALQ, THRESHV_Registers, DropLSB)


    df_Threshold_Sum.to_csv(f'{outputDir}/Threshold_Sum.csv',index=saveIndex)
    df_BestChoice.to_csv(f'{outputDir}/BestChoice.csv',index=saveIndex)
    df_SuperTriggerCell.to_csv(f'{outputDir}/SuperTriggerCell.csv',index=saveIndex)
    df_Repeater.to_csv(f'{outputDir}/Repeater.csv',index=saveIndex)

    # try:
    #     df_linkReset = pd.read_csv(f'{inputDir}/LinkResetEconT.csv')
    # except:
    #     df_linkReset = pd.DataFrame({'LINKRESETECONT':0},index=df_CALQ.index)

    del df_CALQ

    print('Formatter/Buffer Threshold-Sum')
    df_Format_TS = Format_Threshold_Sum(df_Threshold_Sum, df_BX_CNT, TxSyncWord, Use_Sum, EPORTTX_NUMEN, df_linkReset)
    df_BufferOutput_TS  = Buffer(df_Format_TS,  EPORTTX_NUMEN, BUFFER_THRESHOLD_T1, BUFFER_THRESHOLD_T2, BUFFER_THRESHOLD_T3)
    del df_Threshold_Sum
    df_Format_TS.to_csv(f'{outputDir}/Format_TS.csv',index=saveIndex)
    df_BufferOutput_TS.to_csv(f'{outputDir}/Buffer_TS.csv',index=saveIndex)
    del df_Format_TS
    del df_BufferOutput_TS

    print('Formatter/Buffer Best Choice')
    df_Format_BC = Format_BestChoice(df_BestChoice, EPORTTX_NUMEN, df_BX_CNT, TxSyncWord, Use_Sum, df_linkReset)
    df_BufferOutput_BC  = Buffer(df_Format_BC,  EPORTTX_NUMEN, BUFFER_THRESHOLD_T1, BUFFER_THRESHOLD_T2, BUFFER_THRESHOLD_T3)
    del df_BestChoice
    df_Format_BC.to_csv(f'{outputDir}/Format_BC.csv',index=saveIndex)
    df_BufferOutput_BC.to_csv(f'{outputDir}/Buffer_BC.csv',index=saveIndex)
    del df_Format_BC
    del df_BufferOutput_BC

    print('Formatter/Buffer STC')
    df_Format_STC = Format_SuperTriggerCell(df_SuperTriggerCell, STC_TYPE, EPORTTX_NUMEN, df_BX_CNT, TxSyncWord, df_linkReset)
    df_BufferOutput_STC = Buffer(df_Format_STC, EPORTTX_NUMEN, BUFFER_THRESHOLD_T1, BUFFER_THRESHOLD_T2, BUFFER_THRESHOLD_T3)
    del df_SuperTriggerCell
    df_Format_STC.to_csv(f'{outputDir}/Format_STC.csv',index=saveIndex)
    df_BufferOutput_STC.to_csv(f'{outputDir}/Buffer_STC.csv',index=saveIndex)
    del df_Format_STC
    del df_BufferOutput_STC

    print('Formatter/Buffer Repeater')
    df_Format_RPT = Format_Repeater(df_Repeater, df_BX_CNT, TxSyncWord, EPORTTX_NUMEN, df_linkReset)
    df_BufferOutput_RPT = Buffer(df_Format_RPT, EPORTTX_NUMEN, BUFFER_THRESHOLD_T1, BUFFER_THRESHOLD_T2, BUFFER_THRESHOLD_T3)
    del df_Repeater
    df_Format_RPT.to_csv(f'{outputDir}/Format_RPT.csv',index=saveIndex)
    df_BufferOutput_RPT.to_csv(f'{outputDir}/Buffer_RPT.csv',index=saveIndex)
    del df_Format_RPT
    del df_BufferOutput_RPT

    


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-i','--input', dest='inputDir', help='input directory name')
    parser.add_argument('-o','--output', dest='outputDir', default=None, help='outputDirectory, if different than directory of input file')
    parser.add_argument('--links', '--eLinks','--ePortTx', dest="ePortTx", default=-1, type=int, help='number of ePortTx links, if -1, will use value from eLink mapping')
    parser.add_argument('--STC', '--STC_Type', dest="STC_Type", default=-1, type=int, help='STC Type to use, if -1, STC_4_9 for HDM, STC_16_9 for LDM')
    parser.add_argument('--TxSyncWord', dest="Tx_Sync_Word", default='01100110011', help='11-bit Sync word to use for empty words')
    parser.add_argument('--DropLSB', dest="nDropBits", default=-1, type=int, help='Number of LSB to drop when encoding, if -1 HDM will use 3, LDM will use 1')
    parser.add_argument('--UseSum', dest="Use_Sum", default=False, action="store_true", help='Send only sum of all TC in module sum for TS and BC algorithms instead of sum of only TC not transmitted')
    parser.add_argument('--NoAlgo', dest="StopAtAlgoBlock", default=False, action="store_true", help='Only run the code through the MuxFixCalib block, producing the CALQ files and nothing after')
    parser.add_argument('--AEMuxOrdering', dest="AEMuxOrdering", default=False, action="store_true", help='Use MUX settings to use ordering from autoencoder')
    parser.add_argument('--SimEnergyFlag', dest="SimEnergyFlag", default=False, action="store_true", help='Add flag of whether sim energy is present to the CALQ dataframe')
    parser.add_argument('--calibration', default = None, dest="CalRegisters", help="Value of calibrations to use")
    parser.add_argument('--threshold', default = None, dest="ThresholdRegisters", help="Value of thresholds to use")
    parser.add_argument('--T1', type=int, default = None, dest="Buff_T1", help="Buffer threshold T1")
    parser.add_argument('--T2', type=int, default = None, dest="Buff_T2",help="Buffer threshold T2")
    parser.add_argument('--T3', type=int, default = None, dest="Buff_T3",help="Buffer threshold T3")

    args = parser.parse_args()
    
    runEmulator(**vars(args))
