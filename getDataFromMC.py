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

def processTree(_tree, geomDF, subdet, layer, geomVersion="v9", jobNumber=0, nEvents=-1, nStart=-1):

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
        df = _tree.pandas.df( ['tc_subdet','tc_zside','tc_layer','tc_waferu','tc_waferv','tc_cellu','tc_cellv','tc_uncompressedCharge','tc_compressedCharge','tc_data','tc_mipPt'],entrystart=nStart,entrystop=nStop)
        df.columns = ['subdet','zside','layer','waferu','waferv','triggercellu','triggercellv','uncompressedCharge','compressedCharge','data','mipPt']

    else:
        df = _tree.pandas.df( ['tc_subdet','tc_zside','tc_layer','tc_wafer','tc_cell','tc_uncompressedCharge','tc_compressedCharge','tc_data','tc_mipPt'],entrystart=nStart,entrystop=nStop)
        df.columns = ['subdet','zside','layer','wafer','triggercell','uncompressedCharge','compressedCharge','data','mipPt']
    df.reset_index('subentry',drop=True,inplace=True)

    #remove unwanted layers
    df = df[(df.subdet==subdet) & (df.layer==layer)]

    if geomVersion in ['v10','v11']:
        df['wafer'] = 100*df.waferu + df.waferv
        df['UV'] = list(zip(df.triggercellu, df.triggercellv))
        df['triggercell'] = df.UV.map(triggerCellUVRemap)

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



def writeInputCSV(odir,df,subdet,layer,waferList,geomVersion,appendFile=False,jobInfo="",fileInfo=""):
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

    df_out     = pd.DataFrame(index=encodedlist.index)
    df_out[ENCODED_headers]= pd.DataFrame((encodedlist).values.tolist(),index=encodedlist.index)

    df_out.fillna(0,inplace=True)

    df_out[EPORTRX_headers] = pd.DataFrame(df_out.apply(packIntoInputLinks,axis=1).tolist(),columns=EPORTRX_headers,index=encodedlist.index)

    for _wafer in waferList:
        if geomVersion in ['v10','v11']:
            waferu = int(round(_wafer/100))
            waferv = int(_wafer-100*waferu)

            if odir=='./':
                waferDir = f'wafer_D{subdet}L{layer}U{waferu}V{waferv}/'
            else:
                waferDir = f'{odir}/wafer_D{subdet}L{layer}U{waferu}V{waferv}/'
        else:
            if odir=='./':
                waferDir = f'wafer_D{subdet}L{layer}W{_wafer}/'
            else:
                waferDir = f'{odir}/wafer_D{subdet}L{layer}W{_wafer}/'

        if not os.path.exists(waferDir):
            os.makedirs(waferDir, exist_ok=True)
        
        # df_out     = pd.DataFrame(index=f2flist.loc[subdet,layer,_wafer].index)
        # df_out[F2F_headers]     = pd.DataFrame((f2flist.loc[subdet,layer,_wafer]).values.tolist(),index=f2flist.loc[subdet,layer,_wafer].index)
        # df_out[CALQ_headers]   = pd.DataFrame((calQlist.loc[subdet,layer,_wafer]).values.tolist(),index=calQlist.loc[subdet,layer,_wafer].index)
        # df_out.fillna(0,inplace=True)
        
        waferInput = pd.DataFrame(index=df.entry.unique(),columns=EPORTRX_headers)
        waferInput.index.name='entry'
        waferInput[EPORTRX_headers] = df_out.loc[_wafer][EPORTRX_headers]
        
        waferInput[EPORTRX_headers] = waferInput[EPORTRX_headers].fillna("0000000000000000000000000000")
        waferInput.fillna(0,inplace=True)

        waferInput.to_csv(f"{waferDir}/EPORTRX_output{jobInfo}.csv",columns=EPORTRX_headers,index='entry', mode=writeMode, header=header)

        isHDM = df[df.wafer==_wafer].head().isHDM.any()

#        print(df.columns)

        if not appendFile:
            with open(f"{waferDir}/metaData.py",'w') as _metaDataFile:
                _metaDataFile.write(f"subdet={subdet}\n")
                _metaDataFile.write(f"layer={layer}\n")
                _metaDataFile.write(f"wafer={_wafer}\n")
                _metaDataFile.write(f"geomVersion='{geomVersion}'\n")
                _metaDataFile.write(f"isHDM={isHDM}\n")
                _metaDataFile.write(f'rootFile="{fileInfo}"')
                
        
