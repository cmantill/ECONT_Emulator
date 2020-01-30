import uproot
import optparse
import os

import pandas as pd
import numpy as np
import time
import matplotlib.pyplot as plt

from encode import encode, decode
from bestchoice import batcher_sort,sort,sorter
from linkAllocation import linksPerLayer, tcPerLink

from format import formatThresholdOutput, formatThresholdTruncatedOutput, splitToWords, formatBestChoiceOutput
encodeList = np.vectorize(encode)


def processTree(_tree,geomDF, subdet,layer):
    #load dataframe
    df = _tree.pandas.df( ['tc_subdet','tc_zside','tc_layer','tc_wafer','tc_cell','tc_uncompressedCharge','tc_compressedCharge','tc_data','tc_mipPt'])
    df.columns = ['subdet','zside','layer','wafer','triggercell','uncompressedCharge','compressedCharge','data','mipPt']


    #remove unwanted layers
#    df = df[(df.subdet==subdet) & (df.layer==layer) & ( df.wafer==wafer)  ]
    df = df[(df.subdet==subdet) & (df.layer==layer)   ]

    #set index
    df.set_index(['subdet','zside','layer','wafer','triggercell'],append=True,inplace=True)
    df.reset_index('subentry',drop=True,inplace=True)
    df.sort_index(inplace=True)

    #split +/- zside into separate entries
    df.reset_index(inplace=True)
    maxN = df.entry.max()
    df.set_index(['zside'],inplace=True)

    df.loc[-1,['entry']] = df.loc[-1,['entry']] + maxN+1
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
    roundBits = True
   
    df['encodedCharge'] = np.where(df.isHDM,
                                   df.uncompressedCharge.apply(encode,args=(nDropHDM,nExp,nMant,roundBits,True)),
                                   df.uncompressedCharge.apply(encode,args=(nDropLDM,nExp,nMant,roundBits,True)))
    df['decodedCharge'] = np.where(df.isHDM,
                                   df.encodedCharge.apply(decode,args=(nDropHDM,nExp,nMant)),
                                   df.encodedCharge.apply(decode,args=(nDropLDM,nExp,nMant)))
    
    
    #df.decodedCharge.fillna(0,inplace=True)
    df['calibCharge'] = (df.decodedCharge * df.corrFactor_finite)#.round().astype(np.int)

    #threshold ADC is threshold in transverse charge
    df['pass_135'] = df.decodedCharge>(df.threshold_ADC/df.corrFactor)

    return df.reset_index()


def getGeomDF():
    geomName = "root://cmseos.fnal.gov//store/user/dnoonan/HGCAL_Concentrator/triggerGeomV9.root"
    geomTree = uproot.open(geomName,xrootdsource=dict(chunkbytes=1024**3, limitbytes=1024**3))["hgcaltriggergeomtester/TreeTriggerCells"]
    
    tcmapCSVname = 'TC_ELINK_MAP.csv'
    df_tcmap = pd.read_csv(tcmapCSVname)
    
    geomDF = geomTree.pandas.df(['subdet','zside','layer','wafer','triggercell','x','y','z','c_n'])
    geomDF['r'] = (geomDF['x']**2 + geomDF['y']**2)**.5
    geomDF['eta'] = np.arcsinh(geomDF.z/geomDF.r)
    geomDF.set_index(['subdet','zside','layer','wafer','triggercell'],inplace=True)
    geomDF['isHDM'] = geomDF.c_n>4
    geomDF.sort_index(inplace=True)
    geomDF.drop(['x','y','c_n'],axis=1,inplace=True)
    
    #### Need to update layer list in geomdf for subdet 4 and 5 to match df
    geomDF.reset_index(inplace=True)
    geomDF.loc[geomDF.subdet==4,'layer'] += 28
    geomDF.loc[geomDF.subdet==5,'layer'] += 28
    geomDF.set_index(['subdet','zside','layer','wafer','triggercell'],inplace=True)
    
    threshold_mipPt = 1.35
    fCtoADC = 100./1024.
    geomDF['threshold_fC'] = threshold_mipPt* 3.43      ## threshold on transverse charge
    geomDF['threshold_ADC'] = np.round(geomDF.threshold_fC/fCtoADC).astype(np.int)
    precision = 2**-11
    geomDF['corrFactor_finite']    = round(1./np.cosh(geomDF.eta) / precision) * precision
    return geomDF

def makeAddMAP(tclist):
    #tclist = group of tc >threshold in each wafer
    addmap=np.zeros(48, dtype=int)    #zeros 
    addmap[np.array(list(tclist))]=1  #Mark 1 if tc is present
    return addmap
