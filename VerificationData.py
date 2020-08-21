import pandas as pd
import shutil
import argparse
import os

saveIndex=False

if saveIndex:
    index_col=['Orbit','BX']
else:
    index_col=None

def addSpaceToCSV(outputDir, fileList):

    for fName in fileList:
        with open(f'{outputDir}/{fName}', "r") as sourceFile:
            lines = sourceFile.readlines()
        with open(f'{outputDir}/{fName}', "w") as outputFile:
            for line in lines:
                outputFile.write(line.replace(',',', '))


def EPortRXTestBench(inputDir, outputDir):
    NewFiles = []

    #link algorithm outputs to formatter inputs
    linkFiles = [['MuxFixCalib_Input_ePortRxDataGroup.csv', 'EPortRX_Output_ePortRxDataGroup.csv'],
    ]

    for fSrc, fDest in linkFiles:
        if not os.path.exists(f'{outputDir}/{fDest}'):
            os.symlink(f'{fSrc}',f'{outputDir}/{fDest}')
    
    shutil.copy(f'{inputDir}/ORBSYN_CNT_LOAD_VAL.csv',f'{outputDir}/EPortRX_Input_ORBSYN_CNT_LOAD_VAL.csv')
    NewFiles.append('EPortRX_Input_ORBSYN_CNT_LOAD_VAL.csv')
    shutil.copy(f'{inputDir}/EPORTRX_data.csv',f'{outputDir}/EPortRX_Input_EPORTRX_data.csv')
    NewFiles.append('EPortRX_Input_EPORTRX_data.csv')
    
    #update file contents to leave space after comma in csv
    addSpaceToCSV(outputDir, NewFiles)

def MuxFixCalibTestBench(inputDir, outputDir):
    NewFiles = []

    #link algorithm outputs to formatter inputs
    linkFiles = [['Algorithm_Input_CalQ.csv', 'MuxFixCalib_Output_CALQ.csv'],    
    ]

    for fSrc, fDest in linkFiles:
        if not os.path.exists(f'{outputDir}/{fDest}'):
            os.symlink(f'{fSrc}',f'{outputDir}/{fDest}')
    
    #copy registers 
    shutil.copy(f'{inputDir}/HighDensity.csv', f'{outputDir}/MuxFixCalib_Input_HighDensity.csv')
    NewFiles.append('MuxFixCalib_Input_HighDensity.csv')
    shutil.copy(f'{inputDir}/Mux_Select.csv', f'{outputDir}/MuxFixCalib_Input_Mux_Select.csv')
    NewFiles.append('MuxFixCalib_Input_Mux_Select.csv')
    shutil.copy(f'{inputDir}/CALVALUE.csv', f'{outputDir}/MuxFixCalib_Input_CALVALUE.csv')
    NewFiles.append('MuxFixCalib_Input_CALVALUE.csv')

    #inputs and internal values
    shutil.copy(f'{inputDir}/ePortRxDataGroup.csv', f'{outputDir}/MuxFixCalib_Input_ePortRxDataGroup.csv')
    NewFiles.append('MuxFixCalib_Input_ePortRxDataGroup.csv')
    shutil.copy(f'{inputDir}/Mux_in.csv', f'{outputDir}/MuxFixCalib_Input_Mux_in.csv')
    NewFiles.append('MuxFixCalib_Input_Mux_in.csv')
    shutil.copy(f'{inputDir}/Mux_out.csv', f'{outputDir}/MuxFixCalib_Internal_Mux_out.csv')
    NewFiles.append('MuxFixCalib_Internal_Mux_out.csv')
    shutil.copy(f'{inputDir}/F2F.csv', f'{outputDir}/MuxFixCalib_Internal_F2F.csv')
    NewFiles.append('MuxFixCalib_Internal_F2F.csv')

    #update file contents to leave space after comma in csv
    addSpaceToCSV(outputDir, NewFiles)


