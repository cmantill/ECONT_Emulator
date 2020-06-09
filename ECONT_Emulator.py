import uproot
import argparse
import os

# import pandas as pd
# import numpy as np
# import time

# import pickle

# import gc

from linkAllocation import linksPerLayer


from LoadData_ePortRX import loadMetaData, loadEportRXData, splitEportRXData
from MuxFixCalib import getMuxRegisters, Mux, FloatToFix, getCalibrationRegisters_Thresholds, Calibrate
from Algorithms import makeCHARGEQ, ThresholdSum, BestChoice, SuperTriggerCell, Repeater, Algorithms
from Formatter import Format_Threshold_Sum, Format_BestChoice, Format_SuperTriggerCell, Format_Repeater
from BufferBlock import Buffer


def main(inputFile, outputDir, ePortTX, STC_Type, Tx_Sync_Word, nDropBits):
    subdet,layer,wafer,isHDM,geomVersion = loadMetaData(inputDir)
    df_ePortRxDataGroup, df_BX_CNT = loadEportRXData(inputDir)

    if outputDir is None:
        outputDir = inputDir

    df_ePortRxDataGroup.to_csv(f'{outputDir}/ePortRxDataGroup.csv',index=True)
    df_BX_CNT.to_csv(f'{outputDir}/BX_CNT.csv',index=True)

    columns = [f'ePortRxDataGroup_{i}' for i inrange(12)]
    df_Mux_in = splitEportRXData(df_ePortRxDataGroup[columns])
    del df_ePortRxDataGroup
    Mux_Select = getMuxRegisters()
    df_Mux_out = Mux(df_Mux_in, Mux_Select)
    df_F2F = FloatToFix(df_Mux_out, isHDM)
    CALVALUE_Registers, THRESHV_Registers = getCalibrationRegisters_Thresholds(2,33,901,'v10')
    df_CALQ = Calibrate(df_F2F, CALVALUE_Registers)

    df_Mux_in.to_csv(f'{outputDir}/Mux_in.csv',index=True)
    df_Mux_out.to_csv(f'{outputDir}/Mux_out.csv',index=True)
    df_F2F.to_csv(f'{outputDir}/F2F.csv',index=True)
    df_CALQ.to_csv(f'{outputDir}/CALQ.csv',index=True)
    del df_Mux_in
    del df_Mux_out
    del df_F2F

    if nDropBits==-1:
        DropLSB=3 if isHDM else 1
    else:
        DropLSB = nDropBits

    TxSyncWord=int(Tx_Sync_Word,2)
    EPORTTX_NUMEN=ePortTX
    STC_TYPE=STC_Type


    pd.DataFrame([Mux_Select], columns=[f'Mux_Select_{i}' for i in range(48)],index=df_Mux_in.index).to_csv(f'{outputDir}/Mux_Select.csv', index=True)
    pd.DataFrame([CALVALUE_Registers], columns=[f'CALVALUE_{i}' for i in range(48)],index=df_Mux_in.index).to_csv(f'{outputDir}/CALVALUE.csv', index=True)
    pd.DataFrame([THRESHV_Registers], columns=[f'THRESHV_{i}' for i in range(48)],index=df_Mux_in.index).to_csv(f'{outputDir}/THRESHV.csv', index=True)
    pd.DataFrame([[DropLSB]], columns=['DropLSB'],index=df_Mux_in.index).to_csv(f'{outputDir}/DropLSB.csv', index=True)
    pd.DataFrame([[int(isHDM)]], columns=['HighDensity'],index=df_Mux_in.index).to_csv(f'{outputDir}/HighDensity.csv', index=True)
    pd.DataFrame([[TxSyncWord]], columns=['TxSyncWord'],index=df_Mux_in.index).to_csv(f'{outputDir}/TxSyncWord.csv', index=True)
    pd.DataFrame([[EPORTTX_NUMEN]], columns=['EPORTTX_NUMEN'],index=df_Mux_in.index).to_csv(f'{outputDir}/EPORTTX_NUMEN.csv', index=True)
    pd.DataFrame([[STC_TYPE]], columns=['STC_TYPE'],index=df_Mux_in.index).to_csv(f'{outputDir}/STC_TYPE.csv', index=True)



    df_Threshold_Sum, df_BestChoice, df_SuperTriggerCell, df_Repeater = Algorithms(df_CALQ, THRESHV_Registers, DropLSB)
    del df_CALQ


    df_Threshold_Sum.to_csv(f'{outputDir}/Threshold_Sum.csv',index=True)
    df_BestChoice.to_csv(f'{outputDir}/BestChoice.csv',index=True)
    df_SuperTriggerCell.to_csv(f'{outputDir}/SuperTriggerCell.csv',index=True)
    df_Repeater.to_csv(f'{outputDir}/Repeater.csv',index=True)



    df_Format_TS = Format_Threshold_Sum(df_Threshold_Sum, df_BX_CNT, TxSyncWord)
    df_BufferOutput_TS  = Buffer(df_Format_TS,  EPORTTX_NUMEN, EPORTTX_NUMEN*12*2, EPORTTX_NUMEN*12*2-25, 25)
    del df_Threshold_Sum
    df_Format_TS.to_csv(f'{outputDir}/Format_TS.csv',index=True)
    df_Buffer_TS.to_csv(f'{outputDir}/Buffer_TS.csv',index=True)
    del df_Format_TS
    del df_Buffer_TS

    df_Format_BC = Format_BestChoice(df_BestChoice, EPORTTX_NUMEN, df_BX_CNT, TxSyncWord)
    df_BufferOutput_BC  = Buffer(df_Format_BC,  EPORTTX_NUMEN, EPORTTX_NUMEN*12*2, EPORTTX_NUMEN*12*2-25, 25)
    del df_BestChoice
    df_Format_BC.to_csv(f'{outputDir}/Format_BC.csv',index=True)
    df_Buffer_BC.to_csv(f'{outputDir}/Buffer_BC.csv',index=True)
    del df_Format_BC
    del df_Buffer_BC

    df_Format_STC = Format_SuperTriggerCell(df_SuperTriggerCell, STC_TYPE, EPORTTX_NUMEN, df_BX_CNT, TxSyncWord)
    df_BufferOutput_STC = Buffer(df_Format_STC, EPORTTX_NUMEN, EPORTTX_NUMEN*12*2, EPORTTX_NUMEN*12*2-25, 25)
    del df_STC
    df_Format_STC.to_csv(f'{outputDir}/Format_STC.csv',index=True)
    df_Buffer_STC.to_csv(f'{outputDir}/Buffer_STC.csv',index=True)
    del df_Format_STC
    del df_Buffer_STC

    df_Format_RPT = Format_Repeater(df_Repeater, df_BX_CNT, TxSyncWord)    
    df_BufferOutput_RPT = Buffer(df_Format_RPT, EPORTTX_NUMEN, EPORTTX_NUMEN*12*2, EPORTTX_NUMEN*12*2-25, 25)
    del df_Repeater
    df_Format_RPT.to_csv(f'{outputDir}/Format_RPT.csv',index=True)
    df_Buffer_RPT.to_csv(f'{outputDir}/Buffer_RPT.csv',index=True)
    del df_Format_RPT
    del df_Buffer_RPT

    


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-i','--input', dest='inputFile', help='input file name')
    parser.add_argument('-o','--output', dest='outputDir', default=None, help='outputDirectory, if different than directory of input file')
    parser.add_argument('--links', '--eLinks','--ePortTx', dest=ePortTx, default=-1, type=int help='number of ePortTx links, if -1, will use value from eLink mapping')
    parser.add_argument('--STC', '--STC_Type', dest=STC_Type, default=-1, type-int, help='STC Type to use, if -1, STC_4_9 for HDM, STC_16_9 for LDM')
    parser.add_argument('--TxSyncWord', dest=TxSyncWord, default='01100110011', help='11-bit Sync word to use for empty words')
    parser.add_argument('--DropLSB', dest=nDropBits, default=-1, type=int, help='Number of LSB to drop when encoding, if -1 HDM will use 3, LDM will use 1')

    
    main(**vars(args))
