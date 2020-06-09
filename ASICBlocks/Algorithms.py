import pandas as pd
import numpy as np
from Utils.encode import encode, decode

encodeV = np.vectorize(encode)
decodeV = np.vectorize(decode)

def makeCHARGEQ(row, nDropBit=1):
    nExp = 4
    nMant = 3
    roundBits = False

    asInt  = True
    
    raw_charges     = np.array(row.values[row.values>0]).astype(int)
    if len(raw_charges)>0:
        encoded_charges = encodeV(raw_charges,nDropBit,nExp,nMant,roundBits,asInt=True)
    else:
        encoded_charges = np.zeros(48,dtype=int)
        
    return np.pad(encoded_charges,(0,48-len(encoded_charges)),mode='constant',constant_values=0)


def ThresholdSum(df_CALQ, THRESHV_Registers, DropLSB):
    ADD_MAP_Headers = [f'ADDRMAP_{i}' for i in range(48)]
    CHARGEQ_Headers = [f'CHARGEQ_{i}' for i in range(48)]

    df_Threshold_Sum = (df_CALQ>=THRESHV_Registers).astype(int)
    df_Threshold_Sum.columns = ADD_MAP_Headers

    qlist = ((df_CALQ>=THRESHV_Registers).astype(int)*df_CALQ).apply(makeCHARGEQ, nDropBit=DropLSB,axis=1)
    df_Threshold_Sum[CHARGEQ_Headers] = pd.DataFrame(qlist.values.tolist(),index=qlist.index,columns=CHARGEQ_Headers)
    df_Threshold_Sum['SUM'] = encodeV((df_CALQ).sum(axis=1),0,5,3,False,True)
    df_Threshold_Sum['SUMNOTTRANSMITTED'] = encodeV((df_CALQ<THRESHV_Registers).sum(axis=1),0,5,3,False,True)

    return df_Threshold_Sum



from .bestchoice import sort, batcher_sort

def BestChoice(df_CALQ, DropLSB):
    df_in = pd.DataFrame(df_CALQ.values>>DropLSB,columns=df_CALQ.columns, index=df_CALQ.index)

    df_sorted, _ = sort(df_in)
    df_sorted_index = pd.DataFrame(df_in.apply(batcher_sort, axis=1))

    df_sorted.columns = ['BC_CHARGE_{}'.format(i) for i in range(0, df_sorted.shape[1])]
    df_sorted_index.columns = ['BC_TC_Addr_{}'.format(i) for i in range(0, df_sorted_index.shape[1])]

    df_sorted[df_sorted_index.columns] = df_sorted_index
    return df_sorted



    
from .supertriggercell import supertriggercell_2x2, supertriggercell_4x4

def SuperTriggerCell(df_CALQ):

    stcData_2x2 = df_CALQ.apply(supertriggercell_2x2,axis=1)
    stcData_4x4 = df_CALQ.apply(supertriggercell_4x4,axis=1)

    cols_XTC4_9 = [f'XTC4_9_Sum_{i}' for i in range(12)]
    cols_XTC4_7 = [f'XTC4_7_Sum_{i}' for i in range(12)]
    cols_MAX4_ADDR = [f'MAX4_Addr_{i}' for i in range(12)]
    
    cols_XTC16_9 = [f'XTC16_9_Sum_{i}' for i in range(3)]
    cols_MAX16_ADDR = [f'MAX16_Addr_{i}' for i in range(3)]

    df_SuperTriggerCell = pd.DataFrame(stcData_2x2.tolist(),columns = cols_XTC4_9+cols_MAX4_ADDR, index = df_CALQ.index)

    df_SuperTriggerCell[cols_XTC16_9 + cols_MAX16_ADDR] = pd.DataFrame(stcData_4x4.tolist(),columns = cols_XTC16_9+cols_MAX16_ADDR, index = df_CALQ.index)

    for i,c in enumerate(cols_XTC4_9):
        df_SuperTriggerCell[cols_XTC4_7[i]] = encodeV(df_SuperTriggerCell[c],0,4,3,asInt=True)
        df_SuperTriggerCell[c] = encodeV(df_SuperTriggerCell[c],0,5,4,asInt=True)

    for c in cols_XTC16_9:
        df_SuperTriggerCell[c] = encodeV(df_SuperTriggerCell[c],0,5,4,asInt=True)

    
    return df_SuperTriggerCell[cols_XTC4_9 + cols_XTC16_9 + cols_XTC4_7 + cols_MAX4_ADDR + cols_MAX16_ADDR]




def Repeater(df_CALQ, DropLSB):

    df_Repeater = df_CALQ.apply(encodeV,args=(DropLSB,4,3,False,True))
    
    df_Repeater.columns = [f'REPEATERQ_{i}' for i in range(48)]
    
    return df_Repeater
    


def Algorithms(df_CALQ, THRESHV_Registers, DropLSB):
    df_Threshold_Sum = ThresholdSum(df_CALQ, THRESHV_Registers, DropLSB)
    
    df_BestChoice = BestChoice(df_CALQ, DropLSB)
    
    df_SuperTriggerCell = SuperTriggerCell(df_CALQ)
    
    df_Repeater = Repeater(df_CALQ, DropLSB)
    
    return df_Threshold_Sum, df_BestChoice, df_SuperTriggerCell, df_Repeater

