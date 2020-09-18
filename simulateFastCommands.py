import argparse
import pandas as pd
import numpy as np
import os

import shutil
import warnings

import glob

from ECONT_Emulator import runEmulator
from VerificationData import makeVerificationData

allowedFastCommands = ['ocr','bcr','chipsync','linkresetecont','linkresetroct']

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


fullFastCommandList = ["FASTCMD_NOT_IDLE", "FASTCMD_PREL1A", "FASTCMD_L1A", "FASTCMD_L1A_PREL1A", "FASTCMD_L1A_NZS", "FASTCMD_L1A_NZS_PREL1A", "FASTCMD_L1A_BCR", "FASTCMD_L1A_BCR_PREL1A", "FASTCMD_L1A_CALPULSEINT", "FASTCMD_L1A_CALPULSEEXT", "FASTCMD_L1A_CALPULSEINT_PREL1A", "FASTCMD_L1A_CALPULSEEXT_PREL1A", "FASTCMD_BCR", "FASTCMD_BCR_PREL1A", "FASTCMD_BCR_OCR", "FASTCMD_CALPULSEINT", "FASTCMD_CALPULSEEXT", "FASTCMD_CALPULSEINT_PREL1A", "FASTCMD_CALPULSEEXT_PREL1A", "FASTCMD_CHIPSYNC", "FASTCMD_EBR", "FASTCMD_ECR", "FASTCMD_LINKRESETROCT", "FASTCMD_LINKRESETROCD", "FASTCMD_LINKRESETECONT", "FASTCMD_LINKRESETECOND", "FASTCMD_SPARE_0", "FASTCMD_SPARE_1", "FASTCMD_SPARE_2", "FASTCMD_SPARE_3", "FASTCMD_SPARE_4", "FASTCMD_SPARE_5", "FASTCMD_SPARE_6", "FASTCMD_SPARE_7"]

def produceRandomFastCommandsAndOffsets(fastCommandPercent, N):
    commandsBX = np.random.choice(np.arange(N), np.random.poisson(N*fastCommandPercent/100.), replace=False)
    fastCommandBX = np.random.choice(commandsBX, min(np.random.poisson(len(commandsBX)*.5),len(commandsBX)), replace=False)
    offsetBX = list(set(commandsBX) - set(fastCommandBX))

    offsetChanges = []
    fastCommands = []

    for bx in offsetBX:
        offsetChanges.append([int(bx/3564), bx%3564, np.random.choice(range(12)),int(np.random.normal(128,30))])
    for bx in fastCommandBX:
        fastCommands.append([np.random.choice(fullFastCommandList), int(bx/3564), bx%3564])

    return offsetChanges, fastCommands


