import uproot
import argparse
import os

import pandas as pd
import numpy as np

from ASICBlocks.LoadData_ePortRX import loadMetaData, loadEportRXData, splitEportRXData
from ASICBlocks.MuxFixCalib import getMuxRegisters, Mux, FloatToFix, getCalibrationRegisters_Thresholds, Calibrate
from ASICBlocks.Algorithms import makeCHARGEQ, ThresholdSum, BestChoice, SuperTriggerCell, Repeater, Algorithms
from ASICBlocks.Autoencoder import Autoencoder, convertI2CtoWeights
from ASICBlocks.Formatter import Format_Threshold_Sum, Format_BestChoice, Format_SuperTriggerCell, Format_Repeater, Format_Autoencoder
from ASICBlocks.BufferBlock import Buffer

commentChar='#'

def newFormat(x):
    return format(x,'#018b')[2:]

binV=np.vectorize(newFormat)

def bin32(x, isHex=False,reverse=False):
    if isHex:
        v = int(x,16)
    else:
        v=x
    bits = format(v,'032b')
    if reverse:
        bits = bits[::-1]
    return bits

def Serializer(df_Buffer, serializerDelay=101, serializerDelayChange=[0]*13):
    dfBin = df_Buffer.apply(np.vectorize(bin32),reverse=True)
    for i in range(13):
        bitString = ''.join(dfBin[f'TX_DATA_{i}'].values)
        delay = serializerDelay-serializerDelayChange[i]
        bitString = '0'*(delay) + bitString[:(-1*delay)]
        x = [format(int(bitString[i:i+32],2),'08x') for i in range(0,len(bitString),32)]
        #x = [format(int(bitString[i:i+32][::-1],2),'08x') for i in range(0,len(bitString),32)]
        y = np.array(x)
        dfBin[f'ETX_{i}'] = y
#        dfBin[f'ETX_{i}'] = np.array([format(int(bitString[i:i+32][::-1],2),'08x') for i in range(0,len(bitString),32)])
    return dfBin[[f'ETX_{i}' for i in range(13)]]

def findAlignmentTiming(inputDir):
    linkResetTimestamp = -1
    try:
        fName = ''
        if '/IO/' in inputDir:
            fName  = f"{inputDir.replace('/IO/','/RPT/')}/Channel_Aligner_Assertion_File.txt"
        elif '/UVM/' in inputDir:
            fName  = f"{inputDir.replace('/UVM/','/RPT/')}/Channel_Aligner_Assertion_File.txt"
        with open(fName) as alignmentFile:
            for line in alignmentFile:
                if 'Found Link Reset at Timestamp' in line:
                    x=np.array(line.split())
                    idx = np.where(x=='Timestamp')[0]
                    linkResetTimestamp = int(x[idx+2][0].replace(',',''))
                if 'Found take_snapshot activation at Timestamp' in line:
                    x=np.array(line.split())
                    idx = np.where(x=='Timestamp')[0]
                    snapshotTimestamp = int(x[idx+2][0].replace(',',''))
                    idx = np.where(x=='Orbit')[0]
                    snapshotOrbit = int(x[idx+2][0].replace(',',''))
                    idx = np.where(x=='Bucket')[0]
                    snapshotBucket = int(x[idx+2][0].replace(',',''))
                    if linkResetTimestamp==-1:
                        return 255, snapshotTimestamp, snapshotOrbit, snapshotBucket
                    else:
                        return 162*2 + snapshotTimestamp - linkResetTimestamp, snapshotTimestamp, snapshotOrbit, snapshotBucket
    except:
        return 162*2, None, None, None
    return 162*2, None, None, None
                

def getRegister(inputFile):
    value = np.unique(pd.read_csv(inputFile,skipinitialspace=True,comment=commentChar).values,axis=0)

    if not len(value)==1:
        print('Only one register type at a time is supported')
        print(f'Multiple values found in file {inputFile}')
        print('Exitting')
        exit()
    value = value[0]
    if len(value)==1:
        return value[0]
    return value

def AlgorithmRoutine(inputDir, algo, verbose=True, df_CALQ=None):
    if verbose: print('Running Algorithm')
    if df_CALQ is None:
        if verbose:
            print(f'Reading Input from {inputDir}/Algorithm_Input_CalQ.csv')
        df_CALQ = pd.read_csv(f'{inputDir}/Algorithm_Input_CalQ.csv',skipinitialspace=True,comment=commentChar)
    df_CALQ.reset_index(inplace=True,drop=True)
    df_DropLSB = pd.read_csv(f'{inputDir}/Algorithm_Input_DropLSB.csv',skipinitialspace=True,comment=commentChar)
    df_DropLSB.loc[df_DropLSB.DROP_LSB>4] = 0
#    df_Header = pd.read_csv(f'{inputDir}/Algorithm_Input_Header.csv',skipinitialspace=True,comment=commentChar)
    df_Threshold = pd.read_csv(f'{inputDir}/Algorithm_Input_Threshold.csv',skipinitialspace=True,comment=commentChar)

    if algo==0: #threshold sum
        latency=1
        df_Emulator=ThresholdSum(df_CALQ, df_Threshold, df_DropLSB)

        try:
            df_AddrMap = pd.read_csv(f'{inputDir}/Algorithm_Output_AddrMap.csv',skipinitialspace=True,comment=commentChar)
            df_ChargeQ = pd.read_csv(f'{inputDir}/Algorithm_Output_ChargeQ.csv',skipinitialspace=True,comment=commentChar)
            df_Sum = pd.read_csv(f'{inputDir}/Algorithm_Output_Sum.csv',skipinitialspace=True,comment=commentChar)
            df_SumNotTransmitted = pd.read_csv(f'{inputDir}/Algorithm_Output_SumNotTransmitted.csv',skipinitialspace=True,comment=commentChar)
            df_Comparison = df_AddrMap.merge(df_ChargeQ, left_index=True, right_index=True).merge(df_Sum, left_index=True, right_index=True).merge(df_SumNotTransmitted, left_index=True, right_index=True)
        except:
            df_Comparison = None

    elif algo==1: #STC
        latency = 1
        df_Emulator = SuperTriggerCell(df_CALQ, df_DropLSB)

        try:
            df_XTC4_9 = pd.read_csv(f'{inputDir}/Algorithm_Output_XTC4_9_Sum.csv',skipinitialspace=True,comment=commentChar)
            df_XTC16_9 = pd.read_csv(f'{inputDir}/Algorithm_Output_XTC16_9_Sum.csv',skipinitialspace=True,comment=commentChar)
            df_XTC4_7 = pd.read_csv(f'{inputDir}/Algorithm_Output_XTC4_7_Sum.csv',skipinitialspace=True,comment=commentChar)
            df_MAX4_Addr = pd.read_csv(f'{inputDir}/Algorithm_Output_MAX4_Addr.csv',skipinitialspace=True,comment=commentChar)
            df_MAX16_Addr= pd.read_csv(f'{inputDir}/Algorithm_Output_MAX16_Addr.csv',skipinitialspace=True,comment=commentChar)

            df_Comparison = df_XTC4_9.merge(df_XTC16_9,left_index=True, right_index=True).merge(df_XTC4_7,left_index=True, right_index=True).merge(df_MAX4_Addr,left_index=True, right_index=True).merge(df_MAX16_Addr,left_index=True, right_index=True)
        except:
            df_Comparison = None

    elif algo==2: #BC
        latency = 2
        df_Emulator = BestChoice(df_CALQ, df_DropLSB)

        try:
            df_BC_Charge = pd.read_csv(f'{inputDir}/Algorithm_Output_BC_Charge.csv',skipinitialspace=True,comment=commentChar)
            df_BC_TC_map = pd.read_csv(f'{inputDir}/Algorithm_Output_BC_TC_map.csv',skipinitialspace=True,comment=commentChar)
        
            df_Comparison = df_BC_Charge.merge(df_BC_TC_map,left_index=True, right_index=True)
        except:
            df_Comparison = None
        
    elif algo==3: #RPT
        latency = 1
        df_Emulator = Repeater(df_CALQ, df_DropLSB)

        try:
            df_Comparison = pd.read_csv(f'{inputDir}/Algorithm_Output_RepeaterQ.csv',skipinitialspace=True,comment=commentChar)
        except:
            df_Comparison = None

    elif algo==4: #AE
        latency=2

        weights = convertI2CtoWeights(inputDir)
        df_Emulator = Autoencoder(df_CALQ.reset_index(drop=True),weights)

        try:
            df_Comparison = pd.read_csv(f'{inputDir}/AE_Output_outEncoder.csv',skipinitialspace=True,comment=commentChar)
        except:
            df_Comparison = None

