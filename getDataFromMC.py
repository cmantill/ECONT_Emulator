import uproot
import optparse
import os

import pandas as pd
import numpy as np
import time

from Utils.encode import encode, decode

from subprocess import Popen,PIPE
import gc

from Utils.getGeom import getGeomDF_V9, getGeomDF_V10, triggerCellUVRemap

encodeList = np.vectorize(encode)

tc_remap = pd.read_csv("Utils/LDM_TC_Mapping.csv")[['TC_Number','ECON_TC_Number_PostMux','ECON_TC_Number_PreMux']]

def droppedBits(isHDM):
    return 3 if isHDM else 1

def makeTCindexCols(group,col,iMOD=-1,tc_ColName='triggercell'):
    charges=np.zeros(48, dtype=float)    #zeros
    tclist = np.array(list(group[tc_ColName]))  #indexes of tc
    qlist  = np.array(list(group[col]))            #cols for each tc
    charges[tclist] = qlist                       #assign charges in positions
    if iMOD==-1:
        return list(charges.round().astype(np.int))
    modsum = 0
    if iMOD==0:   modsum = charges[0:16].sum().round().astype(np.int)
    elif iMOD==1: modsum = charges[16:32].sum().round().astype(np.int)
    elif iMOD==2: modsum = charges[32:48].sum().round().astype(np.int)                                             
    return modsum

InputLinkGrouping = [[ 0,  1,  2,  3],
                     [ 4,  5,  6,  7],
                     [ 8,  9, 10, 11],
                     [12, 13, 14, 15],
                     [16, 17, 18, 19],
                     [20, 21, 22, 23],
                     [24, 25, 26, 27],
                     [28, 29, 30, 31],
                     [32, 33, 34, 35],
                     [36, 37, 38, 39],
                     [40, 41, 42, 43],
                     [44, 45, 46, 47]]

def packIntoInputLinks(row):
    ENC_headers = ["ENCODED_%s"%i for i in range(0,48)]
    ENC_values = row[ENC_headers].values

    LINK = np.array([(ENC_values[lgroup][0]<<21)+(ENC_values[lgroup][1]<<14)+(ENC_values[lgroup][2]<<7)+(ENC_values[lgroup][3]) for lgroup in InputLinkGrouping])
    
    return LINK

def processTree(_tree, geomDF, subdet, layer, wafer=None, geomVersion="v11", jobNumber=0, nEvents=-1, nStart=-1):

    #load dataframe
    print('load dataframe')
    if nEvents==-1:
        nStop=None
        nStart=0
    else:
        if nStart==-1:
            nStart=0
            nStop=nEvents
        else:
            nStop = nEvents + nStart
    if geomVersion in ['v10','v11']:
        df = _tree.pandas.df( ['tc_subdet','tc_zside','tc_layer','tc_waferu','tc_waferv','tc_cellu','tc_cellv','tc_uncompressedCharge','tc_compressedCharge','tc_data','tc_mipPt','tc_simenergy'],entrystart=nStart,entrystop=nStop)
        df.columns = ['subdet','zside','layer','waferu','waferv','triggercellu','triggercellv','uncompressedCharge','compressedCharge','data','mipPt','simenergy']

    else:
        df = _tree.pandas.df( ['tc_subdet','tc_zside','tc_layer','tc_wafer','tc_cell','tc_uncompressedCharge','tc_compressedCharge','tc_data','tc_mipPt','tc_simenergy'],entrystart=nStart,entrystop=nStop)
        df.columns = ['subdet','zside','layer','wafer','triggercell','uncompressedCharge','compressedCharge','data','mipPt','simenergy']
    df.reset_index('subentry',drop=True,inplace=True)

    df['simenergyEvent'] = df.groupby('entry').simenergy.sum()

    #remove unwanted layers
    df = df[(df.subdet==subdet) & (df.layer==layer)]

    if geomVersion in ['v10','v11']:
        df['wafer'] = 100*df.waferu + df.waferv
        df['UV'] = list(zip(df.triggercellu, df.triggercellv))
        df['triggercell'] = df.UV.map(triggerCellUVRemap)

    if not wafer is None:
        df = df[df.wafer.isin(wafer)]

    df = df.reset_index().merge(tc_remap,left_on='triggercell',right_on='TC_Number',how='left').set_index('entry')

    df['triggercell'] = df.ECON_TC_Number_PostMux

    #set index
    df.set_index(['subdet','zside','layer','wafer','triggercell'],append=True,inplace=True)
    df.sort_index(inplace=True)

    #split +/- zside into separate entries
    df.reset_index(inplace=True)
    negZ_eventOffset = 5000
    jobNumber_eventOffset = 10000

