import numpy as np
from encode import encode

def formatThresholdOutput(row,debug=False):

    NTCQ=row['NTCQ']
    SUM =row['SUM']
    ADD_MAP  = list(row['ADD_MAP'])

    CHARGEQ = np.array(list(row['CHARGEQ']))
    CHARGEQ=CHARGEQ[CHARGEQ>0]      ## remove zeros

    MOD_SUM_0 = row['MOD_SUM_0']
    MOD_SUM_1 = row['MOD_SUM_1']
    MOD_SUM_2 = row['MOD_SUM_2']    
    #header = format(BC, '#0%ib'%(15))[-5:]
    header =  '00000'           ## don't assign BC for now    

    dataType = ''
    if NTCQ==0: 
        dataType='000'
    elif NTCQ<8:
        dataType='001'
    else:
        dataType='010'

    modSumData = format(SUM, '#0%ib'%(10))[2:]
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
        return [header, dataType , modSumData , extraBit ,nChannelData , len(AddressMapData) , len(ChargeData)]



def formatThresholdTruncatedOutput(row):

    header =  '00000'           ## don't assign BC for now    

    dataType_Truncated = '110'

    SUM =row['SUM']
    modSumData = encode(SUM,0,5,3)

    formattedData_Truncated = header + dataType_Truncated + modSumData
        
    return formattedData_Truncated



def formatBestChoiceOutput(row, nTC = 1, isHDM=True,debug=False):

    nExp = 4
    nMant = 3
    roundBits = False
    nDropBit = 3 if isHDM else 1

    ADD_MAP = list(row[[f'BC_Address_{i}' for i in range(48)]])
    CHARGEQ = list(row[[f'BC_Charge_{i}' for i in range(48)]])

    SUM =sum(CHARGEQ)

    sel_q = CHARGEQ[:nTC]
    sel_add = ADD_MAP[:nTC]

    BITMAP = np.zeros(48, dtype=np.int32)
    CHARGEQ = np.zeros(48, dtype=np.int32)

    BITMAP[sel_add] = 1
    CHARGEQ[sel_add] = sel_q 

    CHARGEQ=CHARGEQ[CHARGEQ>0]      ## remove zeros

    #header = format(BC, '#0%ib'%(15))[-5:]
    header =  '00000'           ## don't assign BC for now    
    modSumData = encode(SUM,0,5,3)

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
        AddressMapData=''.join([str(i) for i in ADD_MAP])
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



def splitToWords(row, colName='FRAMEQ', N=16,totalWords=25):
    fullData = row[colName]
    
    words = [fullData[i*N:(i+1)*N] for i in range(int(len(fullData)/N))]

    if len(words)<totalWords:
        words += ['']*(totalWords-len(words))

    return words