def produceEportRX_input(inputDir, outputDir, configFile=None, randomFastCommands=-1, N=-1, ORBSYN_CNT_LOAD_VAL=0, makeOffsetChange=False, randomSampling=False):

    inputFile=f'{inputDir}/EPORTRX_data.csv'
    outputFile=f'{outputDir}/EPORTRX_data.csv'

    # inputFile = f'{inputDir}/MuxFixCalib_Input_ePortRX.csv'
    # outputFile = f'{outputDir}/ECON_T_ePortRX.txt'

    try:
        eportRXData = pd.read_csv(inputFile,skipinitialspace=True)
    except:
        print (f'Problem loading {inputFile}, trying EPortRX_Input_EPORTRX_data.csv')
        try:
            inputFile2=f'{inputDir}/EPortRX_Input_EPORTRX_data.csv'
            eportRXData = pd.read_csv(inputFile2,skipinitialspace=True)
            if not (eportRXData.FASTCMD=='FASTCMD_IDLE').all():
                print('Input data set has fast commands issued, cannot re-process a second time')
                print('Exiting')
                exit()
            eportRXData = eportRXData[[f'ePortRxDataGroup_{i}' for i in range(12)]] & 268435455

        except:
            print('Unable to load eportRX data, exiting')
            exit()

    shutil.copy(f'{inputDir}/metaData.py',f'{outputDir}/metaData.py')

    if N==-1:
        N = len(eportRXData)
    elif N > len(eportRXData):
        if not randomSampling:
            print(f'More BX requested than in the input file, using only {len(eportRXData)} BX from input')
            N = len(eportRXData)

    if randomSampling:
        idxChoice = np.random.choice(eportRXData.index.values, N)
        eportRXData = eportRXData.loc[idxChoice].reset_index(drop=True)
    else:
        eportRXData = eportRXData[:N]

    pd.DataFrame({'ORBSYN_CNT_LOAD_VAL':[ORBSYN_CNT_LOAD_VAL]*N}).to_csv(f'{outputDir}/ORBSYN_CNT_LOAD_VAL.csv',index=False)
    
    dataCols = [f'ePortRxDataGroup_{i}' for i in range(12)]

    eportRXData['GOD_ORBIT_NUMBER'] = (np.arange(N)/3564).astype(int)
    eportRXData['GOD_BUCKET_NUMBER'] = np.arange(N)%3564

    eportRXData['FASTCMD']='FASTCMD_IDLE'
    eportRXData['DATA_SYNCH']='DATA'

    eportRXData['OFFSET_STATUS'] = "STABLE"
    eportRXData['OFFSET_CHANNEL'] = -1
    eportRXData['OFFSET'] = -1

    cols = ['GOD_ORBIT_NUMBER','GOD_BUCKET_NUMBER','FASTCMD','DATA_SYNCH']+dataCols+['OFFSET_STATUS','OFFSET_CHANNEL','OFFSET']

    eportRXData = eportRXData[cols]

    offsetChanges = []
    fastCommands = []

    if not configFile is None:
        offsetChanges, fastCommands = parseConfig(configFile)
    elif not randomFastCommands == -1:
        offsetChanges, fastCommands = produceRandomFastCommandsAndOffsets(randomFastCommands, N)
        print (offsetChanges)
        print (fastCommands)

    offsetChanges.sort()
    fastCommands.sort()

    if len(fastCommands)>0:
        #check for fast commmands issued in the same BX                                                                                                                                                        
        usedBX = []
        goodCommands = []
        for f in fastCommands:
            _command = f[0]
            _orbit = f[1]
            _bucket = f[2]
            _globalBX = _orbit* 3564 + _bucket
            if _globalBX>N:
                print(f'A fast command ({_command}) is issued for a BX ({_orbit},{_bucket}), beyond the maximum used ({N}), skipping this command')
                continue
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

        if ('ocr' in _command.lower()) or ('bcr' in _command.lower()) or ('chipsync' in _command.lower()):
            globalBXCounter[_globalBX:-1] = (np.arange(len(globalBXCounter[_globalBX:-1])) + ORBSYN_CNT_LOAD_VAL) % 3564

    # set header, with BX counter after the fast commands

    header = np.zeros(N,dtype=int) + 10
    header[globalBXCounter==0] = 9

    eportRXData.loc[header==9,'DATA_SYNCH'] = 'SYNCH'

    for c in dataCols:
        eportRXData[c] = eportRXData[c] + (header<<28)


    #do link resets
    idle_packet = 2899102924 #0xaccccccc

    econtLinkReset=pd.DataFrame({'LINKRESETECONT':[0]*N},index=eportRXData.index)

    for f in fastCommands:
        _command = f[0]
        _orbit = f[1]
        _bucket = f[2]
        _globalBX = _orbit* 3564 + _bucket

        if 'linkresetroct' in _command.lower():
            _bxSyncEnd = _globalBX + 255
            if _bxSyncEnd>=N:
                _bxSyncEnd = N-1

            eportRXData.loc[_globalBX:_bxSyncEnd,dataCols] = idle_packet

        if 'linkresetecont' in  _command.lower():
            _bxSyncEnd = _globalBX + 255
            if _bxSyncEnd>=N:
                _bxSyncEnd = N-1

            econtLinkReset.loc[_globalBX:_bxSyncEnd,'LINKRESETECONT'] = 1



    for f in fastCommands:
        _command = f[0]
        _orbit = f[1]
        _bucket = f[2]
        _globalBX = _orbit* 3564 + _bucket

        eportRXData.loc[_globalBX,'FASTCMD'] = ("FASTCMD_"+_command.upper()) if not 'FASTCMD' in _command else _command

    for c in offsetChanges:
        _orbit = c[0]
        _bucket = c[1]
        _eport = c[2]
        _newVal = c[3]

        _globalBX = _orbit* 3564 + _bucket

        if _globalBX >= len(eportRXData):
            warnings.warn(f'Bucket to change ({_orbit},{_bucket}) is beyond the size of the test ({len(eportRXData)}), ignoring this change')
            continue
        if not eportRXData.loc[_globalBX,'OFFSET'] == -1:
            warnings.warn(f'Already changing on eport ({eportRXData.loc[_globalBX,"OFFSET"]}) in this bucket ({_orbit},{_bucket}), ignoring change to eport {_eport}')
            continue

        eportRXData.loc[_globalBX,'OFFSET_STATUS'] = 'CHANGE'
        eportRXData.loc[_globalBX,'OFFSET_CHANNEL'] = _eport
        eportRXData.loc[_globalBX,'OFFSET'] = _newVal

        if makeOffsetChange:
            _column = f'DATA_{_eport}'

            #convert data columns to binary
            for c in dataCols:
                eportRXData[_columns] = eportRXData[columns].apply(bin).str[2:]


            startingData = ''.join(eportRXData.loc[_globalBX:,_column].astype(int).apply(bin).str[2:].values)

            relativeChange = _newVal - offsets[_eport]

            if relativeChange>0:
                newData = '0'*abs(relativeChange) +  startingData[:-1*relativeChange]
            elif relativeChange<0:
                newData = startingData[abs(relativeChange):] + '0'*abs(relativeChange)
            else:
                newData = startingData

            newData = [newData[i*32:(i+1)*32] for i in range(int(len(newData)/32))]
            eportRXData.loc[_globalBX:,_column] = newData

    eportRXData.to_csv(outputFile,index=False)
    econtLinkReset.to_csv(f'{outputDir}/LinkResetEconT.csv',index=False)

    return offsetChanges, fastCommands, N




