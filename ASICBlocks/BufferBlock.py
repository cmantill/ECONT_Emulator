import pandas as pd
import numpy as np

def Buffer(df_formatterOutput, EPORTTX_NUMEN, T1 , T2, T3):

    BufferContents = np.array([-1]*400,dtype=np.int64)
    writePointer = 0
    
    totalData = []

    for BX in df_formatterOutput.index:        
        currentBXData = df_formatterOutput.loc[BX][[f'FRAMEQ_{i}' for i in range(28)]].values
        truncatedData = df_formatterOutput.loc[BX].FRAMEQ_Truncated
        NBXc = df_formatterOutput.loc[BX].FRAMEQ_NUMW
        
        Nbuf = writePointer
        truncated = False
        cond1 = False
        cond2 = False
        cond3 = False
        cond4 = False

        if (Nbuf + NBXc) > T1:
            truncated = True
            BufferContents[writePointer] = truncatedData
            cond1 = True
        elif ((Nbuf + NBXc) <= T1) and (Nbuf > T2) and (NBXc <= T3):
            truncated = True
            BufferContents[writePointer] = truncatedData + 2**8  #add extra bit switch data type of truncated data
            cond2 = True
        elif ((Nbuf + NBXc) <= T1) and (Nbuf > T2) and (NBXc > T3):
            BufferContents[writePointer:writePointer+28] = currentBXData
            cond3 = True
        elif ((Nbuf + NBXc) <= T1) and (Nbuf <= T2):
            BufferContents[writePointer:writePointer+28] = currentBXData
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

        outputData += [None]*(14-EPORTTX_NUMEN)
        outputData += [truncated, Nbuf, NBXc, cond1, cond2, cond3, cond4]
        
        totalData.append(outputData)

    txDataColumns = [f'TX_DATA_{i}' for i in range(14)]
    statusColumns = ['Truncated', 'Nbuf', 'NBXc', 'Cond1', 'Cond2','Cond3','Cond4']
    df_BufferOutput = pd.DataFrame(data = np.array(totalData), columns=txDataColumns + statusColumns, index=df_formatterOutput.index)

    return df_BufferOutput
