import pandas as pd
import numpy as np
from Utils.encode import encode

def splitToWords(row, N=16,totalWords=28):
    fullData = row['FullDataString']
    
    words = [int(fullData[i*N:(i+1)*N],2) for i in range(int(len(fullData)/N))]
        
    if len(words)<totalWords:
        words += [row['IdleWord']]*(totalWords-len(words))

    return words

def formatThresholdOutput(row,TxSynchWord=0, Use_Sum=False, debug=False):

    SUM_FULL =row['SUM']
    SUM_NOT_TRANSMITTED =row['SUM_NOT_TRANSMITTED']
    CHARGEQ = row[[f'CHARGEQ_{i}' for i in range(48)]].values
    CHARGEQ=CHARGEQ[CHARGEQ>0]      ## remove zeros

    ADD_MAP  = row[[f'ADDRMAP_{i}' for i in range(48)]]
            
    NTCQ=sum(ADD_MAP)

    bx_cnt = row['BX_CNT']
    header =  format(bx_cnt, '#0%ib'%(7))[2:]
    
    dataType = ''
    if NTCQ==0: 
        dataType='000'
    elif NTCQ<8:
        dataType='001'
    else:
        dataType='010'

    if Use_Sum:
        modSumData = format(SUM_FULL, '#010b')[2:]
    else:
        modSumData = format(SUM_NOT_TRANSMITTED, '#010b')[2:]

    extraBit=''
    if NTCQ==0:
        nChannelData=''
        AddressMapData=''
        ChargeData=''
    elif NTCQ<8:
        nChannelData=format(NTCQ, '#0%ib'%(3+2))[2:]
        # print (ADD_MAP)        
        # bitmap = np.array([int(x) for x in format(ADD_MAP, '#0%ib'%(48+2))[2:]][::-1])
        channelNumbers = np.arange(48)[ADD_MAP==1]
        channelNumbersBin = [format(x,'#0%ib'%(6+2))[2:] for x in channelNumbers]
        AddressMapData = ''
        for x in channelNumbersBin: AddressMapData += x
        
        ChargeData = ''
        for x in CHARGEQ:
            ChargeData += format(x, '#0%ib'%(9))[2:]
    else:
        nChannelData=''
        AddressMapData=''.join([str(i) for i in ADD_MAP])
        ChargeData = ''
        for x in CHARGEQ:
            ChargeData += format(x, '#0%ib'%(9))[2:]

    formattedData = header + dataType + modSumData + extraBit + nChannelData + AddressMapData + ChargeData
    if len(formattedData)%16==0:
        nPadBits=0
        paddedData = formattedData
    else:
        nPadBits = 16 - (len(formattedData)%16)
        paddedData = formattedData + '0'*nPadBits

    if not debug:
        return paddedData
    else:
        return [header, dataType , modSumData, extraBit ,nChannelData , len(AddressMapData) , len(ChargeData)]

def formatThresholdTruncatedOutput(row):

    header =  format(row['BX_CNT'], '#0%ib'%(7))[2:]

    dataType_Truncated = '110'

    SUM_FULL =row['SUM']
    modSumFull = format(SUM_FULL, '#0%ib'%(10))[2:]

    formattedData_Truncated = header + dataType_Truncated + modSumFull

    return int(formattedData_Truncated,2)


def Format_Threshold_Sum(df_Threshold_Sum, df_BX_CNT, TxSyncWord, Use_Sum):

    df_in = pd.merge(df_Threshold_Sum, df_BX_CNT, left_index=True, right_index=True)

    df_Format = pd.DataFrame(df_in.apply(formatThresholdOutput, Use_Sum=Use_Sum, axis=1).values,columns=['FullDataString'],index=df_in.index)

    df_Format['FRAMEQ_NUMW'] = (df_Format['FullDataString'] .str.len()/16).astype(int)

    df_Format['IdleWord'] = (df_BX_CNT.BX_CNT.values<<11) + TxSyncWord

    frameQ_headers = [f'FRAMEQ_{i}' for i in range(28)]

    df_Format[frameQ_headers]= pd.DataFrame(df_Format.apply(splitToWords,axis=1).tolist(),columns=frameQ_headers,index=df_Format.index)

    df_Format['FRAMEQ_Truncated'] = df_in.apply(formatThresholdTruncatedOutput,axis=1)

    return df_Format[frameQ_headers+['FRAMEQ_NUMW','FRAMEQ_Truncated','IdleWord']]


