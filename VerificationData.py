import pandas as pd
import shutil
import argparse
import os

def addSpaceToCSV(outputDir, fileList):

    for fName in fileList:
        with open(f'{outputDir}/{fName}', "r") as sourceFile:
            lines = sourceFile.readlines()
        with open(f'{outputDir}/{fName}', "w") as outputFile:
            for line in lines:
                outputFile.write(line.replace(',',', '))


def AlgoTestBench(inputDir, outputDir):
    NewFiles = []

    #Copy CALQ, HighDensity, and THRESHV
    shutil.copy(f'{inputDir}/CALQ.csv',f'{outputDir}/Algorithm_Input_CalQ.csv')
    NewFiles.append('Algorithm_Input_CalQ.csv')
    shutil.copy(f'{inputDir}/HighDensity.csv', f'{outputDir}/Algorithm_Input_HighDensity.csv')
    NewFiles.append('Algorithm_Input_HighDensity.csv')
    shutil.copy(f'{inputDir}/THRESHV.csv', f'{outputDir}/Algorithm_Input_Threshold.csv')
    NewFiles.append('Algorithm_Input_Threshold.csv')
    shutil.copy(f'{inputDir}/DropLSB.csv', f'{outputDir}/Algorithm_Input_DropLSB.csv')
    NewFiles.append('Algorithm_Input_DropLSB.csv')

    #Algorith input and output Header are BX_CNT
    df = pd.read_csv(f'{inputDir}/BX_CNT.csv',index_col=['Orbit','BX'])
    df.columns = ['HEADER_IN']
    df.to_csv(f'{outputDir}/Algorithm_Input_Header.csv')
    NewFiles.append('Algorithm_Input_Header.csv')
    df.columns = ['HEADER_OUT']
    df.to_csv(f'{outputDir}/Algorithm_Output_Header.csv')
    NewFiles.append('Algorithm_Output_Header.csv')

    #Make Algo Type csv's
    pd.DataFrame(0,columns=['TYPE'],index=df.index).to_csv(f'{outputDir}/Algorithm_Input_Type_TS.csv')
    NewFiles.append('Algorithm_Input_Type_TS.csv')
    pd.DataFrame(1,columns=['TYPE'],index=df.index).to_csv(f'{outputDir}/Algorithm_Input_Type_STC.csv')
    NewFiles.append('Algorithm_Input_Type_STC.csv')
    pd.DataFrame(2,columns=['TYPE'],index=df.index).to_csv(f'{outputDir}/Algorithm_Input_Type_BC.csv')
    NewFiles.append('Algorithm_Input_Type_BC.csv')
    pd.DataFrame(3,columns=['TYPE'],index=df.index).to_csv(f'{outputDir}/Algorithm_Input_Type_RPT.csv')
    NewFiles.append('Algorithm_Input_Type_RPT.csv')

    #load and output threshold sum data
    df = pd.read_csv(f'{inputDir}/Threshold_Sum.csv',index_col=['Orbit','BX'])
    df[[f'CHARGEQ_{i}' for i in range(48)]].to_csv(f'{outputDir}/Algorithm_Output_ChargeQ.csv')
    NewFiles.append('Algorithm_Output_ChargeQ.csv')
    df[[f'ADDRMAP_{i}' for i in range(48)]].to_csv(f'{outputDir}/Algorithm_Output_AddrMap.csv')
    NewFiles.append('Algorithm_Output_AddrMap.csv')
    df[['SUM']].to_csv(f'{outputDir}/Algorithm_Output_Sum.csv')
    NewFiles.append('Algorithm_Output_Sum.csv')
    df[['SUM_NOT_TRANSMITTED']].to_csv(f'{outputDir}/Algorithm_Output_SumNotTransmitted.csv')
    NewFiles.append('Algorithm_Output_SumNotTransmitted.csv')

    #load and output STC data
    df = pd.read_csv(f'{inputDir}/SuperTriggerCell.csv',index_col=['Orbit','BX'])
    df[[f'XTC4_9_SUM_{i}' for i in range(12)]].to_csv(f'{outputDir}/Algorithm_Output_XTC4_9_Sum.csv')
    NewFiles.append('Algorithm_Output_XTC4_9_Sum.csv')
    df[[f'XTC16_9_SUM_{i}' for i in range(3)]].to_csv(f'{outputDir}/Algorithm_Output_XTC16_9_Sum.csv')
    NewFiles.append('Algorithm_Output_XTC16_9_Sum.csv')
    df[[f'XTC4_7_SUM_{i}' for i in range(12)]].to_csv(f'{outputDir}/Algorithm_Output_XTC4_7_Sum.csv')
    NewFiles.append('Algorithm_Output_XTC4_7_Sum.csv')
    df[[f'MAX4_ADDR_{i}' for i in range(12)]].to_csv(f'{outputDir}/Algorithm_Output_MAX4_Addr.csv')
    NewFiles.append('Algorithm_Output_MAX4_Addr.csv')
    df[[f'MAX16_ADDR_{i}' for i in range(3)]].to_csv(f'{outputDir}/Algorithm_Output_MAX16_Addr.csv')
    NewFiles.append('Algorithm_Output_MAX16_Addr.csv')

    #BestChoice
    df = pd.read_csv(f'{inputDir}/BestChoice.csv',index_col=['Orbit','BX'])
    df[[f'BC_CHARGE_{i}' for i in range(48)]].to_csv(f'{outputDir}/Algorithm_Output_BC_Charge.csv')
    NewFiles.append('Algorithm_Output_BC_Charge.csv')
    df[[f'BC_TC_MAP_{i}' for i in range(48)]].to_csv(f'{outputDir}/Algorithm_Output_BC_TC_map.csv')
    NewFiles.append('Algorithm_Output_BC_TC_map.csv')

    #Repeater just needs to be copied
    shutil.copy(f'{inputDir}/BestChoice.csv', f'{outputDir}/Algorithm_Output_RepeaterQ.csv')
    NewFiles.append('Algorithm_Output_RepeaterQ.csv')

    #update file contents to leave space after comma in csv
    addSpaceToCSV(outputDir, NewFiles)


