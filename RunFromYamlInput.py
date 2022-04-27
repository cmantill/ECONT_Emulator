import pandas as pd
import numpy as np
import yaml

from ASICBlocks.LoadData_ePortRX import loadMetaData, loadEportRXData, splitEportRXData
from ASICBlocks.MuxFixCalib import getMuxRegisters, Mux, FloatToFix, getCalibrationRegisters_Thresholds, Calibrate
from ASICBlocks.Algorithms import makeCHARGEQ, ThresholdSum, BestChoice, SuperTriggerCell, Repeater, Algorithms
from ASICBlocks.Autoencoder import Autoencoder, convertI2CtoWeights
from ASICBlocks.Formatter import Format_Threshold_Sum, Format_BestChoice, Format_SuperTriggerCell, Format_Repeater, Format_Autoencoder
from ASICBlocks.BufferBlock import Buffer


#really, the two functions should be incorporated into

#read in dictionary from yaml file, and parse all of the i2c settings to specific register values
def loadDefaults(regYaml):
    registerValues = {}
    for k in regYaml.keys():
        for regName in regYaml[k]['registers']:
            reg = regYaml[k]['registers'][regName]

            if 'params' in reg:
                params = reg['params']
                val = reg['value']

                prefix = f"{k.replace('*','')}_{regName}_"
                prefix = prefix.replace('config_','')

                for r in params:
                    # print(regName,params[r])
                    mask = params[r]['param_mask']
                    shift = params[r]['param_shift']
                    paramName = f'{prefix}{r}'

                    if '*' in paramName:
                        for i,v in enumerate(val):
                            registerValues[paramName.replace('*',f'{i}')]=(v>>shift)&mask
                    else:
                        registerValues[paramName]=(val>>shift)&mask

            else:
                paramName = f"{k.replace('*','')}_{regName}"
                val = reg['value']

                if '*' in paramName:
                    for i,v in enumerate(val):
                        registerValues[paramName.replace('*',f'{i}')]=v
                else:
                    registerValues[paramName]=val

    return registerValues

def loadUpdates(regYaml):
    registerValues = {}
    for k in regYaml:
        for regName,out in regYaml[k]['registers'].items():
            if 'value' in out:
                rName = f'{k.replace("*","")}_{regName}'
                if '*' in rName:
                    for i,v in enumerate(out['value']):
                        registerValues[rName.replace('*',f'{i}')] = v
                else:
                    registerValues[rName] = out['value']
            elif 'params' in out:
                for r in out['params']:
                    rName = f'{k.replace("*","")}_{regName}_{r}'.replace('_config_','_')
                    registerValues[rName] = out['params'][r]['param_value']
            else:
                rName = f'{k.replace("*","")}_{regName}'
                for r in out:
                    rName = f'{k.replace("*","")}_{regName}_{r}'.replace('_config_','_')
                    registerValues[rName] = out[r]['param_value']

    return registerValues

def toDecimal(x):
    w = -1. if x[0]=='1' else 0
    w += int(x[1:],2)/2**5
    return w

def i2cDictToWeights(i2cDict):
    bits=''
    for i in range(12)[::-1]:
        reg_name=f'AUTOENCODER_{i}INPUT_weights_byte128'
        r=f'{i2cDict[reg_name]:048b}'
        bits += r
        for j in range(0,127,16)[::-1]:
            reg_name=f'AUTOENCODER_{i}INPUT_weights_byte{j}'
            r=f'{i2cDict[reg_name]:0128b}'
            bits += r
    wbWB=[toDecimal(bits[i:i+6]) for i in range(0,len(bits),6)][::-1]
    _w=wbWB[:72]
    _b=wbWB[72:80]
    _W=wbWB[80:2128]
    _B=wbWB[2128:]
    return _w,_b,_W,_B



def AlgorithmRoutine(algo, df_CALQ, i2cDict, verbose=True):
    if verbose: print('Running Algorithm')

    df_CALQ.reset_index(inplace=True,drop=True)

    df_DropLSB = pd.DataFrame({'DropLSB':i2cDict['ALGO_DROPLSB_drop_lsb']},index=df_CALQ.index)
    df_DropLSB.loc[df_DropLSB.DropLSB>4] = 0

    df_Threshold = np.array([i2cDict[f'ALGO_THRESHOLD_VAL_threshold_val_{i}'] for i in range(48)])
    if algo==0: #threshold sum
        print('algo TS')
        latency=1
        df_Emulator=ThresholdSum(df_CALQ, df_Threshold, df_DropLSB)

    elif algo==1: #STC
        print('algo STC')
        latency = 1
        df_Emulator = SuperTriggerCell(df_CALQ, df_DropLSB)

    elif algo==2: #BC
        print('algo BC')
        latency = 2
        df_Emulator = BestChoice(df_CALQ, df_DropLSB)

    elif algo==3: #RPT
        print('algo RPT')
        latency = 1
        df_Emulator = Repeater(df_CALQ, df_DropLSB)


    elif algo==4: #AE
        latency=2

        weights = i2cDictToWeights(i2cDict)
        df_Emulator = Autoencoder(df_CALQ.reset_index(drop=True),weights)

    else:
        print(f'unknown algorithm type : {algo}')
        exit()

    if verbose: print('   --- Finished Algorithm')
    return df_Emulator.reset_index(), latency