def makeCHARGEQ(qlist):
    #qlist = group of charges in each wafer
    charges = np.array(list(qlist))     
    return np.pad(charges,(0,48-len(charges)),mode='constant',constant_values=0)

def makeTCindexCols(group,col,iMOD=-1):
    charges=np.zeros(48, dtype=float)    #zeros
    tclist = np.array(list(group['triggercell']))  #indexes of tc
    qlist  = np.array(list(group[col]))            #cols for each tc
    charges[tclist] = qlist                       #assign charges in positions
    if iMOD==-1:
        return list(charges.round().astype(np.int))
    modsum = 0
    if iMOD==0:   modsum = charges[0:16].sum().round().astype(np.int)
    elif iMOD==1: modsum = charges[16:32].sum().round().astype(np.int)
    elif iMOD==2: modsum = charges[32:48].sum().round().astype(np.int)                                             
    return modsum


### the Threshold algo block from CSV inputs
def writeThresAlgoBlock(d_csv):

    df = pd.read_csv(d_csv['calQ_csv'])
    df_thres = pd.read_csv(d_csv['thres_csv'],header=None)       ## CSV with 1 entry: decodedCharge thresholds of 48 triggercells
    
    df_passThres = pd.DataFrame(index = df.index,columns = df.columns)

    #threshold calibCharge = threshold 
    #default thresholds to high, set ones present in csv to correct values
    calib_thres = np.ones(48,np.int32)*1e9
    calib_thres[df_thres.loc[0].tolist()] = df_thres.loc[1].tolist()
#    calib_thres  = np.array(df_thres.loc[0].tolist()) 
    

    #Filter all 48 columns
    for i in range(0,48):
        df_passThres['CALQ_%i'%i] = df[df['CALQ_%i'%i]> calib_thres[i] ]['CALQ_%i'%i]

    df_out       = pd.DataFrame(index = df.index)
    ADD_headers     = ["ADDRMAP_%s"%i for i in range(0,48)]
    CHARGEQ_headers = ["CHARGEQ_%s"%i for i in range(0,48)]

    df_out['NTCQ'] = df_passThres.count(axis=1)         #df_passThres has NAN for TC below threshold
    df_out['SUM']  = df.sum(axis=1).round().astype(np.int)                     #Sum over all charges regardless of threshold
    df_out['MOD_SUM_0']  = df[['CALQ_%i'%i for i in range(0,16)] ].sum(axis=1).round().astype(np.int)      #Sum over all charges of 0-16 TC regardless of threshold
    df_out['MOD_SUM_1']  = df[['CALQ_%i'%i for i in range(16,32)]].sum(axis=1).round().astype(np.int)      #Sum over all charges of 16-32 TC regardless of threshold
    df_out['MOD_SUM_2']  = df[['CALQ_%i'%i for i in range(32,48)]].sum(axis=1).round().astype(np.int)      #Sum over all charges of 32-48 TC regardless of threshold

    def makeCHARGEQ(row):
        nExp = 4
        nMant = 3
        roundBits = True
        nDropBit = 1 ## TODO: make this configurable
        asInt  = True

        raw_charges     = np.array(row.dropna()).astype(int)
        encoded_charges = encodeList(raw_charges,nDropBit,nExp,nMant,roundBits,asInt=True)
        return np.pad(encoded_charges,(0,48-len(encoded_charges)),mode='constant',constant_values=0)

    ## boolean list of 48 TC cells (filled 0 in df_passThres first)
    tclist                   = df_passThres.fillna(0).apply(lambda x: np.array(x>0).astype(int),axis=1)
    ## calibCharge list of passing TC cells, padding zeros after list 

    qlist                  = df_passThres.apply(makeCHARGEQ,axis=1)
    df_out[CHARGEQ_headers] = pd.DataFrame(qlist.values.tolist(),index=qlist.index,columns=CHARGEQ_headers)
    df_out[ADD_headers]     = pd.DataFrame(tclist.values.tolist(),index=tclist.index,columns=ADD_headers)

    ## output to CSV
    cols = np.array(df_out.columns.tolist())
    WAFER = np.logical_and(~np.in1d(cols,ADD_headers),~np.in1d(cols,CHARGEQ_headers))
    df_out.to_csv(d_csv['thres_charge_csv' ],columns=CHARGEQ_headers,index=False)
    df_out.to_csv(d_csv['thres_address_csv'],columns=ADD_headers,index=False)
    df_out.to_csv(d_csv['thres_wafer_csv'  ],columns=WAFER,index=False)


    return df_out


