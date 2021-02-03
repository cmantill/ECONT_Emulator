import uproot
import argparse
import os

import pandas as pd
import numpy as np

from ASICBlocks.LoadData_ePortRX import loadMetaData, loadEportRXData, splitEportRXData
from ASICBlocks.MuxFixCalib import getMuxRegisters, Mux, FloatToFix, getCalibrationRegisters_Thresholds, Calibrate
from ASICBlocks.Algorithms import makeCHARGEQ, ThresholdSum, BestChoice, SuperTriggerCell, Repeater, Algorithms
from ASICBlocks.Formatter import Format_Threshold_Sum, Format_BestChoice, Format_SuperTriggerCell, Format_Repeater, Format_Autoencoder
from ASICBlocks.BufferBlock import Buffer

def newFormat(x):
    return format(x,'#018b')[2:]

binV=np.vectorize(newFormat)

def getRegister(inputFile):
    value = np.unique(pd.read_csv(inputFile,skipinitialspace=True).values)
    if not len(value)==1:
        print('Only one register type at a time is supported')
        print(f'Multiple values found in file {inputFile}')
        print('Exitting')
        exit()
    return value[0]

def runVerification(inputDir, outputDir, ASICBlock, verbose=False, algo=None):
    if ASICBlock=='Algorithm':

        if algo is None:
            algo=getRegister(f'{inputDir}/Algorithm_Input_Type.csv')

        df_CALQ = pd.read_csv(f'{inputDir}/Algorithm_Input_CalQ.csv',skipinitialspace=True)
        df_DropLSB = pd.read_csv(f'{inputDir}/Algorithm_Input_DropLSB.csv',skipinitialspace=True)
        df_DropLSB.loc[df_DropLSB.DROP_LSB>4] = 0
        df_Header = pd.read_csv(f'{inputDir}/Algorithm_Input_Header.csv',skipinitialspace=True)
        df_Threshold = pd.read_csv(f'{inputDir}/Algorithm_Input_Threshold.csv',skipinitialspace=True)

        if algo==0: #threshold sum
            latency=1
            df_Emulator=ThresholdSum(df_CALQ, df_Threshold, df_DropLSB)

            df_AddrMap = pd.read_csv(f'{inputDir}/Algorithm_Output_AddrMap.csv',skipinitialspace=True)
            df_ChargeQ = pd.read_csv(f'{inputDir}/Algorithm_Output_ChargeQ.csv',skipinitialspace=True)
            df_Sum = pd.read_csv(f'{inputDir}/Algorithm_Output_Sum.csv',skipinitialspace=True)
            df_SumNotTransmitted = pd.read_csv(f'{inputDir}/Algorithm_Output_SumNotTransmitted.csv',skipinitialspace=True)
            df_Comparison = df_AddrMap.merge(df_ChargeQ, left_index=True, right_index=True).merge(df_Sum, left_index=True, right_index=True).merge(df_SumNotTransmitted, left_index=True, right_index=True)

        elif algo==1: #STC
            latency = 1
            df_Emulator = SuperTriggerCell(df_CALQ, df_DropLSB)

            df_XTC4_9 = pd.read_csv(f'{inputDir}/Algorithm_Output_XTC4_9_Sum.csv',skipinitialspace=True)
            df_XTC16_9 = pd.read_csv(f'{inputDir}/Algorithm_Output_XTC16_9_Sum.csv',skipinitialspace=True)
            df_XTC4_7 = pd.read_csv(f'{inputDir}/Algorithm_Output_XTC4_7_Sum.csv',skipinitialspace=True)
            df_MAX4_Addr = pd.read_csv(f'{inputDir}/Algorithm_Output_MAX4_Addr.csv',skipinitialspace=True)
            df_MAX16_Addr= pd.read_csv(f'{inputDir}/Algorithm_Output_MAX16_Addr.csv',skipinitialspace=True)

            df_Comparison = df_XTC4_9.merge(df_XTC16_9,left_index=True, right_index=True).merge(df_XTC4_7,left_index=True, right_index=True).merge(df_MAX4_Addr,left_index=True, right_index=True).merge(df_MAX16_Addr,left_index=True, right_index=True)


        elif algo==2: #BC
            latency = 2
            df_Emulator = BestChoice(df_CALQ, df_DropLSB)

            df_BC_Charge = pd.read_csv(f'{inputDir}/Algorithm_Output_BC_Charge.csv',skipinitialspace=True)
            df_BC_TC_map = pd.read_csv(f'{inputDir}/Algorithm_Output_BC_TC_map.csv',skipinitialspace=True)

            df_Comparison = df_BC_Charge.merge(df_BC_TC_map,left_index=True, right_index=True)

        elif algo==3: #RPT
            latency = 1
            df_Emulator = Repeater(df_CALQ, df_DropLSB)

            df_Comparison = pd.read_csv(f'{inputDir}/Algorithm_Output_RepeaterQ.csv',skipinitialspace=True)

        elif algo==4: #AE
            latency=1
            print('AE not yet implemented')
            exit()
        else:
            print('unknown algorithm type')
            exit()
            

            
    elif ASICBlock=='Formatter':
        df_BX_CNT = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_Bx_Cnt_In.csv',skipinitialspace=True)
        df_BX_CNT.columns = ['BX_CNT']

        algo = getRegister(f'{inputDir}/Formatter_Buffer_Input_Algorithm_Type.csv')
        EPortTx_NumEn = getRegister(f'{inputDir}/Formatter_Buffer_Input_EPortTx_NumEn.csv')
        STC_Type = getRegister(f'{inputDir}/Formatter_Buffer_Input_STC_Type.csv')
        TxSyncWord = getRegister(f'{inputDir}/Formatter_Buffer_Input_TxSyncWord.csv')

        df_LinkReset = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_link_reset_econt.csv',skipinitialspace=True)
        df_LinkReset.columns=['LINKRESETECONT']
        if algo==0: #threshold sum

            latency=1

            df_AddrMap = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_AddrMap.csv',skipinitialspace=True)
            df_ChargeQ = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_ChargeQ.csv',skipinitialspace=True)
            df_Sum = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_Sum.csv',skipinitialspace=True)
            df_SumNotTransmitted = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_SumNotTransmitted.csv',skipinitialspace=True)
            df_SumNotTransmitted.columns=['SUM_NOT_TRANSMITTED']

            Use_Sum = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_Use_Sum.csv',skipinitialspace=True)
            Use_Sum.columns=['USE_SUM']
            
            df_Threshold_Sum = df_AddrMap.merge(df_ChargeQ, left_index=True, right_index=True).merge(df_Sum, left_index=True, right_index=True).merge(df_SumNotTransmitted, left_index=True, right_index=True)

            df_Emulator = Format_Threshold_Sum(df_Threshold_Sum, df_BX_CNT, TxSyncWord, Use_Sum, EPortTx_NumEn, df_LinkReset).drop('IdleWord',axis=1)

        elif algo==1: #STC
            latency=1

            df_XTC16_9 = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_XTC16_9_Sum.csv',skipinitialspace=True)
            df_XTC4_7 = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_XTC4_7_Sum.csv',skipinitialspace=True)
            df_XTC4_9 = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_XTC4_9_Sum.csv',skipinitialspace=True)
            df_MAX16_Addr = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_MAX16_Addr.csv',skipinitialspace=True)
            df_MAX4_Addr = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_MAX4_Addr.csv',skipinitialspace=True)
            
            df_STC = df_XTC4_9.merge(df_XTC16_9, left_index=True, right_index=True).merge(df_XTC4_7, left_index=True, right_index=True).merge(df_MAX4_Addr, left_index=True, right_index=True).merge(df_MAX16_Addr, left_index=True, right_index=True)

            df_Emulator = Format_SuperTriggerCell(df_STC, STC_Type, EPortTx_NumEn, df_BX_CNT, TxSyncWord, df_LinkReset).drop('IdleWord',axis=1)

        elif algo==2: #BC
            latency=1
            df_BC_Charge = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_BC_Charge.csv',skipinitialspace=True)
            df_BC_TC_map = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_BC_TC_map.csv',skipinitialspace=True)
            df_BestChoice = df_BC_Charge.merge(df_BC_TC_map, left_index=True, right_index=True)

            Use_Sum = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_Use_Sum.csv',skipinitialspace=True)
            Use_Sum.columns=['USE_SUM']

            df_Emulator = Format_BestChoice(df_BestChoice,EPortTx_NumEn, df_BX_CNT, TxSyncWord, Use_Sum, df_LinkReset).drop('IdleWord',axis=1)

        elif algo==3: #RPT
            latency=1

            df_Repeater = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_RepeaterQ.csv',skipinitialspace=True)

            df_Emulator = Format_Repeater(df_Repeater, df_BX_CNT, TxSyncWord, EPortTx_NumEn, df_LinkReset).drop('IdleWord',axis=1)

        elif algo==4: #AE
            latency=1
            
            df_AEBytes = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_outEncoder.csv',skipinitialspace=True)
            df_AEMask = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_keep_auto_encoder_bits.csv',skipinitialspace=True)

            df_Autoencoder = df_AEBytes.merge(df_AEMask, left_index=True, right_index=True)

            df_Emulator = Format_Autoencoder(df_Autoencoder, df_BX_CNT, EPortTx_NumEn, TxSyncWord, df_LinkReset).drop('IdleWord',axis=1)

        ### load expected outputs for comparisons
        df_FRAMEQ = pd.read_csv(f'{inputDir}/Formatter_Buffer_Output_FrameQ.csv', skipinitialspace=True)
        df_FRAMEQTruncated = pd.read_csv(f'{inputDir}/Formatter_Buffer_Output_FrameQTruncated.csv', skipinitialspace=True)
        df_FRAMEQ_NumW = pd.read_csv(f'{inputDir}/Formatter_Buffer_Output_FrameQ_NumW.csv', skipinitialspace=True)
        df_Comparison = df_FRAMEQ.merge(df_FRAMEQ_NumW, left_index=True, right_index=True).merge(df_FRAMEQTruncated[['FMT_OUT_FRMQT_0','FMT_OUT_FRMQT_1']], left_index=True, right_index=True)

        df_Comparison.columns = df_Emulator.columns


    elif ASICBlock=='Buffer':
        latency=1
        df_BX_CNT = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_Bx_Cnt_In.csv',skipinitialspace=True)
        df_BX_CNT.columns = ['BX_CNT']

        df_FrameQ=pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_FrameQ.csv', skipinitialspace=True)[[f'BUF_INP_FRMQ_{i}' for i in range(26)]]
        df_FrameQ.columns = [f'FRAMEQ_{i}' for i in range(26)]
        df_FrameQ_NumW=pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_FrameQ_NumW.csv', skipinitialspace=True)
        df_FrameQ_NumW.columns=['FRAMEQ_NUMW']
        df_FrameQTruncated=pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_FrameQTruncated.csv', skipinitialspace=True)[['BUF_INP_FRMQT_0','BUF_INP_FRMQT_1']]
        df_FrameQTruncated.columns = ['FRAMEQ_Truncated_0','FRAMEQ_Truncated_1']

        df_FormatterOutput = df_FrameQ.merge(df_FrameQ_NumW, left_index=True, right_index=True).merge(df_FrameQTruncated, left_index=True, right_index=True)

        T1 = getRegister(f'{inputDir}/Formatter_Buffer_Input_Buffer_Threshold_T1.csv')
        T2 = getRegister(f'{inputDir}/Formatter_Buffer_Input_Buffer_Threshold_T2.csv')
        T3 = getRegister(f'{inputDir}/Formatter_Buffer_Input_Buffer_Threshold_T3.csv')
        EPortTx_NumEn = getRegister(f'{inputDir}/Formatter_Buffer_Input_EPortTx_NumEn.csv')

        df_Emulator = Buffer(df_FormatterOutput, EPortTx_NumEn, T1, T2, T3)

        df_Comparison = pd.read_csv(f'{inputDir}/Formatter_Buffer_Output_buffer_ePortTx_DataIn.csv',skipinitialspace=True)[[f'BUF_OUT_TX_DATA_{i}' for i in range(13)]]

        df_Comparison.columns = [f'TX_DATA_{i}' for i in range(13)]

    elif ASICBlock=="FormatterBuffer":
        print('HERETEST')

        df_BX_CNT = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_Bx_Cnt_In.csv',skipinitialspace=True)
        df_BX_CNT.columns = ['BX_CNT']

        algo = getRegister(f'{inputDir}/Formatter_Buffer_Input_Algorithm_Type.csv')
        EPortTx_NumEn = getRegister(f'{inputDir}/Formatter_Buffer_Input_EPortTx_NumEn.csv')
        STC_Type = getRegister(f'{inputDir}/Formatter_Buffer_Input_STC_Type.csv')
        TxSyncWord = getRegister(f'{inputDir}/Formatter_Buffer_Input_TxSyncWord.csv')

        df_LinkReset = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_link_reset_econt.csv',skipinitialspace=True)
        df_LinkReset.columns=['LINKRESETECONT']

        if algo==0: #threshold sum

            latency=2

            df_AddrMap = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_AddrMap.csv',skipinitialspace=True)
            df_ChargeQ = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_ChargeQ.csv',skipinitialspace=True)
            df_Sum = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_Sum.csv',skipinitialspace=True)
            df_SumNotTransmitted = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_SumNotTransmitted.csv',skipinitialspace=True)
            df_SumNotTransmitted.columns=['SUM_NOT_TRANSMITTED']

            Use_Sum = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_Use_Sum.csv',skipinitialspace=True)
            Use_Sum.columns=['USE_SUM']
            
            df_Threshold_Sum = df_AddrMap.merge(df_ChargeQ, left_index=True, right_index=True).merge(df_Sum, left_index=True, right_index=True).merge(df_SumNotTransmitted, left_index=True, right_index=True)

            df_Emulator = Format_Threshold_Sum(df_Threshold_Sum, df_BX_CNT, TxSyncWord, Use_Sum, EPortTx_NumEn, df_LinkReset).drop('IdleWord',axis=1)

        elif algo==1: #STC
            latency=2

            df_XTC16_9 = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_XTC16_9_Sum.csv',skipinitialspace=True)
            df_XTC4_7 = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_XTC4_7_Sum.csv',skipinitialspace=True)
            df_XTC4_9 = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_XTC4_9_Sum.csv',skipinitialspace=True)
            df_MAX16_Addr = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_MAX16_Addr.csv',skipinitialspace=True)
            df_MAX4_Addr = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_MAX4_Addr.csv',skipinitialspace=True)
            
            df_STC = df_XTC4_9.merge(df_XTC16_9, left_index=True, right_index=True).merge(df_XTC4_7, left_index=True, right_index=True).merge(df_MAX4_Addr, left_index=True, right_index=True).merge(df_MAX16_Addr, left_index=True, right_index=True)

            df_Emulator = Format_SuperTriggerCell(df_STC, STC_Type, EPortTx_NumEn, df_BX_CNT, TxSyncWord, df_LinkReset).drop('IdleWord',axis=1)

        elif algo==2: #BC
            latency=4
            df_BC_Charge = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_BC_Charge.csv',skipinitialspace=True)
            df_BC_TC_map = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_BC_TC_map.csv',skipinitialspace=True)
            df_BestChoice = df_BC_Charge.merge(df_BC_TC_map, left_index=True, right_index=True)

            Use_Sum = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_Use_Sum.csv',skipinitialspace=True)
            Use_Sum.columns=['USE_SUM']

            df_Emulator = Format_BestChoice(df_BestChoice,EPortTx_NumEn, df_BX_CNT, TxSyncWord, Use_Sum, df_LinkReset).drop('IdleWord',axis=1)

        elif algo==3: #RPT
            latency=2

            df_Repeater = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_RepeaterQ.csv',skipinitialspace=True)

            df_Emulator = Format_Repeater(df_Repeater, df_BX_CNT, TxSyncWord, EPortTx_NumEn, df_LinkReset).drop('IdleWord',axis=1)

        elif algo==4: #AE
            latency=2
            
            df_AEBytes = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_outEncoder.csv',skipinitialspace=True)
            df_AEMask = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_keep_auto_encoder_bits.csv',skipinitialspace=True)

            df_Autoencoder = df_AEBytes.merge(df_AEMask, left_index=True, right_index=True)

            df_Emulator = Format_Autoencoder(df_Autoencoder, df_BX_CNT, EPortTx_NumEn, TxSyncWord, df_LinkReset).drop('IdleWord',axis=1)

        T1 = getRegister(f'{inputDir}/Formatter_Buffer_Input_Buffer_Threshold_T1.csv')
        T2 = getRegister(f'{inputDir}/Formatter_Buffer_Input_Buffer_Threshold_T2.csv')
        T3 = getRegister(f'{inputDir}/Formatter_Buffer_Input_Buffer_Threshold_T3.csv')
        EPortTx_NumEn = getRegister(f'{inputDir}/Formatter_Buffer_Input_EPortTx_NumEn.csv')

        df_Emulator = Buffer(df_Emulator, EPortTx_NumEn, T1, T2, T3, df_LinkReset)

        df_Comparison = pd.read_csv(f'{inputDir}/Formatter_Buffer_Output_buffer_ePortTx_DataIn.csv',skipinitialspace=True)[[f'BUF_OUT_TX_DATA_{i}' for i in range(13)]]

        df_Comparison.columns = [f'TX_DATA_{i}' for i in range(13)]

    else:
        print('Unknown block to test', ASICBlock)
        exit()



    for i in range(latency):
        df_Emulator.drop(len(df_Emulator)-1,inplace=True)
            
        df_Comparison.drop(i,inplace=True)

    df_Comparison.reset_index(inplace=True,drop=True)
            

    matching = []
    mismatch = []
    for c in df_Comparison.columns:
        mine = df_Emulator[c].values
        cristians = df_Comparison[c].values
        compare= mine==cristians
        if verbose:
            print (c, "Agree" if compare.all() else "DISAGREE")

        if compare.all():
            matching.append(c)
        else:
            mismatch.append(c)
    if verbose:
        if len(mismatch)>0:
            print()
            print()
            print("DISAGREEMENT COLUMNS")
            print("Emulator:")
            print(df_Emulator[mismatch].head())
            print()
            print("Verilog:")
            print(df_Comparison[mismatch].head())
        else:
            print()
            print("GOOD AGREEMENT")
            print()

        if 'Buffer' in ASICBlock:
            print()
            print('Buffer Control Summary Counts')
            x = df_Emulator[[f'Cond{i}' for i in range(1,5)]]
            x.columns = ['T1 Truncations','T2 Truncations', 'T3 Full Data','Full Data']
            print(x.sum().to_string())
            print()

    return len(mismatch)==0, df_Emulator, df_Comparison

from Utils.linkAllocation import tcPerLink

#debuging function
def splitBCFormat(row, NTX=1):
    columns = [f'FRAMEQ_{i}' for i in range(2*NTX)]
    values = list(row[columns].values)

    bitString = ''.join(binV(values))

    nTC = tcPerLink[NTX]
    output = bitString[0:4] + '  ' + bitString[4:12]
    startIDX = 12
    for i in range(nTC):
        output += '  ' + bitString[startIDX:startIDX+6]
        startIDX += 6
    for i in range(nTC):
        output += '  ' + bitString[startIDX:startIDX+7]
        startIDX += 7

    return output



if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-i','--input', dest='inputDir', help='input directory name')
    parser.add_argument('-o','--output', dest='outputDir', default=None, help='outputDirectory, if different than directory of input file')
    parser.add_argument('-b','--block', dest="ASICBlock", default=None, help='ASIC block to run on')
    parser.add_argument('-a','--algo', dest="algo", default=None, type=int, help='Algorithm to use (if None, use value in csv files)')
#    parser.add_argument('-v','--verbose', dest="Verbose", default=False, action='store_true', help='verbose outputs')

    args = parser.parse_args()
    
    passVerification, df_Mine, df_Cristian= runVerification(**vars(args), verbose=True)