#    maxN = df.entry.max()
    df.set_index(['zside'],inplace=True)
    df['entry'] = df['entry'] + jobNumber_eventOffset*jobNumber
    df.loc[-1,['entry']] = df.loc[-1,['entry']] + negZ_eventOffset

    df.reset_index(inplace=True)
    df.set_index(['entry','subdet','zside','layer','wafer','triggercell'],inplace=True)

    df.reset_index('entry',inplace=True)

    df['isHDM'] = geomDF['isHDM']
    df['eta']   = geomDF['eta']
    df['threshold_ADC'] = geomDF['threshold_ADC']




    
    ## Conversion factor for transverse charge
    df['corrFactor']    = 1./np.cosh(df.eta)
    ## Conversion factor for transverse charge (with finite precision)
    #df['corrFactor_finite']    = truncateFloatList(1./np.cosh(df.eta),8,4)
    precision  = 2**-11
    df['corrFactor_finite']    = round(1./np.cosh(df.eta) / precision) * precision
    #df['threshold_ADC_int'] = geomDF['threshold_ADC_int']

    df.reset_index(inplace=True)
    df.set_index(['entry','subdet','layer','wafer'],inplace=True)
#     df.set_index(['entry','subdet','zside','layer','wafer','triggercell'],inplace=True)
    
    nExp = 4
    nMant = 3
    nDropHDM = 3
    nDropLDM = 1
    roundBits = False
   
    df['encodedCharge'] = np.where(df.isHDM,
                                   df.uncompressedCharge.apply(encode,args=(nDropHDM,nExp,nMant,roundBits,True)),
                                   df.uncompressedCharge.apply(encode,args=(nDropLDM,nExp,nMant,roundBits,True)))


    return df.reset_index()



def writeInputCSV(odir,df,subdet,layer,waferList,geomVersion,appendFile=False,jobInfo="",fileInfo="",zeroSuppress=False):
    writeMode = 'w'
    header=True
    if appendFile:
        writeMode='a'
        header=False

    EPORTRX_headers = ["ePortRxDataGroup_%s"%i for i in range(0,12)]
    ENCODED_headers = ["ENCODED_%s"%i for i in range(0,48)]

    gb = df.groupby(['wafer','entry'],group_keys=False)