def formatBestChoiceOutput(row, nTC = 1, Use_Sum=False, debug=False):

    nExp = 4
    nMant = 3
    roundBits = False
    nDropBit = 0 

    ADD_MAP = list(row[[f'BC_TC_MAP_{i}' for i in range(48)]])
    CHARGEQ = list(row[[f'BC_CHARGE_{i}' for i in range(48)]])

    SUM = encode(sum(CHARGEQ[:]),0,5,3,asInt=True)
    SUM_NOT_TRANSMITTED = encode(sum(CHARGEQ[nTC:]),0,5,3,asInt=True)

    sel_q = CHARGEQ[:nTC]
    sel_add = ADD_MAP[:nTC]

    BITMAP = np.zeros(48, dtype=np.int32)
    CHARGEQ = np.zeros(48, dtype=np.int32)

    BITMAP[sel_add] = 1
    CHARGEQ[sel_add] = sel_q 

    CHARGEQ=CHARGEQ[CHARGEQ>0]      ## remove zeros

    bx_cnt = row['BX_CNT']
    header =  format(bx_cnt, '#0%ib'%(7))[2:]
    header = header[0] + header[2:]

    if Use_Sum:
        modSumData = format(SUM, '#010b')[2:]
    else:
        modSumData = format(SUM_NOT_TRANSMITTED, '#010b')[2:]

    if nTC<8:
        nChannelData=format(nTC, '#0%ib'%(3+2))[2:]
        
#        bitmap = np.array([int(x) for x in format(ADD_MAP, '#0%ib'%(48+2))[2:]][::-1])
        channelNumbers = np.arange(48)[BITMAP==1]
        channelNumbersBin = [format(x,'#0%ib'%(6+2))[2:] for x in channelNumbers]

        AddressMapData = ''
        for x in channelNumbersBin: AddressMapData += x

        ChargeData = ''
        for x in CHARGEQ:
            ChargeData += encode(x,nDropBit,nExp,nMant,roundBits)
        
    else:
        nChannelData=''
        AddressMapData=''.join([str(i) for i in BITMAP])
        ChargeData = ''
        for x in CHARGEQ:
            ChargeData += encode(x,nDropBit,nExp,nMant,roundBits)

    formattedData = header + modSumData + nChannelData + AddressMapData + ChargeData

    if len(formattedData)%16==0:
        nPadBits=0
        paddedData = formattedData
    else:
        nPadBits = 16 - (len(formattedData)%16)
        paddedData = formattedData + '0'*nPadBits

        
    if not debug:
        return paddedData
    else:
        return [header, modSumData , AddressMapData , ChargeData]

from Utils.linkAllocation import tcPerLink

def Format_BestChoice(df_BestChoice, EPORTTX_NUMEN, df_BX_CNT, TxSyncWord, Use_Sum):
    df_in = pd.merge(df_BestChoice, df_BX_CNT, left_index=True, right_index=True)

    df_Format = pd.DataFrame(df_in.apply(formatBestChoiceOutput, nTC=tcPerLink[EPORTTX_NUMEN], Use_Sum=Use_Sum, axis=1).values,columns=['FullDataString'],index=df_in.index)

    df_Format['FRAMEQ_NUMW'] = (df_Format['FullDataString'] .str.len()/16).astype(int)

    df_Format['IdleWord'] = (df_BX_CNT.BX_CNT.values<<11) + TxSyncWord

    frameQ_headers = [f'FRAMEQ_{i}' for i in range(28)]

    df_Format[frameQ_headers]= pd.DataFrame(df_Format.apply(splitToWords,axis=1).tolist(),columns=frameQ_headers,index=df_Format.index)

    df_Format['FRAMEQ_Truncated'] = 0

    return df_Format[frameQ_headers+['FRAMEQ_NUMW','FRAMEQ_Truncated','IdleWord']]