def AlgoTestBench(inputDir, outputDir):
    NewFiles = []

    #Copy CALQ, HighDensity, and THRESHV
    shutil.copy(f'{inputDir}/CALQ.csv',f'{outputDir}/Algorithm_Input_CalQ.csv')
    NewFiles.append('Algorithm_Input_CalQ.csv')
    # shutil.copy(f'{inputDir}/HighDensity.csv', f'{outputDir}/Algorithm_Input_HighDensity.csv')
    # NewFiles.append('Algorithm_Input_HighDensity.csv')
    shutil.copy(f'{inputDir}/THRESHV.csv', f'{outputDir}/Algorithm_Input_Threshold.csv')
    NewFiles.append('Algorithm_Input_Threshold.csv')
    shutil.copy(f'{inputDir}/DropLSB.csv', f'{outputDir}/Algorithm_Input_DropLSB.csv')
    NewFiles.append('Algorithm_Input_DropLSB.csv')

    #Algorith input and output Header are BX_CNT
    df = pd.read_csv(f'{inputDir}/BX_CNT.csv',index_col=index_col)
    df.to_csv(f'{outputDir}/Algorithm_Input_Header.csv', index=saveIndex, header=['HEADER_IN'])
    NewFiles.append('Algorithm_Input_Header.csv')
    df.to_csv(f'{outputDir}/Algorithm_Output_Header.csv', index=saveIndex, header=['HEADER_OUT'])
    NewFiles.append('Algorithm_Output_Header.csv')

    #Make Algo Type csv's
    pd.DataFrame(0,columns=['TYPE'],index=df.index).to_csv(f'{outputDir}/Algorithm_Input_Type_TS.csv', index=saveIndex)
    NewFiles.append('Algorithm_Input_Type_TS.csv')
    pd.DataFrame(1,columns=['TYPE'],index=df.index).to_csv(f'{outputDir}/Algorithm_Input_Type_STC.csv', index=saveIndex)
    NewFiles.append('Algorithm_Input_Type_STC.csv')
    pd.DataFrame(2,columns=['TYPE'],index=df.index).to_csv(f'{outputDir}/Algorithm_Input_Type_BC.csv', index=saveIndex)
    NewFiles.append('Algorithm_Input_Type_BC.csv')
    pd.DataFrame(3,columns=['TYPE'],index=df.index).to_csv(f'{outputDir}/Algorithm_Input_Type_RPT.csv', index=saveIndex)
    NewFiles.append('Algorithm_Input_Type_RPT.csv')

    #load and output threshold sum data
    df = pd.read_csv(f'{inputDir}/Threshold_Sum.csv',index_col=index_col)
    df[[f'CHARGEQ_{i}' for i in range(48)]].to_csv(f'{outputDir}/Algorithm_Output_ChargeQ.csv', index=saveIndex)
    NewFiles.append('Algorithm_Output_ChargeQ.csv')
    df[[f'ADDRMAP_{i}' for i in range(48)]].to_csv(f'{outputDir}/Algorithm_Output_AddrMap.csv', index=saveIndex)
    NewFiles.append('Algorithm_Output_AddrMap.csv')
    df[['SUM']].to_csv(f'{outputDir}/Algorithm_Output_Sum.csv', index=saveIndex)
    NewFiles.append('Algorithm_Output_Sum.csv')
    df[['SUM_NOT_TRANSMITTED']].to_csv(f'{outputDir}/Algorithm_Output_SumNotTransmitted.csv', index=saveIndex)
    NewFiles.append('Algorithm_Output_SumNotTransmitted.csv')

    #load and output STC data
    df = pd.read_csv(f'{inputDir}/SuperTriggerCell.csv',index_col=index_col)
    df[[f'XTC4_9_SUM_{i}' for i in range(12)]].to_csv(f'{outputDir}/Algorithm_Output_XTC4_9_Sum.csv', index=saveIndex)
    NewFiles.append('Algorithm_Output_XTC4_9_Sum.csv')
    df[[f'XTC16_9_SUM_{i}' for i in range(3)]].to_csv(f'{outputDir}/Algorithm_Output_XTC16_9_Sum.csv', index=saveIndex)
    NewFiles.append('Algorithm_Output_XTC16_9_Sum.csv')
    df[[f'XTC4_7_SUM_{i}' for i in range(12)]].to_csv(f'{outputDir}/Algorithm_Output_XTC4_7_Sum.csv', index=saveIndex)
    NewFiles.append('Algorithm_Output_XTC4_7_Sum.csv')
    df[[f'MAX4_ADDR_{i}' for i in range(12)]].to_csv(f'{outputDir}/Algorithm_Output_MAX4_Addr.csv', index=saveIndex)
    NewFiles.append('Algorithm_Output_MAX4_Addr.csv')
    df[[f'MAX16_ADDR_{i}' for i in range(3)]].to_csv(f'{outputDir}/Algorithm_Output_MAX16_Addr.csv', index=saveIndex)
    NewFiles.append('Algorithm_Output_MAX16_Addr.csv')

    #BestChoice
    df = pd.read_csv(f'{inputDir}/BestChoice.csv',index_col=index_col)
    df[[f'BC_CHARGE_{i}' for i in range(48)]].to_csv(f'{outputDir}/Algorithm_Output_BC_Charge.csv', index=saveIndex)
    NewFiles.append('Algorithm_Output_BC_Charge.csv')
    df[[f'BC_TC_MAP_{i}' for i in range(48)]].to_csv(f'{outputDir}/Algorithm_Output_BC_TC_map.csv', index=saveIndex)
    NewFiles.append('Algorithm_Output_BC_TC_map.csv')

    #Repeater just needs to be copied
    shutil.copy(f'{inputDir}/Repeater.csv', f'{outputDir}/Algorithm_Output_RepeaterQ.csv')
    NewFiles.append('Algorithm_Output_RepeaterQ.csv')

    #update file contents to leave space after comma in csv
    addSpaceToCSV(outputDir, NewFiles)


