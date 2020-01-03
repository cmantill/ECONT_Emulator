import uproot
import optparse

import pandas as pd
import numpy as np
import time
import matplotlib.pyplot as plt

from encode import encode, decode
from bestchoice import batcher_sort
encodeList = np.vectorize(encode)

#### Finite precision correction 
import struct
def binary(num):
    return ''.join('{:0>8b}'.format(c) for c in struct.pack('!f', num))

def binaryToFloat(s):
    ## str of bits -> bytes of hex
    bytes = int(s, 2).to_bytes(len(s) // 8, byteorder='big')
    ## IEEE 754 floating point interpretation 
    return struct.unpack("!f", bytes)[0]

def truncateFloat(float_val, nExp=4,nMant=4):
    b = binary(float_val)         ## IEEE 754 rep. 
    signBit = b[0]
    expBits = b[1:9]
    mantBits = b[9:32]
    exp_truc = expBits[:nExp]+'0'*(8-nExp)      ## zero out extra bits 
    man_truc = mantBits[:nMant]+'0'*(23-nMant)  ## zero out extra bits
    b_truc   = signBit+exp_truc+man_truc
    #print ('expbits=     ',expBits, '\nexpbits_truc=',exp_truc)
    #print ('mantbits      =',mantBits, '\nmantBits_trunc=',mantBits[:nMant]+'0'*(23-nMant))
    #print(binaryToFloat(b))
    return (binaryToFloat(b_truc))

truncateFloatList = np.vectorize(truncateFloat)

##########################################


def processTree(_tree,geomDF, subdet,layer,wafer):
    #load dataframe
    df = _tree.pandas.df( ['tc_subdet','tc_zside','tc_layer','tc_wafer','tc_cell','tc_uncompressedCharge','tc_compressedCharge','tc_data','tc_mipPt'])
    df.columns = ['subdet','zside','layer','wafer','triggercell','uncompressedCharge','compressedCharge','data','mipPt']


    #remove unwanted layers
    df = df[(df.subdet==subdet) & (df.layer==layer) ]

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
    df['corrFactor_finite']    = truncateFloatList(1./np.cosh(df.eta),8,4)
    #df['threshold_ADC_int'] = geomDF['threshold_ADC_int']

    df.reset_index(inplace=True)
    #df.set_index(['entry','subdet','layer','wafer','triggercell'],inplace=True)
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

    df['pass_135'] = df.decodedCharge>df.threshold_ADC

    return df


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
    geomDF['threshold_fC'] = threshold_mipPt*np.cosh(geomDF.eta) *3.43
    geomDF['threshold_ADC'] = np.round(geomDF.threshold_fC/fCtoADC).astype(np.int)
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

def modsum(group,iMOD=0):
    charges=np.zeros(48, dtype=float)    #zeros
    tclist = np.array(list(group['triggercell']))  #indexes of tc
    qlist  = np.array(list(group['calibCharge']))  #charges of tc
    charges[tclist] = qlist                       #assign charges in positions
    modsum = 0
    if iMOD==0:   modsum = charges[0:16].sum().round().astype(np.int)
    elif iMOD==1: modsum = charges[16:32].sum().round().astype(np.int)
    elif iMOD==2: modsum = charges[32:48].sum().round().astype(np.int)                                             
    return modsum

def getAlgoBlockOutputDF(df):
    sumEncoding=(0,5,3) 
    tcEncoding=(0,4,4)

    df_thres = df[df.pass_135==True]
    
    gb = df.groupby(['entry','subdet','layer','wafer'],group_keys=False)
    gb_thres = df_thres.groupby(['entry','subdet','layer','wafer'],group_keys=False)
    
    ADD_headers = ["ADDMAP_%s"%i for i in range(0,48)]
    CHARGEQ_headers = ["CHARGEQ_%s"%i for i in range(0,48)]
    
    
    df_out = pd.DataFrame(gb.sum()['calibCharge'].round().astype(np.int))
    df_out.rename(columns={"calibCharge":"SUM"},inplace=True)
    
    df_out['NTCQ'] = gb_thres.count()['pass_135']

    tclist = pd.DataFrame(gb_thres['triggercell'].apply(makeAddMAP))
    qlist  = pd.DataFrame(gb_thres['calibCharge'].apply(makeCHARGEQ))
    df_out[ADD_headers]     = pd.DataFrame((tclist)['triggercell'].values.tolist(),index=tclist.index)
    df_out[CHARGEQ_headers] = pd.DataFrame((qlist)['calibCharge'].values.tolist(),index=qlist.index)
    df_out['MOD_SUM_0']     =pd.DataFrame(gb[['triggercell','calibCharge']].apply(modsum,0))
    df_out['MOD_SUM_1']     =pd.DataFrame(gb[['triggercell','calibCharge']].apply(modsum,1))    
    df_out['MOD_SUM_2']     =pd.DataFrame(gb[['triggercell','calibCharge']].apply(modsum,2))   

    df_out.fillna(0,inplace=True)        ## fill 0 for entries without any TC passing threshold 

    return df_out

def main(args):

    fName='ntuple_bc.root'

    _tree = uproot.open(fName,xrootdsource=dict(chunkbytes=1024**3, limitbytes=1024**3))['Floatingpoint8Threshold0DummyHistomaxGenmatchGenclustersntuple/HGCalTriggerNtuple']
    #_tree_tsgbc = uproot.open(fName,xrootdsource=dict(chunkbytes=1024**3, limitbytes=1024**3))['Floatingpoint8BestchoiceDummyHistomaxGenmatchGenclustersntuple/HGCalTriggerNtuple']

    ####Selection of a single wafer
    subdet = 3
    layer  = 5
    wafer  = 31

    geomDF          =   getGeomDF()
    customCharge_df =   processTree(_tree,geomDF,subdet,layer,wafer)
    df_algo         =   getAlgoBlockOutputDF(customCharge_df)

    ADD = ["ADDMAP_%s"%i for i in range(0,48)]
    CHARGEQ = ["CHARGEQ_%s"%i for i in range(0,48)]
    cols = np.array(df_algo.columns.tolist())
    OTHERS = np.logical_and(~np.in1d(cols,ADD),~np.in1d(cols,CHARGEQ))
    
    df_algo.to_csv('Algo_AddMap.csv',columns=ADD,index=False)
    df_algo.to_csv('Algo_ChargeQ.csv',columns=CHARGEQ,index=False)
    df_algo.to_csv('Algo_OTHERS.csv',columns=OTHERS,index=False)

if __name__=='__main__':
    parser = optparse.OptionParser()
    parser.add_option("--input", type="string", dest="input_file", help="input pattern file")
    parser.add_option("--output_charge", type="string", dest="output_charge_file", help="output charges file")
    parser.add_option("--output_address", type="string", dest="output_address_file", help="output address file")
    (opt, args) = parser.parse_args()

    main(args)