def FormatBuffer(inputDir, outputDir):
    NewFiles = []
    #copy registers 
    shutil.copy(f'{inputDir}/TxSyncWord.csv', f'{outputDir}/Formatter_Buffer_Input_Tx_Sync_Word.csv')
    NewFiles.append('Formatter_Buffer_Input_Tx_Sync_Word.csv')

    shutil.copy(f'{inputDir}/EPORTTX_NUMEN.csv', f'{outputDir}/Formatter_Buffer_Input_EPortTx_NumEn.csv')
    NewFiles.append('Formatter_Buffer_Input_EPortTx_NumEn.csv')

    shutil.copy(f'{inputDir}/Buffer_Threshold_T1.csv', f'{outputDir}/Formatter_Buffer_Input_Buffer_Threshold_T1.csv')
    NewFiles.append('Formatter_Buffer_Input_Buffer_Threshold_T1.csv')

    shutil.copy(f'{inputDir}/Buffer_Threshold_T2.csv', f'{outputDir}/Formatter_Buffer_Input_Buffer_Threshold_T2.csv')
    NewFiles.append('Formatter_Buffer_Input_Buffer_Threshold_T2.csv')

    shutil.copy(f'{inputDir}/Buffer_Threshold_T1.csv', f'{outputDir}/Formatter_Buffer_Input_Buffer_Threshold_T3.csv')
    NewFiles.append('Formatter_Buffer_Input_Buffer_Threshold_T3.csv')

    #header file and algo type
    df = pd.read_csv(f'{inputDir}/BX_CNT.csv',index_col=['Orbit','BX'])
    df.columns = ['HEADER']
    df.to_csv(f'{outputDir}/Formatter_Buffer_Input_Header.csv')
    NewFiles.append('Formatter_Buffer_Input_Header.csv')

    df = pd.read_csv(f'{inputDir}/Buffer_TS.csv',index_col=['Orbit','BX'])
    df[[f'TX_DATA_{i}' for i in range(14)]].to_csv(f'{outputDir}/Formatter_Buffer_Output_ePortTx_DataIn_TS.csv')
    NewFiles.append('Formatter_Buffer_Output_ePortTx_DataIn_TS.csv')

    df = pd.read_csv(f'{inputDir}/Buffer_STC.csv',index_col=['Orbit','BX'])
    df[[f'TX_DATA_{i}' for i in range(14)]].to_csv(f'{outputDir}/Formatter_Buffer_Output_ePortTx_DataIn_STC.csv')
    NewFiles.append('Formatter_Buffer_Output_ePortTx_DataIn_STC.csv')

    df = pd.read_csv(f'{inputDir}/Buffer_BC.csv',index_col=['Orbit','BX'])
    df[[f'TX_DATA_{i}' for i in range(14)]].to_csv(f'{outputDir}/Formatter_Buffer_Output_ePortTx_DataIn_BC.csv')
    NewFiles.append('Formatter_Buffer_Output_ePortTx_DataIn_BC.csv')

    df = pd.read_csv(f'{inputDir}/Buffer_RPT.csv',index_col=['Orbit','BX'])
    df[[f'TX_DATA_{i}' for i in range(14)]].to_csv(f'{outputDir}/Formatter_Buffer_Output_ePortTx_DataIn_RPT.csv')
    NewFiles.append('Formatter_Buffer_Output_ePortTx_DataIn_RPT.csv')

    pd.DataFrame(0,columns=['OVFLW'],index=df.index).to_csv(f'{outputDir}/Formatter_Buffer_Output_error.csv')
    NewFiles.append('Formatter_Buffer_Output_error.csv')

    #update file contents to leave space after comma in csv
    addSpaceToCSV(outputDir, NewFiles)

    #link algorithm outputs to formatter inputs
    linkFiles = [['Algorithm_Output_ChargeQ.csv', 'Formatter_Buffer_Input_ChargeQ.csv'],
                 ['Algorithm_Output_AddrMap.csv', 'Formatter_Buffer_Input_AddrMap.csv'],
                 ['Algorithm_Output_Sum.csv', 'Formatter_Buffer_Input_Sum.csv'],
                 ['Algorithm_Output_SumNotTransmitted.csv', 'Formatter_Buffer_Input_SumNotTransmitted.csv'],
                 ['Algorithm_Output_XTC4_9_Sum.csv', 'Formatter_Buffer_Input_XTC4_9_Sum.csv'],
                 ['Algorithm_Output_XTC16_9_Sum.csv', 'Formatter_Buffer_Input_XTC16_9_Sum.csv'],
                 ['Algorithm_Output_XTC4_7_Sum.csv', 'Formatter_Buffer_Input_XTC4_7_Sum.csv'],
                 ['Algorithm_Output_MAX4_Addr.csv', 'Formatter_Buffer_Input_MAX4_Addr.csv'],
                 ['Algorithm_Output_MAX16_Addr.csv', 'Formatter_Buffer_Input_MAX16_Addr.csv'],
                 ['Algorithm_Output_BC_Charge.csv', 'Formatter_Buffer_Input_BC_Charge.csv'],
                 ['Algorithm_Output_BC_TC_map.csv', 'Formatter_Buffer_Input_BC_TC_map.csv'],
                 ['Algorithm_Output_RepeaterQ.csv', 'Formatter_Buffer_Input_RepeaterQ.csv'],
                 ['Algorithm_Output_Header.csv', 'Formatter_Buffer_Input_Header.csv'],
                 ['Algorithm_Input_Type_TS.csv', 'Formatter_Buffer_Input_Type_TS.csv'],
                 ['Algorithm_Input_Type_STC.csv', 'Formatter_Buffer_Input_Type_STC.csv'],
                 ['Algorithm_Input_Type_BC.csv', 'Formatter_Buffer_Input_Type_BC.csv'],
                 ['Algorithm_Input_Type_RPT.csv', 'Formatter_Buffer_Input_Type_RPT.csv'],
             ]

    for fSrc, fDest in linkFiles:
        if not os.path.exists(f'{outputDir}/{fDest}'):
            os.symlink(f'{fSrc}',f'{outputDir}/{fDest}')

def main(inputDir, outputDir):
    TestBenchList = []

    if not os.path.exists(outputDir):
        os.makedirs(outputDir)

    shutil.copy(f'{inputDir}/metaData.py',f'{outputDir}/metaData.py')
    AlgoTestBench(inputDir, outputDir)
    FormatBuffer(inputDir, outputDir)

if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-i','--input', dest='inputDir', required=True, help='input directory name')
    parser.add_argument('-o','--output', dest='outputDir', required=True, help='outputDirectory, if different than directory of input file')

    args = parser.parse_args()
    
    main(**vars(args))
