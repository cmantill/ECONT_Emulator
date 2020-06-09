import uproot

import pandas as pd
import numpy as np

def getGeomDF_V9():
    geomName = "root://cmseos.fnal.gov//store/user/dnoonan/HGCAL_Concentrator/triggerGeomV9.root"
    geomTree = uproot.open(geomName,xrootdsource=dict(chunkbytes=250*1024**2, limitbytes=250*1024**2))["hgcaltriggergeomtester/TreeTriggerCells"]
    
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


triggerCellUVRemap = {(7,4):0,
                      (6,4):1,
                      (5,4):2,
                      (4,4):3,
                      (7,5):4,
                      (6,5):5,
                      (5,5):6,
                      (4,5):7,
                      (7,6):8,
                      (6,6):9,
                      (5,6):10,
                      (4,6):11,
                      (7,7):12,
                      (6,7):13,
                      (5,7):14,
                      (4,7):15,
                      (1,0):16,
                      (2,1):17,
                      (3,2):18,
                      (4,3):19,
                      (2,0):20,
                      (3,1):21,
                      (4,2):22,
                      (5,3):23,
                      (3,0):24,
                      (4,1):25,
                      (5,2):26,
                      (6,3):27,
                      (4,0):28,
                      (5,1):29,
                      (6,2):30,
                      (7,3):31,
                      (3,6):32,
                      (3,5):33,
                      (3,4):34,
                      (3,3):35,
                      (2,5):36,
                      (2,4):37,
                      (2,3):38,
                      (2,2):39,
                      (1,4):40,
                      (1,3):41,
                      (1,2):42,
                      (1,1):43,
                      (0,3):44,
                      (0,2):45,
                      (0,1):46,
                      (0,0):47,
}

def remapTriggerCellNumbers(x):
    return triggerRemap[(x[0],x[1])]

def getGeomDF_V10():
    geomName = "root://cmseos.fnal.gov//store/user/dnoonan/HGCAL_Concentrator/triggerGeomV10-2.root"
    geomTree = uproot.open(geomName,xrootdsource=dict(chunkbytes=250*1024**2, limitbytes=250*1024**2))["hgcaltriggergeomtester/TreeTriggerCells"]
    
    tcmapCSVname = 'TC_ELINK_MAP.csv'
    df_tcmap = pd.read_csv(tcmapCSVname)
    
    geomDF = geomTree.pandas.df(['subdet','zside','layer','waferu','waferv','triggercellu','triggercellv','x','y','z','c_n'])
    geomDF['UV'] = list(zip(geomDF.triggercellu, geomDF.triggercellv))

    geomDF['triggercell'] = geomDF.UV.map(triggerCellUVRemap)
    geomDF['wafer'] = 100*geomDF.waferu + geomDF.waferv

    geomDF['r'] = (geomDF['x']**2 + geomDF['y']**2)**.5
    geomDF['eta'] = np.arcsinh(geomDF.z/geomDF.r)
    geomDF.set_index(['subdet','zside','layer','wafer','triggercell'],inplace=True)
    geomDF['isHDM'] = geomDF.c_n>4
    geomDF.sort_index(inplace=True)
    geomDF.drop(['x','y','c_n'],axis=1,inplace=True)

    
    #### Need to update layer list in geomdf for subdet 4 and 5 to match df
    geomDF.reset_index(inplace=True)
    geomDF.loc[geomDF.subdet==2,'layer'] += 28
    geomDF.loc[geomDF.subdet==10,'layer'] += 28
    geomDF = geomDF[geomDF.subdet<10]
    geomDF.set_index(['subdet','zside','layer','wafer','triggercell'],inplace=True)
    
    threshold_mipPt = 1.35
    fCtoADC = 100./1024.
    geomDF['threshold_fC'] = threshold_mipPt* 3.43      ## threshold on transverse charge
    geomDF['threshold_ADC'] = np.round(geomDF.threshold_fC/fCtoADC).astype(np.int)
    precision = 2**-11
    geomDF['corrFactor_finite']    = round(1./np.cosh(geomDF.eta) / precision) * precision
    return geomDF

