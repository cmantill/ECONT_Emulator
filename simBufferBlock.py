import pandas as pd
import numpy as np

import optparse
import os

import glob
def alterCSVFiles(outputDir):
    csvFiles = glob.glob(f'{outputDir}/*csv')

    for fName in csvFiles:
        with open(fName, "r") as sources:
            lines = sources.readlines()
        with open(fName, "w") as sources:
            for line in lines:
                sources.write(line.replace(',',', '))


def getBufferOutputs(df, nOutputLinks, outputDir, algoType = "ThresholdSum", nBitsPerLink=32, T1_Latency=12 , T2_Latency = 6, T3=8):

    fixedLatency=True
    if algoType=='ThresholdSum':
        fixedLatency = False

    T1 = T1_Latency*nOutputLinks*2
    T2 = T2_Latency*nOutputLinks*2

    BufferContents = np.array([-1]*400)
    writePointer = 0
    
    totalData = []

    for BX in df.index:        
        currentBXData = df.loc[BX][[f'WORD_{i}' for i in range(25)]].values
        if not fixedLatency:
            truncatedData = df.loc[BX].FRAMEQ_TRUNC
            NBXc = df.loc[BX].wordCount
        else:
            truncatedData = 0
            NBXc = nOutputLinks*2
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
            BufferContents[writePointer:writePointer+25] = currentBXData
            cond3 = True
        elif ((Nbuf + NBXc) <= T1) and (Nbuf <= T2):
            BufferContents[writePointer:writePointer+25] = currentBXData
            cond4 = True
        else:
            print("ERROR")
        if truncated: 
            writePointer += 1
        else:
            writePointer += NBXc
        
        outputData = BufferContents[:2*nOutputLinks].tolist()
        BufferContents[0:400-2*nOutputLinks] = BufferContents[2*nOutputLinks:400]
        writePointer = max(writePointer-2*nOutputLinks, 0)


        # if len(outputData) < 2*nOutputLinks:
        #     outputData += [idleWord]*(2*nOutputLinks - len(outputData))
        outputData += [truncated, Nbuf, NBXc, cond1, cond2, cond3, cond4]
        
        totalData.append(outputData)

#        BufferContents = BufferContents[2*nOutputLinks:]
        
    wordColumns = [f'WORD_{i}' for i in range(2*nOutputLinks)]
    statusColumns = ['Truncated', 'Nbuf', 'NBXc', 'Cond1', 'Cond2','Cond3','Cond4']
    totalData = pd.DataFrame(data = np.array(totalData), columns=wordColumns + statusColumns, index=df.index)
    totalData[wordColumns].to_csv(f'{outputDir}/Buffers/Buffer_Output_{algoType}_{nOutputLinks}Links.csv',index=False)
    totalData[statusColumns].to_csv(f'{outputDir}/Buffers/Buffer_Status_{algoType}_{nOutputLinks}Links.csv',index=False)

    return


def thresholdSumBuffer(directory):
    inputFileName = f'{directory}/Formatter_Output_ThresholdSum.csv'
    dfTS = pd.read_csv(inputFileName,dtype=int,skipinitialspace=True)

    inputFileName = f'{directory}/Formatter_Output_BC.csv'
    dfBC = pd.read_csv(inputFileName,dtype=int,skipinitialspace=True)
    inputFileName = f'{directory}/Formatter_Output_STC.csv'
    dfSTC = pd.read_csv(inputFileName,dtype=int,skipinitialspace=True)

    inputFileName = f'{directory}/Formatter_Output_RPT.csv'
    dfRPT = pd.read_csv(inputFileName,dtype=int,skipinitialspace=True)



    maxLatency = 12
    T1_Words=24 
    T2_Words=12
    T3_Words=8

    os.makedirs(f'{directory}/Buffers',exist_ok=True)

    
    with open(f'{directory}/Buffers/Formatter_Buffer_Input_Buffer_Threshold_T1.csv','w') as _file:
        _file.write('BUFFER_THRESHOLD_T1\n')
        _file.write(f'{T1_Words}\n')

    with open(f'{directory}/Buffers/Formatter_Buffer_Input_Buffer_Threshold_T2.csv','w') as _file:
        _file.write('BUFFER_THRESHOLD_T2\n')
        _file.write(f'{T2_Words}\n')

    with open(f'{directory}/Buffers/Formatter_Buffer_Input_Buffer_Threshold_T3.csv','w') as _file:
        _file.write('BUFFER_THRESHOLD_T3\n')
        _file.write(f'{T3_Words}\n')

    with open(f'{directory}/Buffers/OverflowControls.csv','w') as _file:
        _file.write('T1, T2, T3\n')
        _file.write(f'{T1_Words},{T2_Words},{T3_Words}\n')
 
    if opt.NLinks==-1:
        linkRange = range(1,15)
    else:
        linkRange = [opt.NLinks]
       
    for nLinks in linkRange:
        print(nLinks)
    
        getBufferOutputs(dfTS, nOutputLinks=nLinks, outputDir=directory, algoType='ThresholdSum', nBitsPerLink=32, T1_Latency=T1_Words/2 , T2_Latency = T2_Words/2, T3=T3_Words)

        getBufferOutputs(dfBC, nOutputLinks=nLinks, outputDir=directory, algoType='BC', nBitsPerLink=32)

        getBufferOutputs(dfSTC, nOutputLinks=nLinks, outputDir=directory, algoType='STC', nBitsPerLink=32)
        getBufferOutputs(dfRPT, nOutputLinks=nLinks, outputDir=directory, algoType='RPT', nBitsPerLink=32)



def main(opt, args):
    directory = opt.dir

    thresholdSumBuffer(directory)

    if opt.replaceCSVDelim:
        alterCSVFiles(f'{directory}/Buffer')
    
    
if __name__=='__main__':
    parser = optparse.OptionParser()
    
    parser.add_option('-d',"--dir", type="string", default = './', dest="dir", help="directory to load input from and save output to")
    parser.add_option('-N',"--NLinks", type="int", default = -1, dest="NLinks", help="Run for a single number of links (default -1, run with 2-12 links)")
    parser.add_option('--CSVNoSpace',dest='replaceCSVDelim', action='store_false', default=True, help='keep the output csv files as comma delimited with no trailing space')
    (opt,args) = parser.parse_args()

    main(opt,args)