def writeInputCSV(odir,df,geomDF,subdet,layer,wafer):
    #output of switch matrix ( i.e. decoded charge)
    SM_headers = ["SM_%s"%i for i in range(0,48)]
    #output of Calibration ( i.e. calib charge)
    CALQ_headers = ["CALQ_%s"%i for i in range(0,48)]

    gb = df.groupby(['entry','subdet','layer','wafer'],group_keys=False)

    smlist   = gb[['triggercell','decodedCharge']].apply(makeTCindexCols,'decodedCharge',-1)
    calQlist = gb[['triggercell','calibCharge']].apply(makeTCindexCols,'calibCharge',-1)

    df_out     = pd.DataFrame(index=smlist.index)
    df_out[SM_headers]     = pd.DataFrame((smlist).values.tolist(),index=smlist.index)
    df_out[CALQ_headers]   = pd.DataFrame((calQlist).values.tolist(),index=calQlist.index)
    df_out.fillna(0,inplace=True)
    df_out.to_csv("%s/SM_output.csv"%odir  ,columns=SM_headers,index=False)
    df_out.to_csv("%s/CALQ_output.csv"%odir,columns=CALQ_headers,index=False)

    ## write subsidary files
    df_geom = geomDF.reset_index()
    df_geom = df_geom[(df_geom.subdet==subdet) & (df_geom.layer==layer) & ( df_geom.wafer==wafer) & (df_geom.zside==1) ]
    df_geom = df_geom.reset_index(drop=True)
    precision  = 2**-11
    df_geom['corrFactor_finite']    = round(1./np.cosh(df_geom.eta) / precision) * precision
    df_geom[['triggercell','corrFactor_finite']].transpose().to_csv("%s/calib_D%sL%sW%s.csv"%(odir,subdet,layer,wafer),index=False,header=None)
    df_geom[['triggercell','threshold_ADC']].transpose().to_csv("%s/thres_D%sL%sW%s.csv"%(odir,subdet,layer,wafer),index=False,header=None)

    return

def writeThresholdFormat(d_csv):
    df_wafer  = pd.read_csv(d_csv['wafer_csv'])
    df_addmap = pd.read_csv(d_csv['add_csv'])
    df_charge = pd.read_csv(d_csv['charge_csv'])
    
    df_wafer['CHARGEQ'] = df_charge.apply(list,axis=1)
    df_wafer['ADD_MAP'] = df_addmap.apply(list,axis=1)
   
    debug = False
    nDropbit = 1        ## TODO: make this configurable

    if not debug: 
        cols = [f'WORD_{i}' for i in range(25)]
        df_wafer['FRAMEQ'] = df_wafer.apply(formatThresholdOutput,args=(debug),axis=1)
        df_wafer['FRAMEQ_TRUNC'] = df_wafer.apply(formatThresholdTruncatedOutput,axis=1)
        df_wafer[cols] = pd.DataFrame(df_wafer.apply(splitToWords,axis=1).tolist(),columns=cols)
        df_wafer['WORDCOUNT'] = (df_wafer.FRAMEQ.str.len()/16).astype(int)
    else:
        bit_str = df_wafer.apply(formatThresholdOutput,args=(nDropbit,debug),axis=1)
        cols          = ['header', 'dataType' , 'modSumData' ,'extraBit' ,'nChannelData' , 'AddressMapData' ,'ChargeData']
        df_wafer[cols] = pd.DataFrame(bit_str.values.tolist(), index=bit_str.index)
#    df_wafer.to_csv(d_csv['format_csv'],columns=['FRAMEQ','FRAMEQ_TRUNC'],index=False)
    df_wafer.to_csv(d_csv['format_csv'],columns=['FRAMEQ','FRAMEQ_TRUNC','WORDCOUNT']+cols,index=False)
    return

def writeBestChoice(d_csv):
    df_in = pd.read_csv(d_csv['calQ_csv'])
    df_sorted, _ = sort(df_in)
    df_sorted_index = pd.DataFrame(df_in.apply(batcher_sort, axis=1))
    df_sorted.columns = ['BC_Charge_{}'.format(i) for i in range(0, df_sorted.shape[1])]
    df_sorted.index.name = 'BC'
    df_sorted_index.columns = ['BC_Address_{}'.format(i) for i in range(0, df_sorted_index.shape[1])]
    df_sorted_index.index.name = 'BC'
    df_sorted.to_csv(d_csv['bc_charge_csv'],index=False)
    df_sorted_index.to_csv(d_csv['bc_address_csv'],index=False)

    df_sorted[df_sorted_index.columns] = df_sorted_index

    df_sorted['FRAMEQ'] = df_sorted.apply(formatBestChoiceOutput, args=(d_csv['nTC'],d_csv['isHDM']), axis=1)
    df_sorted['WORDCOUNT'] = (df_sorted.FRAMEQ.str.len()/16).astype(int)
    cols = [f'WORD_{i}' for i in range(25)]
    df_sorted[cols] = pd.DataFrame(df_sorted.apply(splitToWords,axis=1).tolist(),columns=cols)

    df_sorted.to_csv(d_csv['bc_format_csv'],columns=['FRAMEQ','WORDCOUNT']+cols,index=False)    

    return
    