def FormatterRoutine(algo,
                     EPortTx_NumEn,
                     i2cDict,
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
    STC_Type = i2cDict['FMTBUF_ALL_stc_type']
    TxSyncWord = i2cDict['FMTBUF_ALL_tx_sync_word']

    df_BX_CNT.reset_index(inplace=True,drop=True)

    if algo==0: #threshold sum

        latency=1

        Use_Sum = pd.DataFrame({'USE_SUM':i2cDict['FMTBUF_ALL_use_sum']},index=df_BX_CNT.index)

        df_Emulator = Format_Threshold_Sum(df_Threshold_Sum, df_BX_CNT, TxSyncWord, Use_Sum, EPortTx_NumEn, df_LinkReset).drop('IdleWord',axis=1)

    elif algo==1: #STC
        latency=1
        print('type ',STC_Type)
        df_Emulator = Format_SuperTriggerCell(df_STC, STC_Type, EPortTx_NumEn, df_BX_CNT, TxSyncWord, df_LinkReset).drop('IdleWord',axis=1)

    elif algo==2: #BC
        latency=3

        Use_Sum = pd.DataFrame({'USE_SUM':i2cDict['FMTBUF_ALL_use_sum']},index=df_BX_CNT.index)

        df_Emulator = Format_BestChoice(df_BestChoice,EPortTx_NumEn, df_BX_CNT, TxSyncWord, Use_Sum, df_LinkReset).drop('IdleWord',axis=1)

    elif algo==3: #RPT
        latency=1

        df_Emulator = Format_Repeater(df_Repeater, df_BX_CNT, TxSyncWord, EPortTx_NumEn, df_LinkReset).drop('IdleWord',axis=1)

    elif algo==4: #AE
        latency=2

        maskBytes=[(i2cDict['FMTBUF_ALL_mask_ae2']>>(8*i)) & 0xff for i in range(2)] + [(i2cDict['FMTBUF_ALL_mask_ae']>>(8*i)) & 0xff for i in range(16)]
        maskBytes_dict={}
        for i in range(18):
            maskBytes_dict[f'KAEB_BYTE{i}']=maskBytes[i]

        df_AEMask = pd.DataFrame(maskBytes_dict,index=df_BX_CNT.index)
        df_Emulator = Format_Autoencoder(df_Autoencoder, df_BX_CNT, df_AEMask, EPortTx_NumEn, TxSyncWord, df_LinkReset).drop('IdleWord',axis=1)

    if verbose: print('   --- Finished Formatter')
    return df_Emulator.merge(df_BX_CNT, left_index=True, right_index=True), latency



def runEmulator(inputDir, defaultRegMapDir, verbose=False):
    with open(f'{inputDir}/init.yaml','r') as _file:
        runSpecificSetup = yaml.safe_load(_file)

    with open(f'{defaultRegMapDir}/ECON_I2C_params_regmap.yaml','r') as _file:
        defaultI2C = yaml.safe_load(_file)

    i2cDict = {**loadDefaults(defaultI2C['ECON-T']['RW']),
               **loadUpdates(runSpecificSetup['ECON-T']['RW'])}

    eRx_Data=f'{inputDir}/../testInput.csv'
    alignmentTime=256

    latency=0
    try:
        df_ePortRxDataGroup, df_BX_CNT, df_SimEnergyStatus, df_linkReset = loadEportRXData(eRx_Data,alignmentTime=alignmentTime)
    except:
        print(f'No EPortRx data found in directory {eRx_Data}')
        exit()

    columns = [f'ePortRxDataGroup_{i}' for i in range(12)]
    df_Mux_in = splitEportRXData(df_ePortRxDataGroup[columns])

    MuxRegisters = [i2cDict[f'MFC_MUX_SELECT_mux_select_{i}'] for i in range(48)]
    CALVALUE_Registers=[i2cDict[f'MFC_CAL_VAL_cal_{i}'] for i in range(48)]
    isHDM = i2cDict['MFC_ALGORITHM_SEL_DENSITY_algo_density']
    algo = i2cDict['MFC_ALGORITHM_SEL_DENSITY_algo_select']

    df_Mux_out = Mux(df_Mux_in, MuxRegisters)
    df_F2F = FloatToFix(df_Mux_out, isHDM)
    df_CalQ = Calibrate(df_F2F, CALVALUE_Registers)

    front_Latency=11
    front_LinkReset_Offset=6

    EPortTx_NumEn = i2cDict['FMTBUF_ALL_eporttx_numen']

    df_Emulator_Algo, algo_Latency = AlgorithmRoutine(algo, verbose=verbose, df_CALQ = df_CalQ,i2cDict=i2cDict)

    linkResetOffset=None
    if linkResetOffset is None:
        linkResetOffset = front_LinkReset_Offset + algo_Latency
    if algo==0: #threshold sum
        df_Emulator_Formatter, formatter_Latency = FormatterRoutine(algo, EPortTx_NumEn, i2cDict=i2cDict, df_Threshold_Sum=df_Emulator_Algo, verbose=verbose, algoLatency=algo_Latency, df_LinkReset=df_linkReset, df_BX_CNT=df_BX_CNT, linkResetOffset=linkResetOffset)
    elif algo==1: #STC
        df_Emulator_Formatter, formatter_Latency = FormatterRoutine(algo, EPortTx_NumEn, i2cDict=i2cDict, df_STC=df_Emulator_Algo, verbose=verbose, algoLatency=algo_Latency, df_LinkReset=df_linkReset, df_BX_CNT=df_BX_CNT, linkResetOffset=linkResetOffset)
    elif algo==2: #BC
        df_Emulator_Formatter, formatter_Latency = FormatterRoutine(algo, EPortTx_NumEn, i2cDict=i2cDict, df_BestChoice=df_Emulator_Algo, verbose=verbose, algoLatency=algo_Latency, df_LinkReset=df_linkReset, df_BX_CNT=df_BX_CNT, linkResetOffset=linkResetOffset)
    elif algo==3: #Repeater
        df_Emulator_Formatter, formatter_Latency = FormatterRoutine(algo, EPortTx_NumEn, i2cDict=i2cDict, df_Repeater=df_Emulator_Algo, verbose=verbose, algoLatency=algo_Latency, df_LinkReset=df_linkReset, df_BX_CNT=df_BX_CNT, linkResetOffset=linkResetOffset)
    elif algo==4: #Autoencoder
        df_Emulator_Formatter, formatter_Latency = FormatterRoutine(algo, EPortTx_NumEn, i2cDict=i2cDict, df_Autoencoder=df_Emulator_Algo, verbose=verbose, algoLatency=algo_Latency, df_LinkReset=df_linkReset, df_BX_CNT=df_BX_CNT, linkResetOffset=linkResetOffset)

    T1 = i2cDict['FMTBUF_ALL_buff_t1']
    T2 = i2cDict['FMTBUF_ALL_buff_t2']
    T3 = i2cDict['FMTBUF_ALL_buff_t3']

    if verbose: print('Running Buffer')
    df_Emulator = Buffer(df_Emulator_Formatter, EPortTx_NumEn, T1, T2, T3)
    if verbose: print('   --- Finished Buffer')

    latency = front_Latency + algo_Latency + formatter_Latency + 1

    hexOutput=True

    def hex32(x):
        return format(x, '08x')
    hex32 = np.vectorize(hex32)

    c = [f'TX_DATA_{i}' for i in range(13)]
    cHex = [f'HEX_TX_DATA_{i}' for i in range(13)]

    df_Emulator[c] = pd.DataFrame(hex32(df_Emulator[c]),columns=c,index=df_Emulator.index)
    df_Emulator[c].to_csv(f'{inputDir}/testOutput.csv',index=False)

if __name__=='__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--inputDir', default = ' ../econt_sw/configs/test_vectors/counterPatternInTC/RPT/', dest="inputDir", help="Input directory containing testInput.csv and init.yaml files")
    parser.add_argument('--defaultCfg', default = '../econt_sw/zmq_i2c/reg_maps/', dest="defaultRegMapDir", help="Directory containing default register map")
    parser.add_argument('-v', default = False, action='store_true', dest="verbose", help="Verbose output")

    args = parser.parse_args()

    runEmulator(inputDir = args.inputDir,
                defaultRegMapDir = args.defaultRegMapDir,
                verbose = args.verbose)