#    gb = df.groupby(['subdet','layer','wafer','entry'],group_keys=False)

    encodedlist   = gb[['ECON_TC_Number_PreMux','encodedCharge']].apply(makeTCindexCols,'encodedCharge',-1,'ECON_TC_Number_PreMux')

    simEnergy =gb[['simenergy']].sum()
    simEnergy[['eventSimEnergy']] =gb[['simenergyEvent']].mean()
    simEnergy.columns=['SimEnergyTotal','EventSimEnergy']

    df_out     = pd.DataFrame(index=encodedlist.index)
    df_out[ENCODED_headers]= pd.DataFrame((encodedlist).values.tolist(),index=encodedlist.index)

    df_out.fillna(0,inplace=True)

    # if zeroSuppress:
    #     nonZeroModule = df_out.sum(axis=1)>0
    #     print(df_out.sum(axis=1))
    #     df_out = df_out.loc[nonZeroModule]

    df_out[EPORTRX_headers] = pd.DataFrame(df_out.apply(packIntoInputLinks,axis=1).tolist(),columns=EPORTRX_headers,index=encodedlist.index)

    for _wafer in waferList:
        if geomVersion in ['v10','v11']:
            waferu = int(round(_wafer/100))
            waferv = int(_wafer-100*waferu)

            if odir=='./':
                waferDir = f'wafer_D{subdet}L{layer}U{waferu}V{waferv}{jobInfo}/'
            else:
                waferDir = f'{odir}/wafer_D{subdet}L{layer}U{waferu}V{waferv}{jobInfo}/'
        else:
            if odir=='./':
                waferDir = f'wafer_D{subdet}L{layer}W{_wafer}{jobInfo}/'
            else:
                waferDir = f'{odir}/wafer_D{subdet}L{layer}W{_wafer}{jobInfo}/'

        if not os.path.exists(waferDir):
            os.makedirs(waferDir, exist_ok=True)
        
        # df_out     = pd.DataFrame(index=f2flist.loc[subdet,layer,_wafer].index)
        # df_out[F2F_headers]     = pd.DataFrame((f2flist.loc[subdet,layer,_wafer]).values.tolist(),index=f2flist.loc[subdet,layer,_wafer].index)
        # df_out[CALQ_headers]   = pd.DataFrame((calQlist.loc[subdet,layer,_wafer]).values.tolist(),index=calQlist.loc[subdet,layer,_wafer].index)
        # df_out.fillna(0,inplace=True)

        if not os.path.exists(f"{waferDir}/EPORTRX_data.csv"):
            writeMode='w'
            header=True
        else:
            writeMode='a'
            header=False

        if not zeroSuppress:
            waferInput = pd.DataFrame(index=df.entry.unique(),columns=EPORTRX_headers)
            waferInput.index.name='entry'
            waferInput[EPORTRX_headers] = df_out.loc[_wafer][EPORTRX_headers]

#            waferInput[EPORTRX_headers] = waferInput[EPORTRX_headers].fillna(0)
            # waferInput[EPORTRX_headers] = waferInput[EPORTRX_headers].fillna("0000000000000000000000000000")
        else:
            waferInput = df_out.loc[_wafer][EPORTRX_headers]
        waferInput.fillna(0,inplace=True)            
        waferInput.astype(int).to_csv(f"{waferDir}/EPORTRX_data.csv",columns=EPORTRX_headers,index='entry', mode=writeMode, header=header)

        simEnergy.loc[_wafer].to_csv(f"{waferDir}/SimEnergyTotal.csv",columns=["SimEnergyTotal","EventSimEnergy"],index='entry', mode=writeMode, header=header)


        isHDM = df[df.wafer==_wafer].head().isHDM.any()

        if not os.path.exists(f"{waferDir}/metaData.py"):
            print("Making Metadata", waferDir)
            with open(f"{waferDir}/metaData.py",'w') as _metaDataFile:
                _metaDataFile.write(f"subdet={subdet}\n")
                _metaDataFile.write(f"layer={layer}\n")
                _metaDataFile.write(f"wafer={_wafer}\n")
                _metaDataFile.write(f"geomVersion='{geomVersion}'\n")
                _metaDataFile.write(f"isHDM={isHDM}\n")
                _metaDataFile.write(f'rootFile="{fileInfo}"')
        