def formatSTC_4_9(row, nSTC, debug=False):
    colsSUM=[f'XTC4_9_SUM_{i}' for i in range(12)]
    colsIDX=[f'MAX4_ADDR_{i}' for i in range(12)]

    SumData = row[colsSUM].values
    IdxData = row[colsIDX].values

    nBitsAddr = 2 

    #only a 4 bit header for STC
    bx_cnt = row['BX_CNT']
    header =  format(bx_cnt, '#0%ib'%(7))[2:]
    header = header[0] + header[2:]
    
    STC_Data = ""
    for i in range(nSTC):
        idxBits = format(IdxData[i], '#0%ib'%(4))[2:]
        STC_Data += idxBits

    for i in range(nSTC):
        dataBits = format(SumData[i], '#0%ib'%(11))[2:]
        STC_Data += dataBits
        
    formattedData = header + STC_Data

    if len(formattedData)%32==0:
        nPadBits=0
        paddedData = formattedData
    else:
        nPadBits = 32 - (len(formattedData)%32)
        paddedData = formattedData + '0'*nPadBits

    return paddedData


def formatSTC_16_9(row, nSTC, debug=False):
    
    colsSUM=[f'XTC16_9_SUM_{i}' for i in range(12)]
    colsIDX=[f'MAX16_ADDR_{i}' for i in range(12)]

    SumData = row[colsSUM].values
    IdxData = row[colsIDX].values

    nBitsAddr = 4 

    #only a 4 bit header for STC
    bx_cnt = row['BX_CNT']
    header =  format(bx_cnt, '#0%ib'%(7))[2:]
    header = header[0] + header[2:]
    
    STC_Data = ""
    for i in range(nSTC):
        idxBits = format(IdxData[i], '#0%ib'%(6))[2:]
        STC_Data += idxBits

    for i in range(nSTC):
        dataBits = format(SumData[i], '#0%ib'%(11))[2:]
        STC_Data += dataBits
        
    formattedData = header + STC_Data

    if len(formattedData)%32==0:
        nPadBits=0
        paddedData = formattedData
    else:
        nPadBits = 32 - (len(formattedData)%32)
        paddedData = formattedData + '0'*nPadBits

    return paddedData

def formatSTC_4_7(row, nSTC, debug=False):
    
    colsSUM=[f'XTC4_7_SUM_{i}' for i in range(12)]
    colsIDX=[f'MAX4_ADDR_{i}' for i in range(12)]

    SumData = row[colsSUM].values
    IdxData = row[colsIDX].values

    nBitsAddr = 4 

    #only a 4 bit header for STC
    bx_cnt = row['BX_CNT']
    header =  format(bx_cnt, '#0%ib'%(7))[2:]
    header = header[0] + header[2:]
    
    STC_Data = ""
    for i in range(nSTC):
        idxBits = format(IdxData[i], '#0%ib'%(6))[2:]
        STC_Data += idxBits

    for i in range(nSTC):
        dataBits = format(SumData[i], '#0%ib'%(11))[2:]
        STC_Data += dataBits
        
    formattedData = header + STC_Data

    if len(formattedData)%32==0:
        nPadBits=0
        paddedData = formattedData
    else:
        nPadBits = 32 - (len(formattedData)%32)
        paddedData = formattedData + '0'*nPadBits

    return paddedData


def formatCTC_4_7(row, nSTC, debug=False):
    
    colsSUM=[f'XTC4_7_SUM_{i}' for i in range(12)]

    SumData = row[colsSUM].values

    nBitsAddr = 4 

    #only a 4 bit header for STC
    bx_cnt = row['BX_CNT']
    header =  format(bx_cnt, '#0%ib'%(7))[2:]
    header = header[0] + header[2:]
    
    STC_Data = ""
    for i in range(nSTC):
        dataBits = format(SumData[i], '#0%ib'%(11))[2:]
        STC_Data += dataBits
        
    formattedData = header + STC_Data

    if len(formattedData)%32==0:
        nPadBits=0
        paddedData = formattedData
    else:
        nPadBits = 32 - (len(formattedData)%32)
        paddedData = formattedData + '0'*nPadBits

    return paddedData