def main(opt,args):
    print('loading')

    #fName='ntuple_bc.root'

    #_tree = uproot.open(fName,xrootdsource=dict(chunkbytes=1024**3, limitbytes=1024**3))['Floatingpoint8Threshold0DummyHistomaxGenmatchGenclustersntuple/HGCalTriggerNtuple']
    #_tree_tsgbc = uproot.open(fName,xrootdsource=dict(chunkbytes=1024**3, limitbytes=1024**3))['Floatingpoint8BestchoiceDummyHistomaxGenmatchGenclustersntuple/HGCalTriggerNtuple']
    
    fName = 'root://cmseos.fnal.gov//store/user/dnoonan/HGCAL_Concentrator/L1THGCal_Ntuples/TTbar/ntuple_hgcalNtuples_ttbar_200PU_0.root'

    _tree = uproot.open(fName,xrootdsource=dict(chunkbytes=1024**3, limitbytes=1024**3))['hgcalTriggerNtuplizer/HGCalTriggerNtuple']

    print('loaded tree')

    ####Selection of a single wafer
    subdet = opt.subdet  
    layer  = opt.layer   

    print ('start')
    geomDF          =   getGeomDF()
    print ('process tree')
    Layer_df =   processTree(_tree,geomDF,subdet,layer)
    waferList = Layer_df.wafer.unique()
    if not opt.wafer==-1:
        waferList = [opt.wafer]
    for wafer in waferList:
        if opt.odir=='./':
            odir = 'wafer_D%iL%iW%i/'%(subdet,layer,wafer) 
        else:
            odir = '%s/wafer_D%iL%iW%i/'%(opt.odir,subdet,layer,wafer) 
        os.makedirs(odir, exist_ok=True)
#            odir = opt.odir
#        if not os.path.exists(odir):

        customCharge_df = Layer_df[Layer_df.wafer==wafer].set_index(['entry','subdet','layer','wafer'])
        print (f'loaded wafer {wafer}')
        writeInputCSV( odir,  customCharge_df, geomDF, subdet,layer,wafer)
        threshold_inputcsv ={
            'calQ_csv'         :odir+'CALQ_output.csv', #input
            'thres_csv'        :odir+'thres_D%iL%iW%i.csv'%(subdet,layer,wafer), #input threshold
            'thres_charge_csv' :odir+'threshold_charge.csv',   #output
            'thres_address_csv':odir+'threshold_address.csv',  #output
            'thres_wafer_csv'  :odir+'threshold_wafer.csv',  #output
        }
        df_algo         =   writeThresAlgoBlock(threshold_inputcsv)
        bc_inputcsv ={
            'calQ_csv'      :odir+'CALQ_output.csv', #input
            'bc_charge_csv' :odir+'bc_charge.csv',   #output
            'bc_address_csv':odir+'bc_address.csv',  #output
            'bc_format_csv':odir+'bc_formatblock.csv',  #output
            'nTC': tcPerLink[linksPerLayer[layer]],
            'isHDM':customCharge_df.isHDM.any(),
        }
        writeBestChoice(bc_inputcsv)
        format_inputcsv ={
            'wafer_csv' :odir+'threshold_wafer.csv',        #input
            'add_csv'   :odir+'threshold_address.csv',      #input
            'charge_csv':odir+'threshold_charge.csv',       #input
            'format_csv':odir+'threshold_formatblock.csv'   #output
        }
        writeThresholdFormat(format_inputcsv)
    

if __name__=='__main__':
    parser = optparse.OptionParser()
    parser.add_option('-i',"--inputFile", type="string", default = 'ntuple.root',dest="inputFile", help="input TSG ntuple")
    parser.add_option('-o',"--odir", type="string", default = './',dest="odir", help="output directory")
    parser.add_option('-w',"--wafer" , type=int, default = -1,dest="wafer" , help="which wafer to write")
    parser.add_option('-l',"--layer" , type=int, default = 5 ,dest="layer" , help="which layer to write")
    parser.add_option('-d',"--subdet", type=int, default = 3 ,dest="subdet", help="which subdet to write")

    (opt, args) = parser.parse_args()

    main(opt,args)
