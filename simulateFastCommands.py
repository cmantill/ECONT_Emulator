import argparse
import pandas as pd
import numpy as np
import os

import warnings

import glob

allowedFastCommands = ['ocr','bcr','chipsync','linkreset']

#correct the formatted data for the updated headers
def correctFormattedHeader(row):
    NULL = row['NULL']
    nWords = row['wordCount']
    values = row.values
    values[0] = values[0]&2047 + NULL
    for i in range(nWords,28):
        values[i] = NULL
    return values

def alterCSVFiles(outputDir):
    csvFiles = glob.glob(f'{outputDir}/*csv')

    for fName in csvFiles:
        with open(fName, "r") as sources:
            lines = sources.readlines()
        with open(fName, "w") as sources:
            for line in lines:
                sources.write(line.replace(',',', '))

    
def parseConfig(configName):
    offsetChanges = []
    fastCommands = []

    with open(configName,'r') as configFile:
        for i, line in enumerate(configFile):
            #remove newline character
            line = line.replace('\n','')

            #allow # as a comment
            if '#' in line:
                line = line.split('#')[0]
            if len(line)==0: continue

            #remove leading or trailing spaces            
            while line[-1]==' ': 
                line = line[:-1]
            while line[0]==' ': 
                line = line[1:]

            values = line.split(' ')

            if values[2].lower()=='offset':
                if not len(values)==5:
                    print('-'*20)
                    print(f'  Unable to parse config file line {i}, "{line}"')
                    print(f'  Five values expected but only {len(values)} found')
                    print('  Expected: GodOrbit GodBucket OFFSET ePortNumber NewOffset')
                    continue
                offsetChanges.append([int(values[0]),int(values[1]),int(values[3]),int(values[4])])
            elif values[2].lower() in allowedFastCommands:
                fastCommands.append([values[2].lower(),int(values[0]),int(values[1])])
            else:
                print(f'Unknown command {values[2]}, skipping')
    return offsetChanges, fastCommands

                                

