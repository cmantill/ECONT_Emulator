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
        with open('Utils/geomDF_v10.pkl','rb') as geomFile:
            geomDF = pickle.load(geomFile).loc[subdet,layer,wafer]
    else:
        with open('Utils/geomDF_v9.pkl','rb') as geomFile:
            geomDF = pickle.load(geomFile).loc[subdet,layer,wafer]

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
        if isinstance(CalRegisters, np.ndarray):
            remappedCalibVal = CalRegisters
        elif isinstance(CalRegisters,float):
            calV = int(CalRegisters * 2**11)
            remappedCalibVal = np.array([calV]*48)
        elif isinstance(CalRegisters, list):
            remappedCalibVal = np.array(CalRegisters)
        elif 'passThrough' in CalRegisters:
            remappedCalibVal = np.array([1<<11]*48,dtype=int)
        elif '.csv' in CalRegisters:
            calV = pd.read_csv(CalRegisters)
            remappedCalibVal = calV.values[0]

    if not ThresholdRegisters is None:
        if isinstance(ThresholdRegisters, np.ndarray):
            remappedThreshVal = ThresholdRegisters
        elif isinstance(ThresholdRegisters,float):
            thrV = int(ThresholdRegisters)
            remappedThreshVal = np.array([thrV]*48)
        elif isinstance(ThresholdRegisters, list):
            remappedThreshVal = np.array(ThresholdRegisters)
        elif 'passThrough' in ThresholdRegisters:
            remappedThreshVal = np.array([0]*48,dtype=int)
        elif '.csv' in ThresholdRegisters:
            thrV = pd.read_csv(ThresholdRegisters)
            remappedThreshVal = thrV.values[0]

        # if '.csv' in ThresholdRegisters:
        #     calV = pd.read_csv(ThresholdRegisters)
        #     remappedThreshVal = calV.values[0]
        # if type(ThresholdRegisters) is np.ndarray:
        #     remappedThreshVal = ThresholdRegisters
        # if type(ThresholdRegisters) is list:
        #     remappedThreshVal = np.array(ThresholdRegisters)

    return remappedCalibVal, remappedThreshVal
    
def Calibrate(df_F2F, CALVALUE_Registers):
    
    df_CALQ = (df_F2F*CALVALUE_Registers*2**-11).astype(int)
    df_CALQ.columns = [f'CALQ_{i}' for i in range(48)]
    
    return df_CALQ
