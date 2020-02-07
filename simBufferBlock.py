import pandas as pd
import numpy as np

import optparse
import os


def getBufferOutputs(df, nOutputLinks, outputDir, nBitsPerLink=32, T1_Latency=12 , T2_Latency = 6, T3=8):

    T1 = T1_Latency*nOutputLinks*2
    T2 = T2_Latency*nOutputLinks*2

    BufferContents = []
    
    idleWord = '1111000011110000'
    
    columns = [f'WORD_{i}' for i in range(2*nOutputLinks)]
    columns += ['Truncated', 'Nbuf', 'NBXc', 'Cond1', 'Cond2','Cond3','Cond4']
    totalData = []
    for BX in df.index:        
        currentBXData = df.loc[BX].dropna().values[:-1]
        truncatedData = df.loc[BX].FRAMEQ_TRUNC
        NBXc = len(currentBXData)
        Nbuf = len(BufferContents)
        truncated = False
        cond1 = False
        cond2 = False
        cond3 = False
        cond4 = False

        if (Nbuf + NBXc) > T1:
            truncated = True
            BufferContents += [truncatedData]
            cond1 = True
        elif ((Nbuf + NBXc) <= T1) and (Nbuf > T2) and (NBXc <= T3):
            truncated = True
            BufferContents += [truncatedData]
            cond2 = True
        elif ((Nbuf + NBXc) <= T1) and (Nbuf > T2) and (NBXc > T3):
            BufferContents += currentBXData.tolist()
            cond3 = True
        elif ((Nbuf + NBXc) <= T1) and (Nbuf <= T2):
            BufferContents += currentBXData.tolist()                 
            cond4 = True
        else:
            print("ERROR")

        
        outputData = BufferContents[:2*nOutputLinks]        
        if len(outputData) < 2*nOutputLinks:
            outputData += [idleWord]*(2*nOutputLinks - len(outputData))
        outputData += [truncated, Nbuf, NBXc, cond1, cond2, cond3, cond4]
        
        totalData.append(outputData)

        BufferContents = BufferContents[2*nOutputLinks:]
        
    totalData = pd.DataFrame(data = np.array(totalData), columns=columns, index=df.index)
    totalData.to_csv(f'{outputDir}/Buffers/Output_Buffer_{nOutputLinks}Links.csv',index=False)

    return


def main(opt, args):
    directory = opt.dir

    inputFileName = f'{directory}/Algorithm_Output_Format.csv'

    df = pd.read_csv(inputFileName,dtype=object)

    maxLatency = 12
    T1_Words=24 
    T2_Words=12
    T3_Words=8

    os.makedirs(f'{directory}/Buffers',exist_ok=True)

    with open(f'{directory}/Buffers/OverflowControls.csv','w') as _file:
        _file.write('T1, T2, T3\n')
        _file.write(f'{T1_Words},{T2_Words},{T3_Words}\n')
 
    if opt.NLinks==-1:
        linkRange = range(2,13)
    else:
        linkRange = [opt.NLinks]
       
    for nLinks in linkRange:
        print(nLinks)
    
        getBufferOutputs(df, nOutputLinks=nLinks, outputDir=directory, nBitsPerLink=32, T1_Latency=T1_Words/2 , T2_Latency = T2_Words/2, T3=T3_Words)


if __name__=='__main__':
    parser = optparse.OptionParser()
    
    parser.add_option('-d',"--dir", type="string", default = './', dest="dir", help="directory to load input from and save output to")
    parser.add_option('-N',"--NLinks", type="int", default = -1, dest="NLinks", help="Run for a single number of links (default -1, run with 2-12 links)")
    (opt,args) = parser.parse_args()

    main(opt,args)