#        exit()
    else:
        print(f'unknown algorithm type : {algo}')
        exit()
        
    if verbose: print('   --- Finished Algorithm')
    return df_Emulator.reset_index(), df_Comparison, latency



def FormatterRoutine(inputDir, 
                     algo, 
                     EPortTx_NumEn, 
                     algoLatency=0,
                     verbose=True,
                     df_LinkReset=None,
                     linkResetOffset=None,
                     df_BX_CNT=None,
                     df_Threshold_Sum=None, 
                     df_STC=None, 
                     df_BestChoice=None, 
                     df_Repeater=None, 
                     df_Autoencoder=None):

    if verbose: print('Running Formatter')
    STC_Type = getRegister(f'{inputDir}/Formatter_Buffer_Input_STC_Type.csv')
    TxSyncWord = getRegister(f'{inputDir}/Formatter_Buffer_Input_TxSyncWord.csv')

    if df_BX_CNT is None:
        if verbose:
            print(f'Reading Input from {inputDir}/Formatter_Buffer_Input_Bx_Cnt_In.csv')
        df_BX_CNT = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_Bx_Cnt_In.csv',skipinitialspace=True,comment=commentChar)
        df_BX_CNT.columns = ['BX_CNT']

        #adjust the delay used for autoencoder to account for header delay issue that gets fixed internally within the formatter block in RTL
        algoLatCorr = 0
        if algo==4:
            algoLatCorr = -1

        #delay the header to account for algorithm latency
        df_BX_CNT = pd.concat([df_BX_CNT[algoLatency+algoLatCorr:], df_BX_CNT[:algoLatency+algoLatCorr]])

    df_BX_CNT.reset_index(inplace=True,drop=True)

    if df_LinkReset is None:
        if verbose:
            print(f'Reading Link Reset from {inputDir}/Formatter_Buffer_Input_link_reset_econt.csv')        
        df_LinkReset = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_link_reset_econt.csv',skipinitialspace=True,comment=commentChar)
        df_LinkReset.columns=['LINKRESETECONT']

        df_LinkReset = pd.concat([df_LinkReset[algoLatency:], df_LinkReset[:algoLatency]])

    if not linkResetOffset is None:
        df_LinkReset = pd.concat([df_LinkReset[linkResetOffset:], df_LinkReset[:linkResetOffset]])

    if algo==0: #threshold sum

        latency=1

        if df_Threshold_Sum is None:
            if verbose:
                print(f'Reading Input from {inputDir}')
            df_AddrMap = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_AddrMap.csv',skipinitialspace=True,comment=commentChar)
            df_ChargeQ = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_ChargeQ.csv',skipinitialspace=True,comment=commentChar)
            df_Sum = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_Sum.csv',skipinitialspace=True,comment=commentChar)
            df_SumNotTransmitted = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_SumNotTransmitted.csv',skipinitialspace=True,comment=commentChar)
            df_SumNotTransmitted.columns=['SUM_NOT_TRANSMITTED']
        
            df_Threshold_Sum = df_AddrMap.merge(df_ChargeQ, left_index=True, right_index=True).merge(df_Sum, left_index=True, right_index=True).merge(df_SumNotTransmitted, left_index=True, right_index=True)
        
        Use_Sum = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_Use_Sum.csv',skipinitialspace=True,comment=commentChar)
        Use_Sum.columns=['USE_SUM']
        
        df_Emulator = Format_Threshold_Sum(df_Threshold_Sum, df_BX_CNT, TxSyncWord, Use_Sum, EPortTx_NumEn, df_LinkReset).drop('IdleWord',axis=1)
        
    elif algo==1: #STC
        latency=1

        if df_STC is None:
            if verbose:
                print(f'Reading Input from {inputDir}')
            df_XTC16_9 = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_XTC16_9_Sum.csv',skipinitialspace=True,comment=commentChar)
            df_XTC4_7 = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_XTC4_7_Sum.csv',skipinitialspace=True,comment=commentChar)
            df_XTC4_9 = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_XTC4_9_Sum.csv',skipinitialspace=True,comment=commentChar)
            df_MAX16_Addr = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_MAX16_Addr.csv',skipinitialspace=True,comment=commentChar)
            df_MAX4_Addr = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_MAX4_Addr.csv',skipinitialspace=True,comment=commentChar)
        
            df_STC = df_XTC4_9.merge(df_XTC16_9, left_index=True, right_index=True).merge(df_XTC4_7, left_index=True, right_index=True).merge(df_MAX4_Addr, left_index=True, right_index=True).merge(df_MAX16_Addr, left_index=True, right_index=True)


        df_Emulator = Format_SuperTriggerCell(df_STC, STC_Type, EPortTx_NumEn, df_BX_CNT, TxSyncWord, df_LinkReset).drop('IdleWord',axis=1)
        
    elif algo==2: #BC
        latency=3
        
        if df_BestChoice is None:
            if verbose:
                print(f'Reading Input from {inputDir}')
            df_BC_Charge = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_BC_Charge.csv',skipinitialspace=True,comment=commentChar)
            df_BC_TC_map = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_BC_TC_map.csv',skipinitialspace=True,comment=commentChar)
            df_BestChoice = df_BC_Charge.merge(df_BC_TC_map, left_index=True, right_index=True)
            
        Use_Sum = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_Use_Sum.csv',skipinitialspace=True,comment=commentChar)
        Use_Sum.columns=['USE_SUM']
    
        df_Emulator = Format_BestChoice(df_BestChoice,EPortTx_NumEn, df_BX_CNT, TxSyncWord, Use_Sum, df_LinkReset).drop('IdleWord',axis=1)

    elif algo==3: #RPT
        latency=1
        
        if df_Repeater is None:
            if verbose:
                print(f'Reading Input from {inputDir}')
            df_Repeater = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_RepeaterQ.csv',skipinitialspace=True,comment=commentChar)
        
        df_Emulator = Format_Repeater(df_Repeater, df_BX_CNT, TxSyncWord, EPortTx_NumEn, df_LinkReset).drop('IdleWord',axis=1)
        
    elif algo==4: #AE
        latency=2
        
        if df_Autoencoder is None:
            if verbose:
                print(f'Reading Input from {inputDir}')
            df_Autoencoder = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_outEncoder.csv',skipinitialspace=True,comment=commentChar)
            #df_AEOutEncoder = pd.read_csv(f'{inputDir}/AE_Output_outEncoder.csv',skipinitialspace=True,comment=commentChar)

        df_AEMask = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_keep_auto_encoder_bits.csv',skipinitialspace=True,comment=commentChar)        
        df_Emulator = Format_Autoencoder(df_Autoencoder, df_BX_CNT, df_AEMask, EPortTx_NumEn, TxSyncWord, df_LinkReset).drop('IdleWord',axis=1)

    if verbose: print('   --- Finished Formatter')
    return df_Emulator.merge(df_BX_CNT, left_index=True, right_index=True), latency