def processNtupleInputs(fName, geomDF, subdet, layer, wafer, odir, nEvents, chunkSize=10000, geomVersion="v9", appendFile=False, jobInfo="", zeroSuppress=False):

    #load tree into uproot
    _tree = uproot.open(fName,xrootdsource=dict(chunkbytes=250*1024**2, limitbytes=250*1024**2))['hgcalTriggerNtuplizer/HGCalTriggerNtuple']

    print(f'loaded tree {fName}')

    if nEvents==-1:
        nEventsTot = _tree.numentries
    else:
        nEventsTot = nEvents
    
    nJobs = int(np.ceil(nEventsTot/chunkSize))
    print(f'{nEventsTot} events in {nJobs} chunks')

    # writeMode='a' if appendFile else 'w'
    # print (writeMode)
    
    numString = ''
    for x in fName.split('.root')[0][::-1]:
        if x.isdigit():
            numString = x+numString
        else:
            break
    jobNumber = 999
    if numString.isdigit():
        jobNumber = int(numString)
        
    print(f'file is job number {jobNumber}')

    for j in range(nJobs):
        _appendFile = appendFile or j>0

        print ('process tree')
        Layer_df =   processTree(_tree,geomDF,subdet,layer,geomVersion=geomVersion,jobNumber=jobNumber,nEvents=min(nEventsTot, chunkSize), nStart=chunkSize*j)

        waferListStart = Layer_df.wafer.unique()

        waferList = []
        if not wafer==[-1]:
            for w in wafer:
                if w in waferListStart:
                    waferList.append(w)
                else:
                    print(f'Wafer {w} not present in data, skipping')
        else:
            waferList = waferListStart
        print ('Writing Inputs')

        writeInputCSV(odir,  Layer_df, subdet,layer,waferList, geomVersion, _appendFile, jobInfo, fileInfo=fName, zeroSuppress=zeroSuppress)

        del Layer_df
        gc.collect()
            
    del _tree
    gc.collect()

    return waferList




def main(opt,args):
    print ('start')

    jobSplitText = ""

    subdet = opt.subdet
    layer = opt.layer

    geomVersion='v11'
    if opt.useV10:
        geomVersion='v10'
    if opt.useV9:
        geomVersion='v9'

    if geomVersion in ['v10','v11']:
        if subdet==3:
            subdet=1
        if subdet==4:
            subdet=2
        if subdet==5:
            subdet=10

    print('loading')


    fileName = opt.inputFile
    fileNameContent = opt.inputFileFormat
    eosDir = opt.eosDir
    print(fileName)
    if fileName is None:
        if fileNameContent is None:
            if geomVersion=='v10':
                fileNameContent='ntuple_ttbar200PU_RelVal_job'
            elif geomVersion=='v9':
                fileNameContent='ntuple_hgcalNtuples_ttbar_200PU'
            else:
                fileNameContent='ntuple_ttbar_ttbar_v11_aged_unbiased_20191101_'
    
        if eosDir is None:
            if geomVersion=='v10':
                eosDir = '/store/user/dnoonan/HGCAL_Concentrator/NewNtuples/v10_Geom'
            elif geomVersion=='v9':
                eosDir = '/store/user/dnoonan/HGCAL_Concentrator/L1THGCal_Ntuples/TTbar'
            else:
                eosDir = '/store/user/lpchgcal/ConcentratorNtuples/L1THGCal_Ntuples/TTbar_v11'
    
        fileList = []
        # get list of files
        cmd = "xrdfs root://cmseos.fnal.gov ls %s"%eosDir
    
        dirContents,stderr = Popen(cmd,shell=True,stdout=PIPE,stderr=PIPE).communicate()
        dirContentsList = dirContents.decode('ascii').split("\n")
        for fName in dirContentsList:
            if fileNameContent in fName:
                fileList.append("root://cmseos.fnal.gov/%s"%(fName))
    else:
        fileList = [fileName]

    startFileNum = 0
    stopFileNum = -1
    jobSplit = opt.jobSplit
    if '/' in jobSplit:
        if not jobSplit=="1/1":
            jobSplitText = f"_{jobSplit.replace('/','of')}"
            totalFiles = len(fileList)
            jobNumber = int(jobSplit.split('/')[0])-1
            nJobs = int(jobSplit.split('/')[1])
            filesPerJob = 1.*totalFiles/nJobs
            startFileNum = int(jobNumber*filesPerJob)
            stopFileNum = int((jobNumber+1)*filesPerJob)
    if not opt.Nfiles==-1:
        stopFileNum = startFileNum + opt.Nfiles
    if stopFileNum in [-1,len(fileList)]:
        stopFileNum=None
    fileList = fileList[startFileNum:stopFileNum]

    if geomVersion in ['v10','v11']:
        geomDF = getGeomDF_V10()
    else:
        geomDF = getGeomDF_V9()

    waferList = []
    print('HERE')
    print(fileList)
    for i,fName in enumerate(fileList):
        print(i, fName)
        wafer = opt.wafer
        print(wafer)
        if wafer is None:
            wafer = []
        if -1 in wafer:
            wafer = [-1]
        if geomVersion in ['v10','v11']:
            if not wafer==[-1]:
                for j in range(len(opt.waferu)):
                    u = opt.waferu[j]
                    v = opt.waferv[j]
                    wafer.append(u*100 + v)
        
        print(wafer)
        _waferList = processNtupleInputs(fName, geomDF, subdet, layer, wafer, opt.odir, opt.Nevents, opt.chunkSize, geomVersion=geomVersion, appendFile=i>0, jobInfo=jobSplitText, zeroSuppress=opt.zeroSuppress)

        waferList = list(set(list(_waferList) + waferList))

    print(waferList)