def produceEportRX_input(inputDir, outputDir, configFile=None, N=-1):

    inputFile = f'{inputDir}/MuxFixCalib_Input_ePortRX.csv'
    outputFile = f'{outputDir}/ECON_T_ePortRX.txt'

    eportRXData = pd.read_csv(inputFile,skipinitialspace=True)


    if N==-1:
        N = len(eportRXData)
    elif N > len(eportRXData):
        print(f'More BX requested than in the input file, using only {len(eportRXData)} BX from input')
        N = len(eportRXData)

    eportRXData = eportRXData[:N]

    dfFastCommands = pd.DataFrame({'godOrbitNumber':(np.arange(N)/3564).astype(int),'godBucketNumber':(np.arange(N)%3564).astype(int),'Command':'IDLE'})

    dataCols = [f'DATA_{i}' for i in range(12)]
    synchCols = [f'SYNCH_{i}' for i in range(12)]
    orbitCols = [f'ORBIT_{i}' for i in range(12)]

    eportRXData.columns = dataCols

    eportRXData = eportRXData.assign(**{c:2**31 for c in synchCols})
    eportRXData = eportRXData.assign(**{c:2**32-1 for c in orbitCols})

    eportRXData['godOrbitNumber'] = (np.arange(N)/3564).astype(int)
    eportRXData['godBucketNumber'] = np.arange(N)%3564

    eportRXData['CHANGE_OFFSET'] = -1
    eportRXData['OFFSET'] = 0

    cols = ['godOrbitNumber','godBucketNumber','CHANGE_OFFSET','OFFSET']
    for i in range(12):
        cols.append(dataCols[i])
        cols.append(synchCols[i])
        cols.append(orbitCols[i])
    eportRXData = eportRXData[cols]
    
    
    ### STARTING POINT OF CHANGING THE INPUTS
    ### SHOULD A "GOOD" VERSION BE DUMPED FOR AND OUTPUT VALUE, OR AFTER THE FAST COMMANDS

    ## load a config file with the requested changes:
    offsetChanges = []
    fastCommands = []

    if not configFile is None:
        offsetChanges, fastCommands = parseConfig(configFile)

    offsetChanges.sort()
    fastCommands.sort()

    if len(fastCommands)>0:
        #check for fast commmands issued in the same BX
        usedBX = []
        goodCommands = []
        for f in fastCommands:
            if not f[1:] in usedBX:
                usedBX.append(f[1:])
                goodCommands.append(f)
            else:
                print(f'A fast command is already issued for bucket ({f[1]},{f[2]}), skipping the command {f[0]} issued for the same bucket')
        fastCommands = goodCommands[:]


    #keep a global bunch crosing nubmer.  This can be used to later recreate the header
    globalBXCounter = np.arange(N) % 3564

    for f in fastCommands:
        _command = f[0]
        _orbit = f[1]
        _bucket = f[2]
        _globalBX = _orbit* 3564 + _bucket
        if _command.lower() in ['ocr','bcr','chipsync']:
            globalBXCounter[_globalBX:-1] = np.arange(len(globalBXCounter[_globalBX:-1])) % 3564
        
            dfFastCommands.loc[_globalBX,'Command'] = _command.upper()

    # set header, with BX counter after the fast commands
    header = np.zeros(N,dtype=int) + 10
    header[globalBXCounter==0] = 9

    eportRXData.loc[header==9,orbitCols] = 0

    for c in dataCols:
        eportRXData[c] = eportRXData[c] + (header<<28)


    #do link resets
    idle_packet = 2899102924 #0xaccccccc

    for f in fastCommands:
        _command = f[0]
        _orbit = f[1]
        _bucket = f[2]
        _globalBX = _orbit* 3564 + _bucket
        
        if _command.lower()=='linkreset':
            dfFastCommands.loc[_globalBX,'Command'] = _command.upper()

            _bxSyncEnd = _globalBX + 255
            if _bxSyncEnd>=N:
                _bxSyncEnd = N-1

            eportRXData.loc[_globalBX:_bxSyncEnd,dataCols] = idle_packet



    # assume the starting point of all offsets is 128 (is there something better?)
    offsets = [128]*12

    #convert data columns to binary
    for c in dataCols:
        eportRXData[c] = eportRXData[c].apply(bin).str[2:]

    for c in offsetChanges:
        _orbit = c[0]
        _bucket = c[1]
        _eport = c[2]
        _newVal = c[3]
        
        _globalBX = _orbit* 3564 + _bucket

        if _globalBX >= len(eportRXData):
            warnings.warn(f'Bucket to change ({_orbit},{_bucket}) is beyond the size of the test ({len(eportRXData)}), ignoring this change')
            continue
        if not eportRXData.loc[_globalBX,'CHANGE_OFFSET'] == -1:
            warnings.warn(f'Already changing on eport ({eportRXData.loc[_globalBX,"CHANGE_OFFSET"]}) in this bucket ({_orbit},{_bucket}), ignoring change to eport {_eport}')
            continue
        _column = f'DATA_{_eport}'
        
        startingData = ''.join(eportRXData.loc[_globalBX:,_column].tolist())

        relativeChange = _newVal - offsets[_eport]

        if relativeChange>0:
            newData = '0'*abs(relativeChange) +  startingData[:-1*relativeChange]
        elif relativeChange<0:
            newData = startingData[abs(relativeChange):] + '0'*abs(relativeChange)
        else:
            newData = startingData

        newData = [newData[i*32:(i+1)*32] for i in range(int(len(newData)/32))]

        eportRXData.loc[_globalBX:,_column] = newData
        eportRXData.loc[_globalBX,'CHANGE_OFFSET'] = _eport
        eportRXData.loc[_globalBX,'OFFSET'] = _newVal

        
    eportRXData.set_index(['godOrbitNumber','godBucketNumber'],inplace=True)



    for c in dataCols:
        eportRXData[c] = eportRXData[c].apply(int,args=[2])

    eportRXData.to_csv(outputFile)
    dfFastCommands.to_csv(outputFile.replace('ePortRX','fastCommands'))

    return offsetChanges, fastCommands, N


