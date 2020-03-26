import optparse
import pandas as pd
import numpy as np
import os
import re

def toBin(x,nDigits=5):
    return format(x, '#0%ib'%(nDigits+2))[2:]
toBin = np.vectorize(toBin)

def replaceHeader(val, header, nDigits=5):
    return header + val[nDigits:]
replaceHeader = np.vectorize(replaceHeader)

def shiftBits(x,nDigits=11):
    return x<<nDigits
shiftBits= np.vectorize(shiftBits)


def sampleData(directoryName="./", outputName="outputTest", nBX=5000, samplingList=None, extraName=None):

    waferInfo = re.search('\w+_D(\d+)L(\d+)W(\d+)',directoryName)
    if waferInfo is None:
        waferInfo = re.search('\w+_D(\d+)L(\d+)U(\d+)V(\d+)',directoryName)
        

    if not waferInfo is None:
        _subdetector = int(waferInfo.groups()[0])
        _layer = int(waferInfo.groups()[1])
        if len(waferInfo.groups())==3:
            _wafer = int(waferInfo.groups()[2])
        else:
            _waferU = int(waferInfo.groups()[2])
            _waferV = int(waferInfo.groups()[3])
#            wafer = f'D{_subdetector}L{_layer}U{_waferU}V{_waferV}'
            _wafer=100*_waferU+_waferV
    else:
        _subdetector = 0
        _layer=0
        _wafer=0


    wafer = f'D{_subdetector}L{_layer}W{_wafer}'
    inputData = directoryName

    InputEPORTRX = pd.read_csv(f'{inputData}/EPORTRX_output.csv',index_col='entry')
    for c in InputEPORTRX.columns:
        InputEPORTRX[c] = InputEPORTRX[c].apply(int,args=(2,))
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
    if extraName is not None:
        outputDir = f'{outputName}_{wafer}_{extraName}'

    os.makedirs(outputDir,exist_ok=True)

    if samplingList is None:
        SamplingOrder = []    
        SamplingOrder = np.random.choice(InputCALQ.index.values,nBX)
    else:
        SamplingOrder = pd.read_csv(samplingList)['entry'].values
