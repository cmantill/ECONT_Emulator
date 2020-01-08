import numpy as np
from encode import encode

def formatThresholdOutput(row,nDropBit=1,debug=False):

    nExp = 4
    nMant = 3
    roundBits = True

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
        
        bitmap = np.array([int(x) for x in format(ADD_MAP, '#0%ib'%(48+2))[2:]][::-1])
        channelNumbers = np.arange(48)[bitmap==1]
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

    formattedData = header + dataType + modSumData + extraBit + nChannelData + AddressMapData + ChargeData
    if len(formattedData)%16==0:
        nPadBits=0
        paddedData = formattedData
    else:
        nPadBits = 16 - (len(formattedData)%16)
        paddedData = formattedData + '0'*nPadBits

#    print(NTCQ,nPadBits)
    if not debug:
        return paddedData
    else:
        return [header, dataType , modSumData , extraBit ,nChannelData , len(AddressMapData) , len(ChargeData)]