#    return df_Emulator, latency


def hex32(x):
    return format(x, '08x')
hex32 = np.vectorize(hex32)

def runVerification(inputDir, outputDir, ASICBlock, Quiet=False, algo=None, EPortTx_NumEn=None, eRx_DataDir=None, bxSkip=None, serializerDelay=101, forceLatency=None, forceAlignmentTime=None, linkResetOffset=None, skipComparison=False):
    hexOutput=False
    verbose= not Quiet

    df_ePortRxDataGroup = None

    alignmentTime, snapshotTime, snapshotOrbit, snapshotBucket = findAlignmentTiming(inputDir)

    if not forceAlignmentTime is None:
        alignmentTime =forceAlignmentTime
    if verbose:
        print(f'Alignment time = {alignmentTime}')
    comparisonColumns=None

    if ASICBlock=='Algorithm':

        if algo is None:
            algo=getRegister(f'{inputDir}/Algorithm_Input_Type.csv')

        df_Emulator, df_Comparison, latency = AlgorithmRoutine(inputDir, algo, verbose=verbose)

            
    elif ASICBlock=='Formatter':
        algo = getRegister(f'{inputDir}/Formatter_Buffer_Input_Algorithm_Type.csv')
        if EPortTx_NumEn is None:
            EPortTx_NumEn = getRegister(f'{inputDir}/Formatter_Buffer_Input_EPortTx_NumEn.csv')

        df_Emulator, latency = FormatterRoutine(inputDir, algo, EPortTx_NumEn, verbose=verbose, linkResetOffset=linkResetOffset)

        try:
            ### load expected outputs for comparisons
            df_FRAMEQ = pd.read_csv(f'{inputDir}/Formatter_Buffer_Output_FrameQ.csv', skipinitialspace=True,comment=commentChar)
            df_FRAMEQTruncated = pd.read_csv(f'{inputDir}/Formatter_Buffer_Output_FrameQTruncated.csv', skipinitialspace=True,comment=commentChar)
            df_FRAMEQ_NumW = pd.read_csv(f'{inputDir}/Formatter_Buffer_Output_FrameQ_NumW.csv', skipinitialspace=True,comment=commentChar)
            df_LinkReset = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_link_reset_econt.csv', skipinitialspace=True,comment=commentChar)
            # df_Comparison = df_FRAMEQ.merge(df_FRAMEQ_NumW, left_index=True, right_index=True).merge(df_FRAMEQTruncated[['FMT_OUT_FRMQT_0','FMT_OUT_FRMQT_1']], left_index=True, right_index=True)
            # df_Comparison.columns = [f'FRAMEQ_{i}' for i in range(26)] + ['FRAMEQ_NUMW', 'FRAMEQ_Truncated_0', 'FRAMEQ_Truncated_1']

            df_Comparison = df_FRAMEQ.merge(df_FRAMEQ_NumW, left_index=True, right_index=True).merge(df_FRAMEQTruncated[['FMT_OUT_FRMQT_0','FMT_OUT_FRMQT_1']], left_index=True, right_index=True).merge(df_LinkReset, left_index=True, right_index=True)
            df_Comparison.columns = [f'FRAMEQ_{i}' for i in range(26)] + ['FRAMEQ_NUMW', 'FRAMEQ_Truncated_0', 'FRAMEQ_Truncated_1','LINKRESETECONT']
            comparisonColumns = [f'FRAMEQ_{i}' for i in range(26)] + ['FRAMEQ_NUMW', 'FRAMEQ_Truncated_0', 'FRAMEQ_Truncated_1']
        except:
            df_Comparison = None

        hexOutput=True

    elif ASICBlock=='Buffer':
        latency=1

        df_FrameQ=pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_FrameQ.csv', skipinitialspace=True,comment=commentChar)[[f'BUF_INP_FRMQ_{i}' for i in range(26)]]
        df_FrameQ.columns = [f'FRAMEQ_{i}' for i in range(26)]
        df_FrameQ_NumW=pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_FrameQ_NumW.csv', skipinitialspace=True,comment=commentChar)
        df_FrameQ_NumW.columns=['FRAMEQ_NUMW']
        df_FrameQTruncated=pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_FrameQTruncated.csv', skipinitialspace=True,comment=commentChar)[['BUF_INP_FRMQT_0','BUF_INP_FRMQT_1']]
        df_FrameQTruncated.columns = ['FRAMEQ_Truncated_0','FRAMEQ_Truncated_1']

        df_FormatterOutput = df_FrameQ.merge(df_FrameQ_NumW, left_index=True, right_index=True).merge(df_FrameQTruncated, left_index=True, right_index=True)

        T1 = getRegister(f'{inputDir}/Formatter_Buffer_Input_Buffer_Threshold_T1.csv')
        T2 = getRegister(f'{inputDir}/Formatter_Buffer_Input_Buffer_Threshold_T2.csv')
        T3 = getRegister(f'{inputDir}/Formatter_Buffer_Input_Buffer_Threshold_T3.csv')
        if EPortTx_NumEn is None:
            EPortTx_NumEn = getRegister(f'{inputDir}/Formatter_Buffer_Input_EPortTx_NumEn.csv')

        if verbose: print('Running Buffer')
        df_Emulator = Buffer(df_FormatterOutput, EPortTx_NumEn, T1, T2, T3)
        if verbose: print('   --- Finished Buffer')

        try:
            df_Comparison = pd.read_csv(f'{inputDir}/Formatter_Buffer_Output_buffer_ePortTx_DataIn.csv',skipinitialspace=True,comment=commentChar)[[f'BUF_OUT_TX_DATA_{i}' for i in range(13)]]
            df_Comparison.columns = [f'TX_DATA_{i}' for i in range(13)]
        except:
            df_Comparison = None

        hexOutput=True

    elif ASICBlock=='BufferSerializer':
        latency=1

        df_FrameQ=pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_FrameQ.csv', skipinitialspace=True,comment=commentChar)[[f'BUF_INP_FRMQ_{i}' for i in range(26)]]
        df_FrameQ.columns = [f'FRAMEQ_{i}' for i in range(26)]
        df_FrameQ_NumW=pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_FrameQ_NumW.csv', skipinitialspace=True,comment=commentChar)
        df_FrameQ_NumW.columns=['FRAMEQ_NUMW']
        df_FrameQTruncated=pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_FrameQTruncated.csv', skipinitialspace=True,comment=commentChar)[['BUF_INP_FRMQT_0','BUF_INP_FRMQT_1']]
        df_FrameQTruncated.columns = ['FRAMEQ_Truncated_0','FRAMEQ_Truncated_1']

        df_FormatterOutput = df_FrameQ.merge(df_FrameQ_NumW, left_index=True, right_index=True).merge(df_FrameQTruncated, left_index=True, right_index=True)

        T1 = getRegister(f'{inputDir}/Formatter_Buffer_Input_Buffer_Threshold_T1.csv')
        T2 = getRegister(f'{inputDir}/Formatter_Buffer_Input_Buffer_Threshold_T2.csv')
        T3 = getRegister(f'{inputDir}/Formatter_Buffer_Input_Buffer_Threshold_T3.csv')
        if EPortTx_NumEn is None:
            EPortTx_NumEn = getRegister(f'{inputDir}/Formatter_Buffer_Input_EPortTx_NumEn.csv')

        if verbose: print('Running Buffer')
        df_Buffer = Buffer(df_FormatterOutput, EPortTx_NumEn, T1, T2, T3)
        if verbose: print('   --- Finished Buffer')

        serializerDelayChange=[0]*13

        try:
            df_Comparison = None
            for iETX in range(13):
                dETX = pd.read_csv(f'{inputDir}/ETX_{format(iETX,"02")}.csv',dtype=str,skipinitialspace=True,comment=commentChar)[['OUT_DATA_PIN','INP_1G28_EN_ABC_40MHZ']]
                serializerDelayChange[iETX] = int(np.log2(int(dETX.INP_1G28_EN_ABC_40MHZ.values[0],16)))
                if df_Comparison is None:
                    df_Comparison = dETX[['OUT_DATA_PIN']]
                    df_Comparison.columns = [f'ETX_{iETX}']
                else:
                    df_Comparison[f'ETX_{iETX}'] = dETX[['OUT_DATA_PIN']]
        except:
            df_Comparison = None

        df_Emulator=Serializer(df_Buffer, serializerDelay, serializerDelayChange)

        hexOutput=True

    elif ASICBlock=="FormatterBuffer":
        algo = getRegister(f'{inputDir}/Formatter_Buffer_Input_Algorithm_Type.csv')
        if EPortTx_NumEn is None:
            EPortTx_NumEn = getRegister(f'{inputDir}/Formatter_Buffer_Input_EPortTx_NumEn.csv')

        df_Emulator_Formatter, formatter_Latency = FormatterRoutine(inputDir, algo, EPortTx_NumEn, verbose=verbose, linkResetOffset=linkResetOffset)

        T1 = getRegister(f'{inputDir}/Formatter_Buffer_Input_Buffer_Threshold_T1.csv')
        T2 = getRegister(f'{inputDir}/Formatter_Buffer_Input_Buffer_Threshold_T2.csv')
        T3 = getRegister(f'{inputDir}/Formatter_Buffer_Input_Buffer_Threshold_T3.csv')

        if verbose: print('Running Buffer')
        df_Emulator = Buffer(df_Emulator_Formatter, EPortTx_NumEn, T1, T2, T3)
        if verbose: print('   --- Finished Buffer')

        try:
            df_Comparison = pd.read_csv(f'{inputDir}/Formatter_Buffer_Output_buffer_ePortTx_DataIn.csv',skipinitialspace=True,comment=commentChar)[[f'BUF_OUT_TX_DATA_{i}' for i in range(13)]]
            df_Comparison.columns = [f'TX_DATA_{i}' for i in range(13)]
        except:
            df_Comparison = None

        latency=formatter_Latency + 1
        hexOutput=True

    elif ASICBlock=="AlgorithmThroughBuffer":

        algo = getRegister(f'{inputDir}/Formatter_Buffer_Input_Algorithm_Type.csv')
        if EPortTx_NumEn is None:
            EPortTx_NumEn = getRegister(f'{inputDir}/Formatter_Buffer_Input_EPortTx_NumEn.csv')

        df_Emulator_Algo, df_Comparison, algo_Latency = AlgorithmRoutine(inputDir, algo, verbose=verbose)

        if algo==0: #threshold sum
            df_Emulator_Formatter, formatter_Latency = FormatterRoutine(inputDir, algo, EPortTx_NumEn, df_Threshold_Sum=df_Emulator_Algo, verbose=verbose, algoLatency=algo_Latency, linkResetOffset=linkResetOffset)
        if algo==1: #STC
            df_Emulator_Formatter, formatter_Latency = FormatterRoutine(inputDir, algo, EPortTx_NumEn, df_STC=df_Emulator_Algo, verbose=verbose, algoLatency=algo_Latency, linkResetOffset=linkResetOffset)
        if algo==2: #BC
            df_Emulator_Formatter, formatter_Latency = FormatterRoutine(inputDir, algo, EPortTx_NumEn, df_BestChoice=df_Emulator_Algo, verbose=verbose, algoLatency=algo_Latency, linkResetOffset=linkResetOffset)
        if algo==3: #Repeater
            df_Emulator_Formatter, formatter_Latency = FormatterRoutine(inputDir, algo, EPortTx_NumEn, df_Repeater=df_Emulator_Algo, verbose=verbose, algoLatency=algo_Latency, linkResetOffset=linkResetOffset)
        if algo==4: #Autoencoder
            df_Emulator_Formatter, formatter_Latency = FormatterRoutine(inputDir, algo, EPortTx_NumEn, df_Autoencoder=df_Emulator_Algo, verbose=verbose, algoLatency=algo_Latency, linkResetOffset=linkResetOffset)

        T1 = getRegister(f'{inputDir}/Formatter_Buffer_Input_Buffer_Threshold_T1.csv')
        T2 = getRegister(f'{inputDir}/Formatter_Buffer_Input_Buffer_Threshold_T2.csv')
        T3 = getRegister(f'{inputDir}/Formatter_Buffer_Input_Buffer_Threshold_T3.csv')

        if verbose: print('Running Buffer')
        df_Emulator = Buffer(df_Emulator_Formatter, EPortTx_NumEn, T1, T2, T3)
        if verbose: print('   --- Finished Buffer')

        try:
            df_Comparison = pd.read_csv(f'{inputDir}/Formatter_Buffer_Output_buffer_ePortTx_DataIn.csv',skipinitialspace=True,comment=commentChar)[[f'BUF_OUT_TX_DATA_{i}' for i in range(13)]]

            df_Comparison.columns = [f'TX_DATA_{i}' for i in range(13)]
        except:
            df_Comparison = None

        latency = algo_Latency + formatter_Latency + 1
        hexOutput=True

    elif ASICBlock=="AlgorithmThroughFormatter":

        algo = getRegister(f'{inputDir}/Formatter_Buffer_Input_Algorithm_Type.csv')
        if EPortTx_NumEn is None:
            EPortTx_NumEn = getRegister(f'{inputDir}/Formatter_Buffer_Input_EPortTx_NumEn.csv')

        df_Emulator_Algo, df_Comparison, algo_Latency = AlgorithmRoutine(inputDir, algo, verbose=verbose)

        if algo==0: #threshold sum
            df_Emulator, formatter_Latency = FormatterRoutine(inputDir, algo, EPortTx_NumEn, df_Threshold_Sum=df_Emulator_Algo, verbose=verbose, algoLatency=algo_Latency, linkResetOffset=linkResetOffset)
        if algo==1: #STC
            df_Emulator, formatter_Latency = FormatterRoutine(inputDir, algo, EPortTx_NumEn, df_STC=df_Emulator_Algo, verbose=verbose, algoLatency=algo_Latency, linkResetOffset=linkResetOffset)
        if algo==2: #BC
            df_Emulator, formatter_Latency = FormatterRoutine(inputDir, algo, EPortTx_NumEn, df_BestChoice=df_Emulator_Algo, verbose=verbose, algoLatency=algo_Latency, linkResetOffset=linkResetOffset)
        if algo==3: #Repeater
            df_Emulator, formatter_Latency = FormatterRoutine(inputDir, algo, EPortTx_NumEn, df_Repeater=df_Emulator_Algo, verbose=verbose, algoLatency=algo_Latency, linkResetOffset=linkResetOffset)
        if algo==4: #Autoencoder
            df_Emulator, formatter_Latency = FormatterRoutine(inputDir, algo, EPortTx_NumEn, df_Autoencoder=df_Emulator_Algo, verbose=verbose, algoLatency=algo_Latency, linkResetOffset=linkResetOffset)

        try:
            ### load expected outputs for comparisons
            df_FRAMEQ = pd.read_csv(f'{inputDir}/Formatter_Buffer_Output_FrameQ.csv', skipinitialspace=True,comment=commentChar)
            df_FRAMEQTruncated = pd.read_csv(f'{inputDir}/Formatter_Buffer_Output_FrameQTruncated.csv', skipinitialspace=True,comment=commentChar)
            df_FRAMEQ_NumW = pd.read_csv(f'{inputDir}/Formatter_Buffer_Output_FrameQ_NumW.csv', skipinitialspace=True,comment=commentChar)
            df_LinkReset = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_link_reset_econt.csv', skipinitialspace=True,comment=commentChar)
            # df_Comparison = df_FRAMEQ.merge(df_FRAMEQ_NumW, left_index=True, right_index=True).merge(df_FRAMEQTruncated[['FMT_OUT_FRMQT_0','FMT_OUT_FRMQT_1']], left_index=True, right_index=True).merge(df_LinkReset, left_index=True, right_index=True)
            # df_Comparison.columns = [f'FRAMEQ_{i}' for i in range(26)] + ['FRAMEQ_NUMW', 'FRAMEQ_Truncated_0', 'FRAMEQ_Truncated_1','LinkResetStatus']
            
            # df_Comparison = df_FRAMEQ.merge(df_FRAMEQ_NumW, left_index=True, right_index=True).merge(df_FRAMEQTruncated[['FMT_OUT_FRMQT_0','FMT_OUT_FRMQT_1']], left_index=True, right_index=True)
            # df_Comparison.columns = [f'FRAMEQ_{i}' for i in range(26)] + ['FRAMEQ_NUMW', 'FRAMEQ_Truncated_0', 'FRAMEQ_Truncated_1']
            #        df_Comparison.columns = df_Emulator.columns

            df_Comparison = df_FRAMEQ.merge(df_FRAMEQ_NumW, left_index=True, right_index=True).merge(df_FRAMEQTruncated[['FMT_OUT_FRMQT_0','FMT_OUT_FRMQT_1']], left_index=True, right_index=True).merge(df_LinkReset, left_index=True, right_index=True)
            df_Comparison.columns = [f'FRAMEQ_{i}' for i in range(26)] + ['FRAMEQ_NUMW', 'FRAMEQ_Truncated_0', 'FRAMEQ_Truncated_1','LINKRESETECONT']
            comparisonColumns = [f'FRAMEQ_{i}' for i in range(26)] + ['FRAMEQ_NUMW', 'FRAMEQ_Truncated_0', 'FRAMEQ_Truncated_1']
        except:
            df_Comparison = None


        latency = algo_Latency + formatter_Latency

        hexOutput=True

    elif ASICBlock=="Front":
        latency=11
        if eRx_DataDir is None:
            eRx_DataDir=inputDir
        try:
            df_ePortRxDataGroup, df_BX_CNT, df_SimEnergyStatus, df_linkReset = loadEportRXData(eRx_DataDir,alignmentTime=alignmentTime)
        except:
            print(f'No EPortRx data found in directory {eRx_DataDir}')
            exit()
            
        columns = [f'ePortRxDataGroup_{i}' for i in range(12)]
        df_Mux_in = splitEportRXData(df_ePortRxDataGroup[columns])

        MuxRegisters = getRegister(f'{inputDir}/MuxFixCalib_Input_MuxSelect.csv')

        df_Mux_out = Mux(df_Mux_in, MuxRegisters)
        isHDM = getRegister(f'{inputDir}/MuxFixCalib_Input_HighDensity.csv')

        df_F2F = FloatToFix(df_Mux_out, isHDM)
        CALVALUE_Registers = getRegister(f'{inputDir}/MuxFixCalib_Input_CalValue.csv')

        df_Emulator = Calibrate(df_F2F, CALVALUE_Registers)
        try:
            df_Comparison = pd.read_csv(f'{inputDir}/Algorithm_Input_CalQ.csv',skipinitialspace=True,comment=commentChar)
        except:
            df_Comparison = None

    elif ASICBlock=="FrontToAlgo":

        latency=0
        if eRx_DataDir is None:
            eRx_DataDir=inputDir
        try:
            df_ePortRxDataGroup, df_BX_CNT, df_SimEnergyStatus, df_linkReset = loadEportRXData(eRx_DataDir,alignmentTime=alignmentTime)
        except:
            print(f'No EPortRx data found in directory {eRx_DataDir}')
            exit()
            
        columns = [f'ePortRxDataGroup_{i}' for i in range(12)]
        df_Mux_in = splitEportRXData(df_ePortRxDataGroup[columns])

        MuxRegisters = getRegister(f'{inputDir}/MuxFixCalib_Input_MuxSelect.csv')

        df_Mux_out = Mux(df_Mux_in, MuxRegisters)
        isHDM = getRegister(f'{inputDir}/MuxFixCalib_Input_HighDensity.csv')

        df_F2F = FloatToFix(df_Mux_out, isHDM)
        CALVALUE_Registers = getRegister(f'{inputDir}/MuxFixCalib_Input_CalValue.csv')

        df_CalQ = Calibrate(df_F2F, CALVALUE_Registers)

        front_Latency=11

        algo = getRegister(f'{inputDir}/Formatter_Buffer_Input_Algorithm_Type.csv')
        if EPortTx_NumEn is None:
            EPortTx_NumEn = getRegister(f'{inputDir}/Formatter_Buffer_Input_EPortTx_NumEn.csv')

        df_Emulator, df_Comparison, algo_Latency = AlgorithmRoutine(inputDir, algo, verbose=verbose, df_CALQ = df_CalQ)
        latency = front_Latency + algo_Latency 

    elif ASICBlock=="FrontToFormatter":

        latency=0
        if eRx_DataDir is None:
            eRx_DataDir=inputDir
        try:
            df_ePortRxDataGroup, df_BX_CNT, df_SimEnergyStatus, df_linkReset = loadEportRXData(eRx_DataDir,alignmentTime=alignmentTime)
        except:
            print(f'No EPortRx data found in directory {eRx_DataDir}')
            exit()
            
        columns = [f'ePortRxDataGroup_{i}' for i in range(12)]
        df_Mux_in = splitEportRXData(df_ePortRxDataGroup[columns])

        MuxRegisters = getRegister(f'{inputDir}/MuxFixCalib_Input_MuxSelect.csv')

        df_Mux_out = Mux(df_Mux_in, MuxRegisters)
        isHDM = getRegister(f'{inputDir}/MuxFixCalib_Input_HighDensity.csv')

        df_F2F = FloatToFix(df_Mux_out, isHDM)
        CALVALUE_Registers = getRegister(f'{inputDir}/MuxFixCalib_Input_CalValue.csv')

        df_CalQ = Calibrate(df_F2F, CALVALUE_Registers)

        front_Latency=11
        front_LinkReset_Offset = 6

        algo = getRegister(f'{inputDir}/Formatter_Buffer_Input_Algorithm_Type.csv')
        if EPortTx_NumEn is None:
            EPortTx_NumEn = getRegister(f'{inputDir}/Formatter_Buffer_Input_EPortTx_NumEn.csv')

        df_Emulator_Algo, df_Comparison, algo_Latency = AlgorithmRoutine(inputDir, algo, verbose=verbose, df_CALQ = df_CalQ)

        if linkResetOffset is None:
            linkResetOffset = front_LinkReset_Offset + algo_Latency

        if algo==0: #threshold sum
            df_Emulator, formatter_Latency = FormatterRoutine(inputDir, algo, EPortTx_NumEn, df_Threshold_Sum=df_Emulator_Algo, verbose=verbose, algoLatency=algo_Latency, df_LinkReset=df_linkReset, df_BX_CNT=df_BX_CNT, linkResetOffset=linkResetOffset)
        if algo==1: #STC
            df_Emulator, formatter_Latency = FormatterRoutine(inputDir, algo, EPortTx_NumEn, df_STC=df_Emulator_Algo, verbose=verbose, algoLatency=algo_Latency, df_LinkReset=df_linkReset, df_BX_CNT=df_BX_CNT, linkResetOffset=linkResetOffset)
        if algo==2: #BC
            df_Emulator, formatter_Latency = FormatterRoutine(inputDir, algo, EPortTx_NumEn, df_BestChoice=df_Emulator_Algo, verbose=verbose, algoLatency=algo_Latency, df_LinkReset=df_linkReset, df_BX_CNT=df_BX_CNT, linkResetOffset=linkResetOffset)
        if algo==3: #Repeater
            df_Emulator, formatter_Latency = FormatterRoutine(inputDir, algo, EPortTx_NumEn, df_Repeater=df_Emulator_Algo, verbose=verbose, algoLatency=algo_Latency, df_LinkReset=df_linkReset, df_BX_CNT=df_BX_CNT, linkResetOffset=linkResetOffset)
        if algo==4: #Autoencoder
            df_Emulator, formatter_Latency = FormatterRoutine(inputDir, algo, EPortTx_NumEn, df_Autoencoder=df_Emulator_Algo, verbose=verbose, algoLatency=algo_Latency, df_LinkReset=df_linkReset, df_BX_CNT=df_BX_CNT, linkResetOffset=linkResetOffset)

        try:
            ### load expected outputs for comparisons
            df_FRAMEQ = pd.read_csv(f'{inputDir}/Formatter_Buffer_Output_FrameQ.csv', skipinitialspace=True,comment=commentChar)
            df_FRAMEQTruncated = pd.read_csv(f'{inputDir}/Formatter_Buffer_Output_FrameQTruncated.csv', skipinitialspace=True,comment=commentChar)
            df_FRAMEQ_NumW = pd.read_csv(f'{inputDir}/Formatter_Buffer_Output_FrameQ_NumW.csv', skipinitialspace=True,comment=commentChar)
            df_LinkReset = pd.read_csv(f'{inputDir}/Formatter_Buffer_Input_link_reset_econt.csv', skipinitialspace=True,comment=commentChar)

            # df_Comparison = df_FRAMEQ.merge(df_FRAMEQ_NumW, left_index=True, right_index=True).merge(df_FRAMEQTruncated[['FMT_OUT_FRMQT_0','FMT_OUT_FRMQT_1']], left_index=True, right_index=True)
            # df_Comparison.columns = [f'FRAMEQ_{i}' for i in range(26)] + ['FRAMEQ_NUMW', 'FRAMEQ_Truncated_0', 'FRAMEQ_Truncated_1']

            df_Comparison = df_FRAMEQ.merge(df_FRAMEQ_NumW, left_index=True, right_index=True).merge(df_FRAMEQTruncated[['FMT_OUT_FRMQT_0','FMT_OUT_FRMQT_1']], left_index=True, right_index=True).merge(df_LinkReset, left_index=True, right_index=True)
            df_Comparison.columns = [f'FRAMEQ_{i}' for i in range(26)] + ['FRAMEQ_NUMW', 'FRAMEQ_Truncated_0', 'FRAMEQ_Truncated_1','LINKRESETECONT']
            comparisonColumns = [f'FRAMEQ_{i}' for i in range(26)] + ['FRAMEQ_NUMW', 'FRAMEQ_Truncated_0', 'FRAMEQ_Truncated_1']
        except:
            df_Comparison = None

        latency = front_Latency + algo_Latency + formatter_Latency 

        hexOutput=True

    elif ASICBlock=="FormatterBufferSerializer":
        algo = getRegister(f'{inputDir}/Formatter_Buffer_Input_Algorithm_Type.csv')
        if EPortTx_NumEn is None:
            EPortTx_NumEn = getRegister(f'{inputDir}/Formatter_Buffer_Input_EPortTx_NumEn.csv')

        df_Emulator_Formatter, formatter_Latency = FormatterRoutine(inputDir, algo, EPortTx_NumEn, verbose=verbose, linkResetOffset=linkResetOffset)

        T1 = getRegister(f'{inputDir}/Formatter_Buffer_Input_Buffer_Threshold_T1.csv')
        T2 = getRegister(f'{inputDir}/Formatter_Buffer_Input_Buffer_Threshold_T2.csv')
        T3 = getRegister(f'{inputDir}/Formatter_Buffer_Input_Buffer_Threshold_T3.csv')

        if verbose: print('Running Buffer')
        df_Buffer = Buffer(df_Emulator_Formatter, EPortTx_NumEn, T1, T2, T3)
        if verbose: print('   --- Finished Buffer')

        serializerDelayChange=[0]*13

        try:
            df_Comparison = None
            for iETX in range(13):
                dETX = pd.read_csv(f'{inputDir}/ETX_{format(iETX,"02")}.csv',dtype=str,skipinitialspace=True,comment=commentChar)[['OUT_DATA_PIN','INP_1G28_EN_ABC_40MHZ']]
                serializerDelayChange[iETX] = int(np.log2(int(dETX.INP_1G28_EN_ABC_40MHZ.values[0],16)))
                if df_Comparison is None:
                    df_Comparison = dETX[['OUT_DATA_PIN']]
                    df_Comparison.columns = [f'ETX_{iETX}']
                else:
                    df_Comparison[f'ETX_{iETX}'] = dETX[['OUT_DATA_PIN']]
        except:
            df_Comparison = None

        df_Emulator=Serializer(df_Buffer, serializerDelay, serializerDelayChange)


        latency=formatter_Latency + 1
        hexOutput=True

    elif ASICBlock=="AlgorithmThroughSerializer":

        algo = getRegister(f'{inputDir}/Formatter_Buffer_Input_Algorithm_Type.csv')
        if EPortTx_NumEn is None:
            EPortTx_NumEn = getRegister(f'{inputDir}/Formatter_Buffer_Input_EPortTx_NumEn.csv')

        df_Emulator_Algo, df_Comparison, algo_Latency = AlgorithmRoutine(inputDir, algo, verbose=verbose)

        if algo==0: #threshold sum
            df_Emulator_Formatter, formatter_Latency = FormatterRoutine(inputDir, algo, EPortTx_NumEn, df_Threshold_Sum=df_Emulator_Algo, verbose=verbose, algoLatency=algo_Latency, linkResetOffset=linkResetOffset)
        if algo==1: #STC
            df_Emulator_Formatter, formatter_Latency = FormatterRoutine(inputDir, algo, EPortTx_NumEn, df_STC=df_Emulator_Algo, verbose=verbose, algoLatency=algo_Latency, linkResetOffset=linkResetOffset)
        if algo==2: #BC
            df_Emulator_Formatter, formatter_Latency = FormatterRoutine(inputDir, algo, EPortTx_NumEn, df_BestChoice=df_Emulator_Algo, verbose=verbose, algoLatency=algo_Latency, linkResetOffset=linkResetOffset)
        if algo==3: #Repeater
            df_Emulator_Formatter, formatter_Latency = FormatterRoutine(inputDir, algo, EPortTx_NumEn, df_Repeater=df_Emulator_Algo, verbose=verbose, algoLatency=algo_Latency, linkResetOffset=linkResetOffset)
        if algo==4: #Autoencoder
            df_Emulator_Formatter, formatter_Latency = FormatterRoutine(inputDir, algo, EPortTx_NumEn, df_Autoencoder=df_Emulator_Algo, verbose=verbose, algoLatency=algo_Latency, linkResetOffset=linkResetOffset)

        T1 = getRegister(f'{inputDir}/Formatter_Buffer_Input_Buffer_Threshold_T1.csv')
        T2 = getRegister(f'{inputDir}/Formatter_Buffer_Input_Buffer_Threshold_T2.csv')
        T3 = getRegister(f'{inputDir}/Formatter_Buffer_Input_Buffer_Threshold_T3.csv')

        if verbose: print('Running Buffer')
        df_Buffer = Buffer(df_Emulator_Formatter, EPortTx_NumEn, T1, T2, T3)
        if verbose: print('   --- Finished Buffer')

        serializerDelayChange=[0]*13

        try:
            df_Comparison = None
            for iETX in range(13):
                dETX = pd.read_csv(f'{inputDir}/ETX_{format(iETX,"02")}.csv',dtype=str,skipinitialspace=True,comment=commentChar)[['OUT_DATA_PIN','INP_1G28_EN_ABC_40MHZ']]
                serializerDelayChange[iETX] = int(np.log2(int(dETX.INP_1G28_EN_ABC_40MHZ.values[0],16)))
                if df_Comparison is None:
                    df_Comparison = dETX[['OUT_DATA_PIN']]
                    df_Comparison.columns = [f'ETX_{iETX}']
                else:
                    df_Comparison[f'ETX_{iETX}'] = dETX[['OUT_DATA_PIN']]
        except:
            df_Comparison = None

        df_Emulator=Serializer(df_Buffer, serializerDelay, serializerDelayChange)


        latency = algo_Latency + formatter_Latency + 1
        hexOutput=True


    elif ASICBlock=="FullNoSerializer":

        latency=0
        if eRx_DataDir is None:
            eRx_DataDir=inputDir
        try:
            df_ePortRxDataGroup, df_BX_CNT, df_SimEnergyStatus, df_linkReset = loadEportRXData(eRx_DataDir,alignmentTime=alignmentTime)
        except:
            print(f'No EPortRx data found in directory {eRx_DataDir}')
            exit()
            
        columns = [f'ePortRxDataGroup_{i}' for i in range(12)]
        df_Mux_in = splitEportRXData(df_ePortRxDataGroup[columns])

        MuxRegisters = getRegister(f'{inputDir}/MuxFixCalib_Input_MuxSelect.csv')

        df_Mux_out = Mux(df_Mux_in, MuxRegisters)
        isHDM = getRegister(f'{inputDir}/MuxFixCalib_Input_HighDensity.csv')

        df_F2F = FloatToFix(df_Mux_out, isHDM)
        CALVALUE_Registers = getRegister(f'{inputDir}/MuxFixCalib_Input_CalValue.csv')

        df_CalQ = Calibrate(df_F2F, CALVALUE_Registers)

        front_Latency=11
        front_LinkReset_Offset=6

        algo = getRegister(f'{inputDir}/Formatter_Buffer_Input_Algorithm_Type.csv')

        if EPortTx_NumEn is None:
            EPortTx_NumEn = getRegister(f'{inputDir}/Formatter_Buffer_Input_EPortTx_NumEn.csv')

        df_Emulator_Algo, df_Comparison, algo_Latency = AlgorithmRoutine(inputDir, algo, verbose=verbose, df_CALQ = df_CalQ)

        if linkResetOffset is None:
            linkResetOffset = front_LinkReset_Offset + algo_Latency

        if algo==0: #threshold sum
            df_Emulator_Formatter, formatter_Latency = FormatterRoutine(inputDir, algo, EPortTx_NumEn, df_Threshold_Sum=df_Emulator_Algo, verbose=verbose, algoLatency=algo_Latency, df_LinkReset=df_linkReset, df_BX_CNT=df_BX_CNT, linkResetOffset=linkResetOffset)
        if algo==1: #STC
            df_Emulator_Formatter, formatter_Latency = FormatterRoutine(inputDir, algo, EPortTx_NumEn, df_STC=df_Emulator_Algo, verbose=verbose, algoLatency=algo_Latency, df_LinkReset=df_linkReset, df_BX_CNT=df_BX_CNT, linkResetOffset=linkResetOffset)
        if algo==2: #BC
            df_Emulator_Formatter, formatter_Latency = FormatterRoutine(inputDir, algo, EPortTx_NumEn, df_BestChoice=df_Emulator_Algo, verbose=verbose, algoLatency=algo_Latency, df_LinkReset=df_linkReset, df_BX_CNT=df_BX_CNT, linkResetOffset=linkResetOffset)
        if algo==3: #Repeater
            df_Emulator_Formatter, formatter_Latency = FormatterRoutine(inputDir, algo, EPortTx_NumEn, df_Repeater=df_Emulator_Algo, verbose=verbose, algoLatency=algo_Latency, df_LinkReset=df_linkReset, df_BX_CNT=df_BX_CNT, linkResetOffset=linkResetOffset)
        if algo==4: #Autoencoder
            df_Emulator_Formatter, formatter_Latency = FormatterRoutine(inputDir, algo, EPortTx_NumEn, df_Autoencoder=df_Emulator_Algo, verbose=verbose, algoLatency=algo_Latency, df_LinkReset=df_linkReset, df_BX_CNT=df_BX_CNT, linkResetOffset=linkResetOffset)

        T1 = getRegister(f'{inputDir}/Formatter_Buffer_Input_Buffer_Threshold_T1.csv')
        T2 = getRegister(f'{inputDir}/Formatter_Buffer_Input_Buffer_Threshold_T2.csv')
        T3 = getRegister(f'{inputDir}/Formatter_Buffer_Input_Buffer_Threshold_T3.csv')

        if verbose: print('Running Buffer')
        df_Emulator = Buffer(df_Emulator_Formatter, EPortTx_NumEn, T1, T2, T3)
        if verbose: print('   --- Finished Buffer')

        try:
            df_Comparison = pd.read_csv(f'{inputDir}/Formatter_Buffer_Output_buffer_ePortTx_DataIn.csv',skipinitialspace=True,comment=commentChar)[[f'BUF_OUT_TX_DATA_{i}' for i in range(13)]]

            df_Comparison.columns = [f'TX_DATA_{i}' for i in range(13)]
        except:
            df_Comparison = None

        latency = front_Latency + algo_Latency + formatter_Latency + 1

        hexOutput=True

    elif ASICBlock=="Full":

        latency=0
        if eRx_DataDir is None:
            eRx_DataDir=inputDir
        try:
            df_ePortRxDataGroup, df_BX_CNT, df_SimEnergyStatus, df_linkReset = loadEportRXData(eRx_DataDir,alignmentTime=alignmentTime)
        except:
            print(f'No EPortRx data found in directory {eRx_DataDir}')
            exit()
            
        columns = [f'ePortRxDataGroup_{i}' for i in range(12)]
        df_Mux_in = splitEportRXData(df_ePortRxDataGroup[columns])

        MuxRegisters = getRegister(f'{inputDir}/MuxFixCalib_Input_MuxSelect.csv')

        df_Mux_out = Mux(df_Mux_in, MuxRegisters)
        isHDM = getRegister(f'{inputDir}/MuxFixCalib_Input_HighDensity.csv')

        df_F2F = FloatToFix(df_Mux_out, isHDM)
        CALVALUE_Registers = getRegister(f'{inputDir}/MuxFixCalib_Input_CalValue.csv')

        df_CalQ = Calibrate(df_F2F, CALVALUE_Registers)

        front_Latency=11
        front_LinkReset_Offset=6

        algo = getRegister(f'{inputDir}/Formatter_Buffer_Input_Algorithm_Type.csv')

        if EPortTx_NumEn is None:
            EPortTx_NumEn = getRegister(f'{inputDir}/Formatter_Buffer_Input_EPortTx_NumEn.csv')

        df_Emulator_Algo, df_Comparison, algo_Latency = AlgorithmRoutine(inputDir, algo, verbose=verbose, df_CALQ = df_CalQ)

        if linkResetOffset is None:
            linkResetOffset = front_LinkReset_Offset + algo_Latency

        if algo==0: #threshold sum
            df_Emulator_Formatter, formatter_Latency = FormatterRoutine(inputDir, algo, EPortTx_NumEn, df_Threshold_Sum=df_Emulator_Algo, verbose=verbose, algoLatency=algo_Latency, df_LinkReset=df_linkReset, df_BX_CNT=df_BX_CNT, linkResetOffset=linkResetOffset)
        if algo==1: #STC
            df_Emulator_Formatter, formatter_Latency = FormatterRoutine(inputDir, algo, EPortTx_NumEn, df_STC=df_Emulator_Algo, verbose=verbose, algoLatency=algo_Latency, df_LinkReset=df_linkReset, df_BX_CNT=df_BX_CNT, linkResetOffset=linkResetOffset)
        if algo==2: #BC
            df_Emulator_Formatter, formatter_Latency = FormatterRoutine(inputDir, algo, EPortTx_NumEn, df_BestChoice=df_Emulator_Algo, verbose=verbose, algoLatency=algo_Latency, df_LinkReset=df_linkReset, df_BX_CNT=df_BX_CNT, linkResetOffset=linkResetOffset)
        if algo==3: #Repeater
            df_Emulator_Formatter, formatter_Latency = FormatterRoutine(inputDir, algo, EPortTx_NumEn, df_Repeater=df_Emulator_Algo, verbose=verbose, algoLatency=algo_Latency, df_LinkReset=df_linkReset, df_BX_CNT=df_BX_CNT, linkResetOffset=linkResetOffset)
        if algo==4: #Autoencoder
            df_Emulator_Formatter, formatter_Latency = FormatterRoutine(inputDir, algo, EPortTx_NumEn, df_Autoencoder=df_Emulator_Algo, verbose=verbose, algoLatency=algo_Latency, df_LinkReset=df_linkReset, df_BX_CNT=df_BX_CNT, linkResetOffset=linkResetOffset)

        T1 = getRegister(f'{inputDir}/Formatter_Buffer_Input_Buffer_Threshold_T1.csv')
        T2 = getRegister(f'{inputDir}/Formatter_Buffer_Input_Buffer_Threshold_T2.csv')
        T3 = getRegister(f'{inputDir}/Formatter_Buffer_Input_Buffer_Threshold_T3.csv')

        if verbose: print('Running Buffer')
        df_Buffer = Buffer(df_Emulator_Formatter, EPortTx_NumEn, T1, T2, T3)
        if verbose: print('   --- Finished Buffer')

        serializerDelayChange=[0]*13

        try:
            df_Comparison = None
            for iETX in range(13):
                dETX = pd.read_csv(f'{inputDir}/ETX_{format(iETX,"02")}.csv',dtype=str,skipinitialspace=True,comment=commentChar)[['OUT_DATA_PIN','INP_1G28_EN_ABC_40MHZ']]
                serializerDelayChange[iETX] = int(np.log2(int(dETX.INP_1G28_EN_ABC_40MHZ.values[0],16)))
                if df_Comparison is None:
                    df_Comparison = dETX[['OUT_DATA_PIN']]
                    df_Comparison.columns = [f'ETX_{iETX}']
                else:
                    df_Comparison[f'ETX_{iETX}'] = dETX[['OUT_DATA_PIN']]
        except:
            df_Comparison = None

        df_Emulator=Serializer(df_Buffer, serializerDelay, serializerDelayChange)

        latency = front_Latency + algo_Latency + formatter_Latency + 1

        hexOutput=True

    else:
        print('Unknown block to test', ASICBlock)
        exit()

    if df_Comparison is None or skipComparison:
        return True, df_Emulator, df_Comparison, latency

    if not df_ePortRxDataGroup is None and bxSkip == 'auto':
        print(f'Snapshot was at {snapshotOrbit}:{snapshotBucket}')
        print(f'Alignment time of {alignmentTime} used')

        startOrbit, startBucket = df_ePortRxDataGroup.index[0]
        if not snapshotOrbit is None:
            bxSkip = (snapshotOrbit - startOrbit)*3564 + (snapshotBucket - startBucket) + 162*2

    if not forceLatency is None:
        if verbose: print(f'Forcing latency of {forceLatency} to be used')
        latency=forceLatency

    if not bxSkip is None:
        try:
            bxSkip = int(bxSkip)
            if verbose: print(f'Dropping the initial {bxSkip} buckets from comparison')
            df_Emulator = df_Emulator[bxSkip:]
            df_Comparison = df_Comparison[bxSkip:]
            df_Emulator.reset_index(inplace=True,drop=True)
            df_Comparison.reset_index(inplace=True,drop=True)
        except:
            print(f'Argument of bxSkip ({bxSkip}) was not an int, will use whole dataset')
    if verbose: print(f'Latency={latency}')

    # for i in range(latency):        
    #     df_Emulator.drop(len(df_Emulator)-1,inplace=True)
    #     df_Comparison.drop(i,inplace=True)
    if latency>0:
        df_Emulator = df_Emulator[:-1*latency]
        df_Comparison =df_Comparison[latency:]

    df_Emulator.reset_index(inplace=True,drop=True)
    df_Comparison.reset_index(inplace=True,drop=True)

    matching = []
    mismatch = []
    if comparisonColumns is None:
        comparisonColumns = df_Comparison.columns
    for c in comparisonColumns:
        mine = df_Emulator[c].values
        cristians = df_Comparison[c].values
        compare= mine==cristians
        if verbose:
            print (c, "Agree" if compare.all() else "DISAGREE")

        if compare.all():
            matching.append(c)
        else:
            mismatch.append(c)

    if hexOutput:
        try:
            df_Emulator[comparisonColumns] = hex32(df_Emulator[comparisonColumns])
            df_Comparison[comparisonColumns] = hex32(df_Comparison[comparisonColumns])
        except:
            None

    if verbose:
        if len(mismatch)>0:
            misMatchBX = ~(df_Emulator[mismatch]==df_Comparison[mismatch]).all(axis=1)
            em = df_Emulator.loc[misMatchBX,mismatch].copy()
            ver = df_Comparison.loc[misMatchBX,mismatch].copy()
            
            print()
            print()
            print("DISAGREEMENT COLUMNS")
            print("Emulator:")
            print(em)
            print()
            print("Verilog:")
            print(ver)
        else:
            print()
            print("GOOD AGREEMENT")
            print()

        if 'Buffer' in ASICBlock and not 'Serializer' in ASICBlock:
            print()
            print('Buffer Control Summary Counts')
            x = df_Emulator[[f'Cond{i}' for i in range(1,5)]]
            x.columns = ['T1 Truncations','T2 Truncations', 'T3 Full Data','Full Data']
            print(x.sum().to_string())
            print()

    return len(mismatch)==0, df_Emulator, df_Comparison, latency

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
    parser.add_argument('--eTx',dest="EPortTx_NumEn", default=None, type=int, help='Number of eTx to use (if None, use value in csv files)')
    parser.add_argument('--eRx',dest="eRx_DataDir", default=None, help='Location to look for input data to EPortRX used in simulation')
    parser.add_argument('--skip', '--bxSkip',dest="bxSkip", default=None,  help='Number of BX to skip before starting the comparison')
    parser.add_argument('-l', '--latency',dest="forceLatency", default=None, type=int, help='Latency to use, if None, use assumptions based on blocks run')
    parser.add_argument('--delay','--serializerDelay',dest="serializerDelay", default=101, type=int, help='Initial delay of serializer, in bits, default of 101')
    parser.add_argument('--alignment', '--align',dest="forceAlignmentTime", default=None, type=int, help='Alignment time to use, if None, use what can be found from sim information')
    parser.add_argument('-r', '--reset','--resetOffset',dest="linkResetOffset", default=None, type=int, help='Amount to move the link reset offset by')
    parser.add_argument('-q','--quiet', dest="Quiet", default=False, action='store_true', help='Quiet outputs')

    args = parser.parse_args()
    
    passVerification, df_Mine, df_Cristian, latency= runVerification(**vars(args))
    if args.Quiet: print("    PASS" if passVerification else "xxxxFAIL", latency)