def getVerificationData(inputDir, outputDir, fastCommands, N):

    #copied over register files from input to output directory
    registerFiles = ['Algorithm_Input_DroppedBits.csv','Algorithm_Input_HighDensity.csv','Algorithm_Input_Threshold.csv','Algorithm_Input_Type_BC.csv','Algorithm_Input_Type_RPT.csv','Algorithm_Input_Type_STC.csv','Algorithm_Input_Type_TS.csv','Calibration_Input_Calibration.csv','Formatter_Buffer_Input_Tx_Sync_Word.csv']

    for _fName in registerFiles:
        df = pd.read_csv(f'{inputDir}/{_fName}',skipinitialspace=True).loc[:N-1]
        df.to_csv(f'{outputDir}/{_fName}',index=False)


    #Need to change for link reset
    dataFiles = ['Algorithm_Input_CalQ.csv','Algorithm_Output_AddrMap.csv','Algorithm_Output_BC_Charge.csv','Algorithm_Output_BC_TC_map.csv','Algorithm_Output_ChargeQ.csv','Algorithm_Output_MAX16_ADDR.csv','Algorithm_Output_MAX4_ADDR.csv','Algorithm_Output_NTCQ.csv','Algorithm_Output_RepeaterQ.csv','Algorithm_Output_Sum.csv','Algorithm_Output_XTC16_9.csv','Algorithm_Output_XTC4_7.csv','Algorithm_Output_XTC4_9.csv','MuxFixCalib_Input_ePortRX.csv','MuxFixCalib_PreCalibration_F2F.csv']
        
    #need to change for link reset data, and update headers
    formatFiles = ['Formatter_Output_BC.csv','Formatter_Output_RPT.csv','Formatter_Output_STC.csv','Formatter_Output_ThresholdSum.csv']
    
    #need to be upated for BCR
    headerFiles = ['Algorithm_Input_Header.csv','Algorithm_Output_Header.csv']
        
    if len(fastCommands)==0:
        #copy all files over as they are
        for _fName in dataFiles+formatFiles+headerFiles:
            df = pd.read_csv(f'{inputDir}/{_fName}',skipinitialspace=True).loc[:N-1]
            df.to_csv(f'{outputDir}/{_fName}',index=False)
    else:


        #read in the csv files that will need to be changed by a link reset
        inputValuesDF = {_fName: pd.read_csv(f'{inputDir}/{_fName}',skipinitialspace=True).loc[:N-1] for _fName in dataFiles+formatFiles}
        idleValuesDF = {_fName: pd.read_csv(f'{inputDir}/Idle/{_fName}',skipinitialspace=True).loc[:N-1] for _fName in dataFiles+formatFiles}

        globalBXCounter = np.arange(N) % 3564

        for f in fastCommands:
            _command = f[0]
            _orbit = f[1]
            _bucket = f[2]
            _globalBX = _orbit* 3564 + _bucket

            if _command.lower() in ['ocr','bcr','chipsync']:
                globalBXCounter[_globalBX:-1] = np.arange(len(globalBXCounter[_globalBX:-1])) % 3564        

            if _command.lower()=='linkreset':
                _bxSyncEnd = _globalBX + 255
                if _bxSyncEnd>=N:
                    _bxSyncEnd = N-1

                #replace 256 BX with Idle word values
                for _fName in dataFiles+formatFiles:
                    inputValuesDF[_fName].loc[_globalBX:_bxSyncEnd] = [idleValuesDF[_fName].loc[0].values]*int(_bxSyncEnd - _globalBX + 1)


        header = globalBXCounter%32

        np.savetxt(f'{outputDir}/Algorithm_Input_Header.csv', header,fmt='%d', header='HEADER',comments="")
        np.savetxt(f'{outputDir}/Algorithm_Output_Header.csv', header,fmt='%d', header='HEADER',comments="")


        # update the idle words in formatter and header of first word with the correct header after counter resets
        for _fName in formatFiles:
            inputValuesDF[_fName]['NULL'] = header<<11
            inputValuesDF[_fName].loc[:] = inputValuesDF[_fName].apply(correctFormattedHeader,axis=1).tolist()
            inputValuesDF[_fName].drop('NULL',axis=1,inplace=True)

        for _fName in dataFiles+formatFiles:
            inputValuesDF[_fName].to_csv(f'{outputDir}/{_fName}',index=False)

    
    #need to replicate these links
    formatBufferInputLinks=['AddrMap.csv','BC_Charge.csv','BC_TC_map.csv','ChargeQ.csv','MAX16_ADDR.csv','MAX4_ADDR.csv','NTCQ.csv','RepeaterQ.csv','Sum.csv','XTC16_9.csv','XTC4_7.csv','XTC4_9.csv']

    for _fName in formatBufferInputLinks:
        if not os.path.exists(f'{outputDir}/Formatter_Buffer_Input_{_fName}'):
            os.symlink(f'Algorithm_Output_{_fName}',f'{outputDir}/Formatter_Buffer_Input_{_fName}')

    for _fName in ['Type_BC.csv','Type_RPT.csv','Type_STC.csv','Type_TS.csv']:
        if not os.path.exists(f'{outputDir}/Formatter_Buffer_Input_{_fName}'):
            os.symlink(f'Algorithm_Input_{_fName}',f'{outputDir}/Formatter_Buffer_Input_{_fName}')



if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-i',"--input", default = None ,dest="inputDir", required=True, help="input directory name containing verification CSV files (default: None)")
    parser.add_argument('-o',"--output", default = None ,dest="outputDir", required=True, help="directory name for output verification data")
    parser.add_argument('-c','--config', default = None, dest='configFile', help='configuration file from which to read the changes (default: None)')
    parser.add_argument('-N', type=int, default = -1,dest="N", help="Number of BX to use, -1 is all in input (default: -1)")

    args = parser.parse_args()

    os.makedirs(args.outputDir,exist_ok=True)

    offsetChanges, fastCommands, N = produceEportRX_input(**vars(args))

    getVerificationData(args.inputDir, args.outputDir, fastCommands, N)

    alterCSVFiles(args.outputDir)