if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-i',"--input", default = None ,dest="inputDir", required=True, help="input directory name containing verification CSV files (default: None)")
    parser.add_argument('-o',"--output", default = None ,dest="outputDir", required=True, help="directory name for output verification data")
    parser.add_argument('-c','--config', default = None, dest='configFile', help='configuration file from which to read the changes (default: None)')
    parser.add_argument('-N', type=int, default = -1,dest="N", help="Number of BX to use, -1 is all in input (default: -1)")
    parser.add_argument('--random', default = False,dest="RandomSampling", action='store_true', help="Use random sampling of input data to increase statistics")
    parser.add_argument('--randomFast','--randomFastCommands', default = -1, type=float, dest='randomFastCommands', help='issue random fast commands a certain percent of the time (default is -1, which is off)')
    parser.add_argument('-L', type=int, default = -1,dest="NLinks", help="Number of ePortTX links to use, -1 is all in input (default: -1)")
    parser.add_argument('--counterReset', type=int, default = 0,dest="ORBSYN_CNT_LOAD_VAL", help="Value to reset BX counter to at reset (default: 0)")


    args = parser.parse_args()

    os.makedirs(args.outputDir,exist_ok=True)

    tempOutputDir = (args.outputDir+"/temp").replace("//","/")
    os.makedirs(tempOutputDir,exist_ok=True)

    offsetChanges, fastCommands, N = produceEportRX_input(inputDir = args.inputDir, 
                                                          outputDir = tempOutputDir, 
                                                          configFile = args.configFile,
                                                          randomFastCommands = args.randomFastCommands,
                                                          N = args.N,
                                                          ORBSYN_CNT_LOAD_VAL=args.ORBSYN_CNT_LOAD_VAL,
                                                          makeOffsetChange=False,
                                                          randomSampling=args.RandomSampling)

    runEmulator(tempOutputDir, ePortTx=args.NLinks)

    makeVerificationData(tempOutputDir, args.outputDir)

    shutil.rmtree(tempOutputDir)
    