def processNtupleInputs(fName, geomDF, subdet, layer, wafer, odir, nEvents, chunkSize=10000, geomVersion="v9", appendFile=False, jobInfo=""):

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
        Layer_df =   processTree(_tree,geomDF,subdet,layer,geomVersion,jobNumber,nEvents=min(nEventsTot, chunkSize), nStart=chunkSize*j)

        waferList = Layer_df.wafer.unique()

        if not wafer==-1:
            waferList = [wafer]
        print ('Writing Inputs')

        writeInputCSV(odir,  Layer_df, subdet,layer,waferList, geomVersion, _appendFile, jobInfo, fileInfo=fName)

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

    if opt.useV10 or opt.useV11:
        if subdet==3:
            subdet=1
        if subdet==4:
            subdet=2
        if subdet==5:
            subdet=10

    print('loading')


    fileNameContent = opt.inputFile
    eosDir = opt.eosDir

    if fileNameContent is None:
        if opt.useV10:
            fileNameContent='ntuple_ttbar200PU_RelVal_job'
        elif opt.useV11:
            fileNameContent='ntuple_ttbar_ttbar_v11_aged_unbiased_20191101_'
        else:
            fileNameContent='ntuple_hgcalNtuples_ttbar_200PU'
    if eosDir is None:
        if opt.useV10:
            eosDir = '/store/user/dnoonan/HGCAL_Concentrator/NewNtuples/v10_Geom'
        elif opt.useV11:
            eosDir = '/store/user/lpchgcal/ConcentratorNtuples/L1THGCal_Ntuples/TTbar_v11'
        else:
            eosDir = '/store/user/dnoonan/HGCAL_Concentrator/L1THGCal_Ntuples/TTbar'

    fileList = []
    # get list of files
    cmd = "xrdfs root://cmseos.fnal.gov ls %s"%eosDir

    dirContents,stderr = Popen(cmd,shell=True,stdout=PIPE,stderr=PIPE).communicate()
    dirContentsList = dirContents.decode('ascii').split("\n")
    for fName in dirContentsList:
        if fileNameContent in fName:
            fileList.append("root://cmseos.fnal.gov/%s"%(fName))

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
    fileList = fileList[startFileNum:stopFileNum]


    if opt.useV10 or opt.useV11:
        geomVersion="v10"
        if opt.useV11:
            geomVersion="v11"
        geomDF = getGeomDF_V10()
    else:
        geomVersion="v9"
        geomDF = getGeomDF_V9()

    for i,fName in enumerate(fileList):
        print(i, fName)
        wafer = opt.wafer
        if opt.useV10 or opt.useV11:
            if not wafer==-1:
                wafer = opt.waferu*100 + opt.waferv
        waferList = processNtupleInputs(fName, geomDF, subdet, layer, wafer, opt.odir, opt.Nevents, opt.chunkSize, geomVersion=geomVersion, appendFile=i>0, jobInfo=jobSplitText)
    print(waferList)


if __name__=='__main__':
    parser = optparse.OptionParser()
    parser.add_option('-i',"--inputFile", type="string", default = None,dest="inputFile", help="input TPG ntuple name format")
    parser.add_option("--eosDir", type="string", default = None,dest="eosDir", help="direcot")
    # parser.add_option('-i',"--inputFile", type="string", default = 'ntuple_hgcalNtuples_ttbar_200PU',dest="inputFile", help="input TPG ntuple name format")
    # parser.add_option("--eosDir", type="string", default = '/store/user/dnoonan/HGCAL_Concentrator/L1THGCal_Ntuples/TTbar',dest="eosDir", help="direcot")

    parser.add_option('-o',"--odir", type="string", default = './',dest="odir", help="output directory")
    parser.add_option('-w',"--wafer" , type=int, default = 31,dest="wafer" , help="which wafer to write")
    parser.add_option('-u',"--waferu" , type=int, default = 4,dest="waferu" , help="which wafer to write")
    parser.add_option('-v',"--waferv" , type=int, default = 2,dest="waferv" , help="which wafer to write")
    parser.add_option('-l',"--layer" , type=int, default = 5 ,dest="layer" , help="which layer to write")
    parser.add_option('-d',"--subdet", type=int, default = 3 ,dest="subdet", help="which subdet to write")
    parser.add_option('--Nfiles', type=int, default = 1 ,dest="Nfiles", help="Limit on number of files to read (-1 is all)")
    parser.add_option('--Nevents', type=int, default = 50 ,dest="Nevents", help="Limit on number of events to read per file (-1 is all)")
    parser.add_option('--chunkSize', type=int, default = 100000 ,dest="chunkSize", help="Number of events to load from root file in a single chunk")
    parser.add_option('--jobSplit', type="string", default = "1/1" ,dest="jobSplit", help="Split of the input root files")
    parser.add_option("--v10", default = False, action='store_true',dest="useV10", help="use v10 geometry")
    parser.add_option("--v11", default = False, action='store_true',dest="useV11", help="use v11 geometry")

    (opt, args) = parser.parse_args()

    main(opt,args)