def FormatBuffer(inputDir, outputDir):
    NewFiles = []
    #copy registers 
    shutil.copy(f'{inputDir}/TxSyncWord.csv', f'{outputDir}/Formatter_Buffer_Input_TxSyncWord.csv')
    NewFiles.append('Formatter_Buffer_Input_TxSyncWord.csv')

    shutil.copy(f'{inputDir}/EPORTTX_NUMEN.csv', f'{outputDir}/Formatter_Buffer_Input_EPortTx_NumEn.csv')
    NewFiles.append('Formatter_Buffer_Input_EPortTx_NumEn.csv')

    shutil.copy(f'{inputDir}/STC_TYPE.csv', f'{outputDir}/Formatter_Buffer_Input_STC_Type.csv')
    NewFiles.append('Formatter_Buffer_Input_STC_Type.csv')

    shutil.copy(f'{inputDir}/Use_Sum.csv', f'{outputDir}/Formatter_Buffer_Input_Use_Sum.csv')
    NewFiles.append('Formatter_Buffer_Input_Use_Sum.csv')

    shutil.copy(f'{inputDir}/Buffer_Threshold_T1.csv', f'{outputDir}/Formatter_Buffer_Input_Buffer_Threshold_T1.csv')
    NewFiles.append('Formatter_Buffer_Input_Buffer_Threshold_T1.csv')

    shutil.copy(f'{inputDir}/Buffer_Threshold_T2.csv', f'{outputDir}/Formatter_Buffer_Input_Buffer_Threshold_T2.csv')
    NewFiles.append('Formatter_Buffer_Input_Buffer_Threshold_T2.csv')

    shutil.copy(f'{inputDir}/Buffer_Threshold_T3.csv', f'{outputDir}/Formatter_Buffer_Input_Buffer_Threshold_T3.csv')
    NewFiles.append('Formatter_Buffer_Input_Buffer_Threshold_T3.csv')

    df = pd.read_csv(f'{inputDir}/LinkResetEconT.csv')
    df.to_csv(f'{outputDir}/Formatter_Buffer_Input_link_reset_econt.csv',index=saveIndex,header=['LINK_RESET'])
    NewFiles.append('Formatter_Buffer_Input_link_reset_econt.csv')

    df = pd.read_csv(f'{inputDir}/BX_CNT.csv',index_col=index_col)
    df.to_csv(f'{outputDir}/Formatter_Buffer_Input_Bx_Cnt_In.csv', index=saveIndex, header=['BX_CNT_IN'])
    NewFiles.append('Formatter_Buffer_Input_Bx_Cnt_In.csv')

    #header file and algo type
    df = pd.read_csv(f'{inputDir}/BX_CNT.csv',index_col=index_col)
    df.columns = ['HEADER']
    df.to_csv(f'{outputDir}/Formatter_Buffer_Input_Header.csv', index=saveIndex)
    NewFiles.append('Formatter_Buffer_Input_Header.csv')

    for ALGO in ['TS','STC','BC','RPT']:
        df = pd.read_csv(f'{inputDir}/Buffer_{ALGO}.csv',index_col=index_col)
        df[[f'TX_DATA_{i}' for i in range(13)]].to_csv(f'{outputDir}/Formatter_Buffer_Output_ePortTx_DataIn_{ALGO}.csv', index=saveIndex)
        NewFiles.append(f'Formatter_Buffer_Output_ePortTx_DataIn_{ALGO}.csv')

        pd.DataFrame(0,columns=['TX_ERR'],index=df.index).to_csv(f'{outputDir}/Formatter_Buffer_Output_ePortTx_err_{ALGO}.csv', index=saveIndex)
        NewFiles.append(f'Formatter_Buffer_Output_ePortTx_err_{ALGO}.csv')

        df[[f'TX_DATA_{i}' for i in range(12,-1,-1)]].to_csv(f'{outputDir}/Formatter_Buffer_Output_buffer_ePortTx_DataIn_{ALGO}.csv', header=[f'BUF_OUT_TX_DATA_{i}' for i in range(12,-1,-1)],index=saveIndex)
        NewFiles.append(f'Formatter_Buffer_Output_buffer_ePortTx_DataIn_{ALGO}.csv')

        pd.DataFrame(0,columns=['BUF_OUT_ERR'],index=df.index).to_csv(f'{outputDir}/Formatter_Buffer_Output_buffer_err_{ALGO}.csv', index=saveIndex)
        NewFiles.append(f'Formatter_Buffer_Output_buffer_err_{ALGO}.csv')

        #Make Algo Type csv's
        pd.DataFrame(0,columns=['ALGORITHM_TYPE'],index=df.index).to_csv(f'{outputDir}/Formatter_Buffer_Input_Algorithm_Type_{ALGO}.csv', index=saveIndex)
        NewFiles.append(f'Formatter_Buffer_Input_Algorithm_Type_{ALGO}.csv')


    # df = pd.read_csv(f'{inputDir}/Buffer_STC.csv',index_col=index_col)
    # df[[f'TX_DATA_{i}' for i in range(14)]].to_csv(f'{outputDir}/Formatter_Buffer_Output_ePortTx_DataIn_STC.csv', index=saveIndex)
    # NewFiles.append('Formatter_Buffer_Output_ePortTx_DataIn_STC.csv')

    # df = pd.read_csv(f'{inputDir}/Buffer_BC.csv',index_col=index_col)
    # df[[f'TX_DATA_{i}' for i in range(14)]].to_csv(f'{outputDir}/Formatter_Buffer_Output_ePortTx_DataIn_BC.csv', index=saveIndex)
    # NewFiles.append('Formatter_Buffer_Output_ePortTx_DataIn_BC.csv')

    # df = pd.read_csv(f'{inputDir}/Buffer_RPT.csv',index_col=index_col)
    # df[[f'TX_DATA_{i}' for i in range(14)]].to_csv(f'{outputDir}/Formatter_Buffer_Output_ePortTx_DataIn_RPT.csv', index=saveIndex)
    # NewFiles.append('Formatter_Buffer_Output_ePortTx_DataIn_RPT.csv')

    # pd.DataFrame(0,columns=['TX_ERR'],index=df.index).to_csv(f'{outputDir}/Formatter_Buffer_Output_ePortTx_err_TS.csv', index=saveIndex)
    # NewFiles.append('Formatter_Buffer_Output_ePortTx_err_TS.csv')
    # pd.DataFrame(0,columns=['TX_ERR'],index=df.index).to_csv(f'{outputDir}/Formatter_Buffer_Output_ePortTx_err_TS.csv', index=saveIndex)
    # NewFiles.append('Formatter_Buffer_Output_ePortTx_err_TS.csv')
    # pd.DataFrame(0,columns=['TX_ERR'],index=df.index).to_csv(f'{outputDir}/Formatter_Buffer_Output_ePortTx_err_TS.csv', index=saveIndex)
    # NewFiles.append('Formatter_Buffer_Output_ePortTx_err_TS.csv')

    # pd.DataFrame(1,columns=['ALGORITHM_TYPE'],index=df.index).to_csv(f'{outputDir}/Formatter_Buffer_Input_Algorithm_Type_STC.csv', index=saveIndex)
    # NewFiles.append('Formatter_Buffer_Input_Algorithm_Type_STC.csv')
    # pd.DataFrame(2,columns=['ALGORITHM_TYPE'],index=df.index).to_csv(f'{outputDir}/Formatter_Buffer_Input_Algorithm_Type_BC.csv', index=saveIndex)
    # NewFiles.append('Formatter_Buffer_Input_Algorithm_Type_BC.csv')
    # pd.DataFrame(3,columns=['ALGORITHM_TYPE'],index=df.index).to_csv(f'{outputDir}/Formatter_Buffer_Input_Algorithm_Type_RPT.csv', index=saveIndex)
    # NewFiles.append('Formatter_Buffer_Input_Algorithm_Type_RPT.csv')