#        SamplingOrder = np.array(samplingLinst)
        nBX = len(SamplingOrder)
    print(SamplingOrder)

    np.savetxt(f'{outputDir}/EventSampleOrder.csv', SamplingOrder,fmt='%d', header='entry',comments="")

    with open(f'{outputDir}/WaferInfo.txt','w') as _file:
        _file.write(f'InputData {inputData}\n')
        _file.write(f'Subdet {_subdetector}\n')
        _file.write(f'Layer {_layer}\n')
        _file.write(f'Wafer {_wafer}\n')

    #### Track Registers

    calibReg = pd.read_csv(f'{inputData}/calib_{wafer}.csv')
    threshReg = pd.read_csv(f'{inputData}/thres_{wafer}.csv')

    threshReg = threshReg.loc[threshReg.index.repeat(nBX)]
    threshReg.columns = [f'THRESHV_{i}' for i in range(48)]
    threshReg.to_csv(f'{outputDir}/Algorithm_Input_Threshold.csv',index=False)

    calibReg = calibReg.loc[calibReg.index.repeat(nBX)]
    calibReg.columns = [f'CALV_{i}' for i in range(48)]
    calibReg = (calibReg*2**11).astype(int)
    calibReg.to_csv(f'{outputDir}/Calibration_Input_Calibration.csv',index=False)

    registers = Registers.loc[Registers.index.repeat(nBX)]
    registers.columns = ['HIGH_DENSITY','DROPPED_BITS']
    registers[['HIGH_DENSITY']].astype(int).to_csv(f'{outputDir}/Algorithm_Input_HighDensity.csv',index=False)
    registers[['DROPPED_BITS']].astype(int).to_csv(f'{outputDir}/Algorithm_Input_DroppedBits.csv',index=False)

    type_TS = pd.DataFrame({'TYPE':[0]*nBX})
    type_TS.to_csv(f'{outputDir}/Algorithm_Input_Type_TS.csv',index=False)
    type_STC = pd.DataFrame({'TYPE':[1]*nBX})
    type_STC.to_csv(f'{outputDir}/Algorithm_Input_Type_STC.csv',index=False)
    type_BC = pd.DataFrame({'TYPE':[2]*nBX})
    type_BC.to_csv(f'{outputDir}/Algorithm_Input_Type_BC.csv',index=False)
    type_RPT = pd.DataFrame({'TYPE':[3]*nBX})
    type_RPT.to_csv(f'{outputDir}/Algorithm_Input_Type_RPT.csv',index=False)

    #need to track is HDM
    headerValues = np.arange(len(SamplingOrder))%32
    np.savetxt(f'{outputDir}/Algorithm_Input_Header.csv', headerValues,fmt='%d', header='HEADER',comments="")
    np.savetxt(f'{outputDir}/Algorithm_Output_Header.csv', headerValues,fmt='%d', header='HEADER',comments="")

    InputEPORTRX.astype(int).loc[SamplingOrder].to_csv(f'{outputDir}/Mux_Input_ePortRX.csv',index=False)
    InputSM.loc[SamplingOrder].to_csv(f'{outputDir}/Mux_Output_SM.csv',index=False)
    InputCALQ.loc[SamplingOrder].to_csv(f'{outputDir}/Algorithm_Input_CalQ.csv',index=False)

    Threshold_AddMap.loc[SamplingOrder].to_csv(f'{outputDir}/Algorithm_Output_AddrMap.csv',index=False)
    Threshold_Charge.loc[SamplingOrder].to_csv(f'{outputDir}/Algorithm_Output_ChargeQ.csv',index=False)
    Threshold_Wafer.loc[SamplingOrder,["NTCQ"]].to_csv(f'{outputDir}/Algorithm_Output_NTCQ.csv',index=False)
    Threshold_Wafer.loc[SamplingOrder,["SUM"]].to_csv(f'{outputDir}/Algorithm_Output_Sum.csv',index=False)
    Threshold_Wafer['MOD_SUM'] = shiftBits(Threshold_Wafer.MOD_SUM_0,0) + shiftBits(Threshold_Wafer.MOD_SUM_1,8) + shiftBits(Threshold_Wafer.MOD_SUM_2,16)
    Threshold_Wafer.loc[SamplingOrder,["MOD_SUM"]].to_csv(f'{outputDir}/Algorithm_Output_Mod_Sum.csv',index=False)

    BC_Addresses.loc[SamplingOrder].to_csv(f'{outputDir}/Algorithm_Output_BC_TC_map.csv',index=False)
    BC_Charge.loc[SamplingOrder].to_csv(f'{outputDir}/Algorithm_Output_BC_Charge.csv',index=False,header=[f'BC_CHARGE_{i}' for i in range(48)])

    Cols_STC_2x2_Sum = [f'STC_2x2_SUM_{i}' for i in range(12)]
    Cols_STC_2x2_Idx = [f'STC_2x2_IDX_{i}' for i in range(12)]

    Cols_Mod_Sum = [f'MOD_SUM_STC_{i}' for i in range(3)]
    Cols_Mod_Sum_Idx = [f'MOD_SUM_STC_IDX_{i}' for i in range(3)]

    STC_Sum.columns = Cols_STC_2x2_Sum + Cols_Mod_Sum
    STC_Idx.columns = Cols_STC_2x2_Idx + Cols_Mod_Sum_Idx

    STC_Sum.loc[SamplingOrder,Cols_STC_2x2_Sum].to_csv(f'{outputDir}/Algorithm_Output_STC_2x2_Sum.csv',index=False)
    STC_Idx.loc[SamplingOrder,Cols_STC_2x2_Idx].to_csv(f'{outputDir}/Algorithm_Output_STC_Idx.csv',index=False)
    

    STC_Sum['MOD_SUM_STC'] = shiftBits(STC_Sum.MOD_SUM_STC_0,0) + shiftBits(STC_Sum.MOD_SUM_STC_1,8) + shiftBits(STC_Sum.MOD_SUM_STC_2,16)
    STC_Sum.loc[SamplingOrder,['MOD_SUM_STC']].to_csv(f'{outputDir}/Algorithm_Output_Mod_Sum_stc.csv',index=False)
    STC_Idx.loc[SamplingOrder,Cols_Mod_Sum_Idx].to_csv(f'{outputDir}/Algorithm_Output_Mod_Sum_Idx_stc.csv',index=False)

    RPT_Chg.loc[SamplingOrder].to_csv(f'{outputDir}/Algorithm_Output_RepeaterQ.csv',index=False)



    sampledEPORTRXInput = InputEPORTRX.loc[SamplingOrder]
    for c in sampledEPORTRXInput.columns:
        sampledEPORTRXInput[c] = sampledEPORTRXInput[c] + (headerValues<<24)

    
    sampledEPORTRXInput['godOrbitNumber'] = (np.arange(len(SamplingOrder))/3564).astype(int)
    sampledEPORTRXInput['godBucketNumber'] = np.arange(len(SamplingOrder))%3564
    sampledEPORTRXInput.set_index(['godOrbitNumber','godBucketNumber'],inplace=True)
    sampledEPORTRXInput.to_csv(f'{outputDir}/EPORTRX_Input.csv',index=True)

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


    cols =[f'WORD_{i}' for i in range(28)]

    TX_SYNC_WORD='00000000000'

    sampledThresholdFormat['NULLVAL'] = shiftBits(headerValues) + int(TX_SYNC_WORD)
    sampledBCFormat['NULLVAL'] = shiftBits(headerValues) + int(TX_SYNC_WORD)
    sampledSTCFormat['NULLVAL'] = shiftBits(headerValues) + int(TX_SYNC_WORD)
    sampledRPTFormat['NULLVAL'] = shiftBits(headerValues) + int(TX_SYNC_WORD)

    # print(sampledThresholdFormat[cols].head())
    # print(sampledThresholdFormat[cols].notna().sum(axis=1))
    # print(sampledThresholdFormat[cols].iloc[0].values)

    sampledThresholdFormat['wordCount'] = sampledThresholdFormat[cols].notna().sum(axis=1)
    sampledRPTFormat['wordCount'] = sampledRPTFormat[cols].notna().sum(axis=1)
    sampledSTCFormat['wordCount'] = sampledSTCFormat[cols].notna().sum(axis=1)
    sampledBCFormat['wordCount'] = sampledBCFormat[cols].notna().sum(axis=1)

    sampledThresholdFormat['FRAMEQ_TRUNC'] = sampledThresholdFormat['FRAMEQ_TRUNC'].apply(int,args=(2,))

    for c in cols:
        sampledThresholdFormat.loc[sampledThresholdFormat[c].notna(),c] = sampledThresholdFormat.loc[sampledThresholdFormat[c].notna(),c].apply(int,args=(2,))
        sampledThresholdFormat.loc[sampledThresholdFormat[c].isna(),c] = sampledThresholdFormat.loc[sampledThresholdFormat[c].isna(),'NULLVAL']        

        sampledBCFormat.loc[sampledBCFormat[c].notna(),c] = sampledBCFormat.loc[sampledBCFormat[c].notna(),c].apply(int,args=(2,))
        sampledBCFormat.loc[sampledBCFormat[c].isna(),c] = sampledBCFormat.loc[sampledBCFormat[c].isna(),'NULLVAL']        

        sampledSTCFormat.loc[sampledSTCFormat[c].notna(),c] = sampledSTCFormat.loc[sampledSTCFormat[c].notna(),c].apply(int,args=(2,))
        sampledSTCFormat.loc[sampledSTCFormat[c].isna(),c] = sampledSTCFormat.loc[sampledSTCFormat[c].isna(),'NULLVAL']        

        sampledRPTFormat.loc[sampledRPTFormat[c].notna(),c] = sampledRPTFormat.loc[sampledRPTFormat[c].notna(),c].apply(int,args=(2,))
        sampledRPTFormat.loc[sampledRPTFormat[c].isna(),c] = sampledRPTFormat.loc[sampledRPTFormat[c].isna(),'NULLVAL']        

    sampledThresholdFormat[cols+['FRAMEQ_TRUNC','wordCount']].to_csv(f'{outputDir}/Formatter_Output_ThresholdSum.csv',index=False)
    sampledBCFormat[cols + ['wordCount']].to_csv(f'{outputDir}/Formatter_Output_BC.csv',index=False)
    sampledSTCFormat[cols + ['wordCount']].to_csv(f'{outputDir}/Formatter_Output_STC.csv',index=False)
    sampledRPTFormat[cols + ['wordCount']].to_csv(f'{outputDir}/Formatter_Output_RPT.csv',index=False)

    sampledThresholdFormat['TX_SYNC_WORD'] = int(TX_SYNC_WORD)
    sampledThresholdFormat[['TX_SYNC_WORD']].to_csv(f'{outputDir}/Formatter_Buffer_Input_Tx_Sync_Word.csv',index=False)

    return outputDir