def Format_SuperTriggerCell(df_SuperTriggerCell, STC_TYPE, EPORTTX_NUMEN, df_BX_CNT, TxSyncWord):
    df_in = pd.merge(df_SuperTriggerCell, df_BX_CNT, left_index=True, right_index=True)

    if STC_TYPE==0: #STC4_9
        nSTC = 12 if EPORTTX_NUMEN>=5 else 11 if EPORTTX_NUMEN==4 else 8 if EPORTTX_NUMEN==3 else 5 if EPORTTX_NUMEN==2 else 2 
        df_Format = pd.DataFrame(df_in.apply(formatSTC_4_9, nSTC=nSTC, axis=1).values,columns=['FullDataString'],index=df_in.index)
    elif STC_TYPE==1: #STC16_9
        nSTC = 3 if EPORTTX_NUMEN>=2 else 2
        df_Format = pd.DataFrame(df_in.apply(formatSTC_16_9, nSTC=nSTC, axis=1).values,columns=['FullDataString'],index=df_in.index)
    elif STC_TYPE==2: #CTC4_7
        nSTC = 12 if EPORTTX_NUMEN>=3 else 8 if EPORTTX_NUMEN==2 else 4
        df_Format = pd.DataFrame(df_in.apply(formatSTC_4_7, nSTC=nSTC, axis=1).values,columns=['FullDataString'],index=df_in.index)
    elif STC_TYPE==3: #STC4_7
        nSTC = 3 if EPORTTX_NUMEN>=2 else 2
        df_Format = pd.DataFrame(df_in.apply(formatCTC_4_7, nSTC=nSTC, axis=1).values,columns=['FullDataString'],index=df_in.index)
        
    df_Format['FRAMEQ_NUMW'] = (df_Format['FullDataString'] .str.len()/16).astype(int)
        
    df_Format['IdleWord'] = (df_BX_CNT.BX_CNT.values<<11) + TxSyncWord

    frameQ_headers = [f'FRAMEQ_{i}' for i in range(28)]

    df_Format[frameQ_headers]= pd.DataFrame(df_Format.apply(splitToWords,axis=1).tolist(),columns=frameQ_headers,index=df_Format.index)

    df_Format['FRAMEQ_Truncated'] = 0

    return df_Format[frameQ_headers+['FRAMEQ_NUMW','FRAMEQ_Truncated','IdleWord']]


def formatRepeaterOutput(row,debug=False):
    cols = [f'RPT_{i}' for i in range(48)]
    CHARGEQ = row[cols].values
    ChargeData = ''
    for x in CHARGEQ:
        ChargeData += format(x, '#0%ib'%(9))[2:]

    bx_cnt = row['BX_CNT']
    header =  format(bx_cnt, '#0%ib'%(7))[2:]

    formattedData = header + ChargeData
    nPadBits = 16 - (len(formattedData)%16)
    paddedData = formattedData + '0'*nPadBits

    return paddedData

def Format_Repeater(df_Repeater, df_BX_CNT, TxSyncWord):
    df_in = pd.merge(df_Repeater, df_BX_CNT, left_index=True, right_index=True)

    df_Format = pd.DataFrame(df_in.apply(formatRepeaterOutput, axis=1).values,columns=['FullDataString'],index=df_in.index)

    df_Format['FRAMEQ_NUMW'] = (df_Format['FullDataString'] .str.len()/16).astype(int)

    df_Format['IdleWord'] = (df_BX_CNT.BX_CNT.values<<11) + TxSyncWord

    frameQ_headers = [f'FRAMEQ_{i}' for i in range(28)]

    df_Format[frameQ_headers]= pd.DataFrame(df_Format.apply(splitToWords,axis=1).tolist(),columns=frameQ_headers,index=df_Format.index)

    df_Format['FRAMEQ_Truncated'] = 0

    return df_Format[frameQ_headers+['FRAMEQ_NUMW','FRAMEQ_Truncated','IdleWord']]
