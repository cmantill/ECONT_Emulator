import pandas as pd
import numpy as np

from Utils.encode import decode
decodeV = np.vectorize(decode)

import pickle

def getMuxRegisters(tpgNtupleMapping=False, MuxRegisters=None):
    if not MuxRegisters is None:
        if 'passThrough' in MuxRegisters:
            return np.arange(48)
        if '.csv' in MuxRegisters:
            mux = pd.read_csv(MuxRegisters)
            return mux.values[0]
        if type(MuxRegisters) is np.ndarray:
            return MuxRegisters
        if type(MuxRegisters) is list:
            return np.array(MuxRegisters)

    tc_remap = pd.read_csv("Utils/LDM_TC_Mapping.csv")[['TC_Number','ECON_TC_Number_PostMux','ECON_TC_Number_PreMux']]
    
    muxRegisters = tc_remap[['ECON_TC_Number_PostMux','ECON_TC_Number_PreMux']].values
    if tpgNtupleMapping:
        muxRegisters = tc_remap[['TC_Number','ECON_TC_Number_PreMux']].values
    
    x = muxRegisters.tolist()
    x.sort()
    muxRegisters = np.array(x)
    return muxRegisters[:,1]

def Mux(df_Mux_in, Mux_registers):

    Mux_in_headers_ordered = [f'Mux_in_{i}' for i in Mux_registers]
    
    df_Mux_out = df_Mux_in[Mux_in_headers_ordered]
    
    df_Mux_out.columns = [f'Mux_out_{i}' for i in range(48)]
    return df_Mux_out



def FloatToFix(df_Mux_out, isHDM):
    df_F2F = pd.DataFrame(decodeV(df_Mux_out,3 if isHDM else 1),columns=[f'F2F_{i}' for i in range(48)],index=df_Mux_out.index)
    return df_F2F

def getCalibrationRegisters_Thresholds(subdet, layer, wafer, geomVersion, tpgNtupleMapping=False, CalRegisters=None, ThresholdRegisters=None):
    
    if geomVersion in ['v10','v11']:
        geomDF = pd.read_csv('Utils/geomDF_v10.csv', index_col=[0,1,2,3]).loc[subdet,layer,wafer]
    else:
        geomDF = pd.read_csv('Utils/geomDF_v9.csv', index_col=[0,1,2,3]).loc[subdet,layer,wafer]

    if len(geomDF)<48:
        newGeomDF = pd.DataFrame({'corrFactor_finite':[0]*48,'threshold_ADC':[0]*48,'triggercell':np.arange(48)})
        newGeomDF.set_index('triggercell',inplace=True)
        newGeomDF['corrFactor_finite'] = geomDF['corrFactor_finite']
        newGeomDF['threshold_ADC'] = geomDF['threshold_ADC']
        geomDF = newGeomDF.fillna(0)

    calibVal, threshVal =  np.round((geomDF.corrFactor_finite*2**11).values).astype(int), geomDF.threshold_ADC.values

    if tpgNtupleMapping:
        return calibVal, threshVal

    tc_remap = pd.read_csv("Utils/LDM_TC_Mapping.csv")[['TC_Number','ECON_TC_Number_PostMux','ECON_TC_Number_PreMux']]
    muxRegisters = tc_remap[['TC_Number','ECON_TC_Number_PostMux']].values

    remappedCalibVal = np.zeros(48,dtype=int)
    remappedThreshVal = np.zeros(48,dtype=int)

    for x in muxRegisters:
        remappedCalibVal[x[1]] = calibVal[x[0]]
        remappedThreshVal[x[1]] = threshVal[x[0]]

    if not CalRegisters is None:
        try:
            calV = float(CalRegisters)
        except:
            try:
                calV = eval(CalRegisters)
            except:
                calV = CalRegisters
        if isinstance(calV, np.ndarray):
            remappedCalibVal = calV
        elif isinstance(calV,float):
            calV = int(calV * 2**11)
            remappedCalibVal = np.array([calV]*48)
        elif isinstance(calV, list):
            remappedCalibVal = np.array(calV)
        elif 'passThrough' in calV:
            remappedCalibVal = np.array([1<<11]*48,dtype=int)
        elif '.csv' in calV:
            calV = pd.read_csv(calV)
            remappedCalibVal = calV.values[0]

    if not ThresholdRegisters is None:
        try:
            threshV = float(ThresholdRegisters)
        except:
            try:
                threshV = eval(ThresholdRegisters)
            except:
                threshV = ThresholdRegisters
        if isinstance(threshV, np.ndarray):
            remappedThreshVal = threshV
        elif isinstance(threshV,float):
            thrV = int(threshV)
            remappedThreshVal = np.array([thrV]*48)
        elif isinstance(threshV, list):
            remappedThreshVal = np.array(threshV)
        elif 'passThrough' in threshV:
            remappedThreshVal = np.array([0]*48,dtype=int)
        elif '.csv' in threshV:
            thrV = pd.read_csv(threshV)
            remappedThreshVal = thrV.values[0]

    return remappedCalibVal, remappedThreshVal
    
def Calibrate(df_F2F, CALVALUE_Registers):
    
    df_CALQ = (df_F2F*CALVALUE_Registers*2**-11).astype(int)
    df_CALQ.columns = [f'CALQ_{i}' for i in range(48)]
    
    return df_CALQ
