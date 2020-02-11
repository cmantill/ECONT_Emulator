import pandas as pd
import numpy as np
import os

def toBin(x,nDigits=5):
    return format(x, '#0%ib'%(nDigits+2))[2:]
toBin = np.vectorize(toBin)

def replaceHeader(val, header, nDigits=5):
    return header + val[nDigits:]
replaceHeader = np.vectorize(replaceHeader)


def sampleData(_subdetector = 3, _layer = 5, _wafer = 31, nBX=5000, samplingList=None, directoryName="./", outputName="outputTest"):

    wafer = f'D{_subdetector}L{_layer}W{_wafer}'

    inputData = f'{directoryName}/wafer_{wafer}'

    InputEPORTRX = pd.read_csv(f'{inputData}/EPORTRX_output.csv',index_col='entry')
    InputSM = pd.read_csv(f'{inputData}/SM_output.csv',index_col='entry')
    InputCALQ = pd.read_csv(f'{inputData}/CALQ_output.csv',index_col='entry')
    Registers = pd.read_csv(f'{inputData}/registers_{wafer}.csv')
    
    Threshold_AddMap = pd.read_csv(f'{inputData}/threshold_address.csv',index_col='entry')
    Threshold_Charge = pd.read_csv(f'{inputData}/threshold_charge.csv',index_col='entry')
    Threshold_Wafer = pd.read_csv(f'{inputData}/threshold_wafer.csv',index_col='entry')
    Threshold_Format = pd.read_csv(f'{inputData}/threshold_formatblock.csv',index_col='entry',dtype=np.object)
    
    BC_Addresses = pd.read_csv(f'{inputData}/bc_address.csv',index_col='entry')
    BC_Addresses.columns = [f'BC_TC_MAP_{i}' for i in range(48)]
    BC_Charge = pd.read_csv(f'{inputData}/bc_charge.csv',index_col='entry')
    BC_Format = pd.read_csv(f'{inputData}/bc_formatblock.csv',index_col='entry',dtype=np.object)
    
    STC_Idx = pd.read_csv(f'{inputData}/stc_idx.csv',index_col='entry')
    STC_Sum = pd.read_csv(f'{inputData}/stc_sum.csv',index_col='entry')
    STC_Format = pd.read_csv(f'{inputData}/stc_formatblock.csv',index_col='entry',dtype=np.object)
    
    RPT_Chg = pd.read_csv(f'{inputData}/repeater_charge.csv',index_col='entry')
    RPT_Format = pd.read_csv(f'{inputData}/repeater_formatblock.csv',index_col='entry',dtype=np.object)
    
    isHDM = Registers.isHDM.loc[0]

    outputDir = f'{outputName}_{wafer}'
    os.makedirs(outputDir,exist_ok=True)

    nBX = 5000

    if samplingList is None:
        SamplingOrder = []    
        SamplingOrder = np.random.choice(InputCALQ.index.values,nBX)
    else:
        SamplingOrder = np.array(samplingLinst)
        nBX = len(SamplingOrder)
    np.savetxt(f'{outputDir}/EventSampleOrder.csv', SamplingOrder,fmt='%d', header='entry',comments="")

    with open(f'{outputDir}/WaferInfo.txt','w') as _file:
        _file.write(f'InputData {inputData}\n')
        _file.write(f'Subdet {_subdetector}\n')
        _file.write(f'Layer {_layer}\n')
        _file.write(f'Wafer {_wafer}\n')

    #### Track Registers

    calibReg = pd.read_csv(f'{inputData}/calib_{wafer}.csv')
    threshReg = pd.read_csv(f'{inputData}/thres_{wafer}.csv')
    
    output=open(f'{outputDir}/Registers.csv','w')
    for i in range(48):
        output.write(f'CALV_{i},')
    for i in range(48):
        output.write(f'THRESV_{i},')
    output.write('HIGH_DENSITY\n')

    for i,c in enumerate(calibReg.values[0]):
        c = int(c*2**11)
        output.write(f'{c},')

    for i,c in enumerate(threshReg.values[0]):
        output.write(f'{c},')

    output.write(f'{int(isHDM)}\n')

    output.close()

    #need to track is HDM
    headerValues = np.arange(len(SamplingOrder))%32
    np.savetxt(f'{outputDir}/Algorithm_Input_Header.csv', headerValues,fmt='%d', header='HEADER',comments="")
    np.savetxt(f'{outputDir}/Algorithm_Output_Header.csv', headerValues,fmt='%d', header='HEADER',comments="")

    InputEPORTRX.loc[SamplingOrder].to_csv(f'{outputDir}/Algorithm_Input_ePortRX.csv',index=False)
    InputSM.loc[SamplingOrder].to_csv(f'{outputDir}/Algorithm_Input_SM.csv',index=False)
    InputCALQ.loc[SamplingOrder].to_csv(f'{outputDir}/Algorithm_Input_CalQ.csv',index=False)

    Threshold_AddMap.loc[SamplingOrder].to_csv(f'{outputDir}/Algorithm_Output_AddrMap.csv',index=False)
    Threshold_Charge.loc[SamplingOrder].to_csv(f'{outputDir}/Algorithm_Output_ChargeQ.csv',index=False)
    Threshold_Wafer.loc[SamplingOrder,["NTCQ"]].to_csv(f'{outputDir}/Algorithm_Output_NTCQ.csv',index=False)
    Threshold_Wafer.loc[SamplingOrder,["SUM"]].to_csv(f'{outputDir}/Algorithm_Output_Sum.csv',index=False)
    Threshold_Wafer.loc[SamplingOrder,["MOD_SUM_0","MOD_SUM_1","MOD_SUM_2"]].to_csv(f'{outputDir}/Algorithm_Output_Mod_Sum.csv',index=False)

    BC_Addresses.loc[SamplingOrder].to_csv(f'{outputDir}/Algorithm_Output_BC_TC_map.csv',index=False)
    BC_Charge.loc[SamplingOrder].to_csv(f'{outputDir}/Algorithm_Output_BC_Charge.csv',index=False)
    
    STC_Sum.columns = [f'STC_2x2_SUM_{i}' for i in range(12)]
    STC_Sum.loc[SamplingOrder].to_csv(f'{outputDir}/Algorithm_Output_STC_2x2_Sum.csv',index=False)
    STC_Idx.loc[SamplingOrder].to_csv(f'{outputDir}/Algorithm_Output_STC_Idx.csv',index=False)

    RPT_Chg.loc[SamplingOrder].to_csv(f'{outputDir}/Algorithm_Output_RepeaterQ.csv',index=False)

    head = toBin(headerValues)

    sampledThresholdFormat = Threshold_Format.loc[SamplingOrder]
    sampledBCFormat = BC_Format.loc[SamplingOrder]
    sampledSTCFormat = STC_Format.loc[SamplingOrder]
    sampledRPTFormat = RPT_Format.loc[SamplingOrder]

    sampledThresholdFormat['FRAMEQ'] = replaceHeader(sampledThresholdFormat.FRAMEQ,head)
    sampledThresholdFormat['FRAMEQ_TRUNC'] = replaceHeader(sampledThresholdFormat.FRAMEQ_TRUNC,head)
    sampledThresholdFormat['WORD_0'] = replaceHeader(sampledThresholdFormat.WORD_0,head)
    
    sampledBCFormat['FRAMEQ'] = replaceHeader(sampledBCFormat.FRAMEQ,head)
    sampledBCFormat['WORD_0'] = replaceHeader(sampledBCFormat.WORD_0,head)

    sampledSTCFormat['FRAMEQ'] = replaceHeader(sampledSTCFormat.FRAMEQ,head)
    sampledSTCFormat['WORD_0'] = replaceHeader(sampledSTCFormat.WORD_0,head)

    sampledRPTFormat['FRAMEQ'] = replaceHeader(sampledRPTFormat.FRAMEQ,head)
    sampledRPTFormat['WORD_0'] = replaceHeader(sampledRPTFormat.WORD_0,head)

    cols =[f'WORD_{i}' for i in range(25)]
    sampledThresholdFormat[cols+['FRAMEQ_TRUNC']].to_csv(f'{outputDir}/Algorithm_Output_Format.csv',index=False)
    sampledBCFormat[cols].to_csv(f'{outputDir}/Algorithm_Output_BC_Format.csv',index=False)
    sampledSTCFormat[cols[:10]].to_csv(f'{outputDir}/Algorithm_Output_STC_Format.csv',index=False)
    sampledRPTFormat[cols].to_csv(f'{outputDir}/Algorithm_Output_RPT_Format.csv',index=False)

    return

sampleData(_subdetector = 3, _layer = 5, _wafer = 31, nBX=5000, samplingList=None, directoryName="ttbarData_subdet_EE_layer_5", outputName="outputTest")