import glob
def alterCSVFiles(outputDir):
    csvFiles = glob.glob(f'{outputDir}/*csv')

    for fName in csvFiles:
        with open(fName, "r") as sources:
            lines = sources.readlines()
        with open(fName, "w") as sources:
            for line in lines:
                sources.write(line.replace(',',', '))




if __name__=='__main__':
    parser = optparse.OptionParser()
    parser.add_option('-i',"--inputDir", type="string", default = None,dest="inputDir", help="input directory to sample")
    parser.add_option('-o',"--output", type="string", default = "outputData",dest="outputName", help="file name for output")
    parser.add_option('-N',"--nBX", type=int, default = None,dest="nBX", help="number of BX to simulate")
    parser.add_option('--samplingList', '--sampleList', type="string", default = None,dest="samplingList", help="file containing the list of BX to sample")
    parser.add_option('--extra', '--extraText', type="string", default = None,dest="extraText", help="extra text ot append to directory name (ex: version number, other notes to track)")
    parser.add_option('--CSVNoSpace',dest='replaceCSVDelim', action='store_false', default=True, help='keep the output csv files as comma delimited with no trailing space')
    (opt, args) = parser.parse_args()

    outputDir = sampleData(directoryName = opt.inputDir, outputName = opt.outputName, nBX = opt.nBX, samplingList = opt.samplingList, extraName=opt.extraText)

    alterCSVFiles(outputDir)


    linkFiles = [["Formatter_Buffer_Input_Type_BC.csv",              "Algorithm_Input_Type_BC.csv"],                  
                 ["Formatter_Buffer_Input_Type_RPT.csv",             "Algorithm_Input_Type_RPT.csv"],                  
                 ["Formatter_Buffer_Input_Type_STC.csv",             "Algorithm_Input_Type_STC.csv"],                  
                 ["Formatter_Buffer_Input_Type_TS.csv",              "Algorithm_Input_Type_TS.csv"],                  
                 ["Formatter_Buffer_Input_ChargeQ.csv",              "Algorithm_Output_ChargeQ.csv"],              
                 ["Formatter_Buffer_Input_AddrMap.csv",              "Algorithm_Output_AddrMap.csv"],              
                 ["Formatter_Buffer_Input_NTCQ.csv",                 "Algorithm_Output_NTCQ.csv"],                 
                 ["Formatter_Buffer_Input_Mod_Sum.csv",              "Algorithm_Output_Mod_Sum.csv"],              
                 ["Formatter_Buffer_Input_Sum.csv",                  "Algorithm_Output_Sum.csv"],                  
                 ["Formatter_Buffer_Inputr_STC_2x2_Sum.csv",         "Algorithm_Output_STC_2x2_Sum.csv"],         
                 ["Formatter_Buffer_Input_Mod_Sum_stc.csv",          "Algorithm_Output_Mod_Sum_stc.csv"],          
                 ["Formatter_Buffer_Input_BC_Charge.csv",            "Algorithm_Output_BC_Charge.csv"],            
                 ["Formatter_Buffer_Input_BC_TC_map.csv",            "Algorithm_Output_BC_TC_map.csv"],            
                 ["Formatter_Buffer_Input_RepeaterQ.csv",            "Algorithm_Output_RepeaterQ.csv"]]            

    for f1, f2 in linkFiles:
        if not os.path.exists(f'{outputDir}/{f1}'):
            os.symlink(f'{f2}',f'{outputDir}/{f1}')
        