if __name__=='__main__':
    parser = optparse.OptionParser()
    parser.add_option('-i',"--inputFile", type="string", default = None,dest="inputFile", help="input file name (single file to run on)")
    parser.add_option("--inputFileFormat", type="string", default = None,dest="inputFileFormat", help="input TPG ntuple name format")
    parser.add_option("--eosDir", type="string", default = None,dest="eosDir", help="direcot")
    # parser.add_option('-i',"--inputFile", type="string", default = 'ntuple_hgcalNtuples_ttbar_200PU',dest="inputFile", help="input TPG ntuple name format")
    # parser.add_option("--eosDir", type="string", default = '/store/user/dnoonan/HGCAL_Concentrator/L1THGCal_Ntuples/TTbar',dest="eosDir", help="direcot")

    parser.add_option('-o',"--odir", type="string", default = './',dest="odir", help="output directory")
    parser.add_option('-w',"--wafer"  , type=int, action="append", dest="wafer"  , help="which wafer to write")
    parser.add_option('-u',"--waferu" , type=int, action="append", dest="waferu" , help="which wafer to write")
    parser.add_option('-v',"--waferv" , type=int, action="append", dest="waferv" , help="which wafer to write")
    # parser.add_option('-w',"--wafer" , type=int, default = 31,dest="wafer" , help="which wafer to write")
    # parser.add_option('-u',"--waferu" , type=int, default = 4,dest="waferu" , help="which wafer to write")
    # parser.add_option('-v',"--waferv" , type=int, default = 2,dest="waferv" , help="which wafer to write")
    parser.add_option('-l',"--layer" , type=int, default = 5 ,dest="layer" , help="which layer to write")
    parser.add_option('-d',"--subdet", type=int, default = 3 ,dest="subdet", help="which subdet to write")
    parser.add_option('--Nfiles', type=int, default = 1 ,dest="Nfiles", help="Limit on number of files to read (-1 is all)")
    parser.add_option('--Nevents', type=int, default = -1 ,dest="Nevents", help="Limit on number of events to read per file (-1 is all)")
    parser.add_option('--chunkSize', type=int, default = 100000 ,dest="chunkSize", help="Number of events to load from root file in a single chunk")
    parser.add_option('--jobSplit', type="string", default = "1/1" ,dest="jobSplit", help="Split of the input root files")
    parser.add_option('--zeroSuppress', default = False, action='store_true' ,dest="zeroSuppress", help="Drop lines which are all 0")
    parser.add_option("--v10", default = False, action='store_true',dest="useV10", help="use v10 geometry")
    parser.add_option("--v9", default = False, action='store_true',dest="useV9", help="use v9 geometry")

    (opt, args) = parser.parse_args()

    if opt.wafer is None:
        if opt.waferu is None or opt.waferv is None:
            print('Need to specify at least one wafer to use')
            exit()
        if not len(opt.waferu)==len(opt.waferv):
            print('Need to specify a u and v value for each wafer')
            exit()

    main(opt,args)
