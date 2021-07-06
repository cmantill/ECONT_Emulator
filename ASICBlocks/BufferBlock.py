import pandas as pd
import numpy as np

MAX_EPORTTX=13

def Buffer(df_formatterOutput, EPORTTX_NUMEN, T1 , T2, T3):

    BufferContents = np.array([-1]*400,dtype=np.int64)
    writePointer = 0
    
    totalData = []

    for BX in df_formatterOutput.index:        
        currentBXData = df_formatterOutput.loc[BX][[f'FRAMEQ_{i}' for i in range(2*MAX_EPORTTX)]].values
        truncatedData = df_formatterOutput.loc[BX][['FRAMEQ_Truncated_0','FRAMEQ_Truncated_1']].values
        NBXc = df_formatterOutput.loc[BX].FRAMEQ_NUMW
        
        Nbuf = writePointer
        truncated = False
        cond1 = False
        cond2 = False
        cond3 = False
        cond4 = False

        if (Nbuf + NBXc) > T1:
            truncated = True
            ### explicitly set eighth bit to 0
            truncatedData[0] = truncatedData[0] & ~(1<<8)

            BufferContents[writePointer:writePointer+2] = truncatedData
            cond1 = True
        elif ((Nbuf + NBXc) <= T1) and (Nbuf > T2) and (NBXc <= T3):
            truncated = True
            ### explicitly set eighth bit to 1
            truncatedData[0] = truncatedData[0] | (1<<8)

            BufferContents[writePointer:writePointer+2] = truncatedData
            cond2 = True
        elif ((Nbuf + NBXc) <= T1) and (Nbuf > T2) and (NBXc > T3):
            BufferContents[writePointer:writePointer+2*MAX_EPORTTX] = currentBXData
            cond3 = True
        elif ((Nbuf + NBXc) <= T1) and (Nbuf <= T2):
            BufferContents[writePointer:writePointer+2*MAX_EPORTTX] = currentBXData
            cond4 = True
        else:
            print("ERROR")
        if truncated: 
            writePointer += 1
        else:
            writePointer += NBXc
        
        words = BufferContents[:2*EPORTTX_NUMEN]
        
        outputData = ((words[::2]<<16) + words[1::2]).tolist()
        BufferContents[0:400-2*EPORTTX_NUMEN] = BufferContents[2*EPORTTX_NUMEN:400]
        writePointer = max(writePointer-2*EPORTTX_NUMEN, 0)

        outputData += [0]*(MAX_EPORTTX-EPORTTX_NUMEN)
        outputData += [truncated, Nbuf, NBXc, cond1, cond2, cond3, cond4]
        
        totalData.append(outputData)

    while writePointer > 0:
        words = BufferContents[:2*EPORTTX_NUMEN]
        
        outputData = ((words[::2]<<16) + words[1::2]).tolist()
        BufferContents[0:400-2*EPORTTX_NUMEN] = BufferContents[2*EPORTTX_NUMEN:400]
        writePointer = max(writePointer-2*EPORTTX_NUMEN, 0)

        outputData += [0]*(MAX_EPORTTX-EPORTTX_NUMEN)
        outputData += [truncated, Nbuf, NBXc, cond1, cond2, cond3, cond4]
        
        totalData.append(outputData)

    txDataColumns = [f'TX_DATA_{i}' for i in range(MAX_EPORTTX)]
    statusColumns = ['Truncated', 'Nbuf', 'NBXc', 'Cond1', 'Cond2','Cond3','Cond4']
    #df_BufferOutput = pd.DataFrame(data = np.array(totalData), columns=txDataColumns + statusColumns, index=df_formatterOutput.index)
    df_BufferOutput = pd.DataFrame(data = np.array(totalData), columns=txDataColumns + statusColumns)

    return df_BufferOutput