#    for ALGO in ['TS','BC','STC','RPT']:
        df = pd.read_csv(f'{inputDir}/Format_{ALGO}.csv',index_col=index_col)

        df[[f'FRAMEQ_{i}' for i in range(25,-1,-1)]].to_csv(f'{outputDir}/Formatter_Buffer_Input_FrameQ_{ALGO}.csv',index=saveIndex,header=[f'BUF_INP_FRMQ_{i}' for i in range(25,-1,-1)])
        NewFiles.append(f'Formatter_Buffer_Input_FrameQ_{ALGO}.csv')

        df[['FRAMEQ_NUMW']].to_csv(f'{outputDir}/Formatter_Buffer_Input_FrameQ_NumW_{ALGO}.csv',index=saveIndex,header=['BUF_INP_FRMQ_NUMW'])
        NewFiles.append(f'Formatter_Buffer_Input_FrameQ_NumW_{ALGO}.csv')

        df[['FRAMEQ_Truncated_1']*25 + ['FRAMEQ_Truncated_0']].to_csv(f'{outputDir}/Formatter_Buffer_Input_FrameQTruncated_{ALGO}.csv',index=saveIndex,header=[f'BUF_INP_FRMQT_{i}' for i in range(25,-1,-1)])
        NewFiles.append(f'Formatter_Buffer_Input_FrameQTruncated_{ALGO}.csv')

        df[[f'FRAMEQ_{i}' for i in range(26)]].to_csv(f'{outputDir}/Formatter_Buffer_Output_FrameQ_{ALGO}.csv',index=saveIndex,header=[f'FMT_OUT_FRMQ_{i}' for i in range(26)])
        NewFiles.append(f'Formatter_Buffer_Output_FrameQ_{ALGO}.csv')

        df[['FRAMEQ_NUMW']].to_csv(f'{outputDir}/Formatter_Buffer_Output_FrameQ_NumW_{ALGO}.csv',index=saveIndex,header=['FMT_OUT_FRMQ_NUMW'])
        NewFiles.append(f'Formatter_Buffer_Output_FrameQ_NumW_{ALGO}.csv')

        df[['FRAMEQ_Truncated_0','FRAMEQ_Truncated_1']].to_csv(f'{outputDir}/Formatter_Buffer_Output_FrameQTruncated_{ALGO}.csv',index=saveIndex,header=['FMT_OUT_FRMQT_0','FMT_OUT_FRMQT_1'])
        NewFiles.append(f'Formatter_Buffer_Output_FrameQTruncated_{ALGO}.csv')


    #create dummy files for the auto encoder
    dfAE = pd.DataFrame(dict({f'AE_BYTE{i}':0 for i in range(20)},**{f'MAE_BYTE{i}':0 for i in range(18)}), index=df.index)
    dfAE[[f'AE_BYTE{i}' for i in range(20)]].to_csv(f'{outputDir}/Formatter_Buffer_Input_outEncoder.csv',index=saveIndex)
    NewFiles.append('Formatter_Buffer_Input_outEncoder.csv')
    dfAE[[f'MAE_BYTE{i}' for i in range(18)]].to_csv(f'{outputDir}/Formatter_Buffer_Input_mask_auto_encoder.csv',index=saveIndex)
    NewFiles.append('Formatter_Buffer_Input_mask_auto_encoder.csv')


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
             ]

    for fSrc, fDest in linkFiles:
        if not os.path.exists(f'{outputDir}/{fDest}'):
            os.symlink(f'{fSrc}',f'{outputDir}/{fDest}')

def makeVerificationData(inputDir, outputDir):

    if not os.path.exists(outputDir):
        os.makedirs(outputDir)

    shutil.copy(f'{inputDir}/metaData.py',f'{outputDir}/metaData.py')

    AlgoTestBench(inputDir, outputDir)
    FormatBuffer(inputDir, outputDir)
    MuxFixCalibTestBench(inputDir, outputDir)
    EPortRXTestBench(inputDir, outputDir)

if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-i','--input', dest='inputDir', required=True, help='input directory name')
    parser.add_argument('-o','--output', dest='outputDir', required=True, help='outputDirectory, if different than directory of input file')

    args = parser.parse_args()
    
    makeVerificationData(**vars(args))
