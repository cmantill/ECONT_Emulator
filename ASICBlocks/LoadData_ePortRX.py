import pandas as pd
import numpy as np
import configparser

def loadMetaData(_inputDir):
    config = configparser.ConfigParser()
    with open(f'{_inputDir}/metaData.py') as cfgfile:
        config.read_string('[section]\n' + cfgfile.read())
    sec = config['section']

    subdet = sec.getint('subdet')
    layer = sec.getint('layer')
    wafer = sec.getint('wafer')
    geomVersion = sec.get('geomversion')[1:-1]
    isHDM = sec.getboolean('isHDM')
    
    return subdet, layer, wafer, isHDM, geomVersion


def loadEportRXData(_inputDir, simEnergy=False, alignmentTime=324):
    df = None
    for fileName in ['EPORTRX_data','EPORTRX_output','EPortRX_Input_EPORTRX_data']:
        try:
            df = pd.read_csv(f"{_inputDir}/{fileName}.csv", skipinitialspace=True)
            break
        except:
            continue
    if df is None:
        raise AttributeError("Input data not found")

    df_SimEnergyStatus=None
    if simEnergy:
        try:
            df_SimEnergyStatus = pd.read_csv(f'{_inputDir}/SimEnergyTotal.csv')
        except:
            raise AttributeError('SimEnergy csv is missing')
        df = df.merge(df_SimEnergyStatus,on='entry',how='left').fillna(0)

    if not 'Orbit' in df.columns:
        df['Orbit'] = (np.arange(len(df))/3564).astype(int)
        df['BX'] = np.arange(len(df),dtype=int)%3564
    if 'GOD_ORBIT_NUMBER' in df.columns:
        df['Orbit'] = df.GOD_ORBIT_NUMBER
        df['BX'] = df.GOD_BUCKET_NUMBER

    columns = [f'ePortRxDataGroup_{i}' for i in range(12)]

    ePortHeader = df['ePortRxDataGroup_0'].values>>28
    if (ePortHeader==0).all() :
        headers = df['BX'].values%16
        headers[df['BX'].values==0] = 31
    else:
        try:
            CounterResetValue = pd.read_csv(f"{_inputDir}/CounterResetValue.csv").loc[0].CounterResetValue
        except:
            CounterResetValue = 0
        BX = df['BX'].values.copy()
        resetIndices = df.index[(df.ePortRxDataGroup_0.values>>28)==9].values
        for i in resetIndices:
            BX[i:] = (np.arange(len(BX[i:]),dtype=int) + CounterResetValue)%3564
        headers = BX % 16
        headers[BX==0] = 31

    df[columns] = df[columns].values & (2**28 - 1)

    df_linkResets = pd.DataFrame({'LINKRESETECONT':0,'LINKRESETROCT':0},index=df.index)

    if 'FASTCMD' in df.columns:
        df_linkResets.loc[df.FASTCMD=='FASTCMD_LINKRESETROCT','LINKRESETROCT'] = 1
        df_linkResets.loc[df.FASTCMD=='FASTCMD_LINKRESETECONT','LINKRESETECONT'] = 1
        resets = np.where(df.FASTCMD.values=='FASTCMD_LINKRESETROCT')[0]        
        for reset_bx in resets:
            df.loc[reset_bx:reset_bx+alignmentTime,columns] = 0
        
    
    df.set_index(['Orbit','BX'], inplace=True)

    df_BX_CNT = pd.DataFrame(headers, columns=['BX_CNT'], index=df.index)

    if simEnergy:
        if 'EventSimEnergy' in df.columns:
            df_SimEnergyStatus = df[['SimEnergyTotal','EventSimEnergy','entry']]
        else:
            df_SimEnergyStatus = df[['SimEnergyTotal','entry']]
    return df[columns], df_BX_CNT, df_SimEnergyStatus, df_linkResets

def splitEportRXData(df_ePortRxDataGroup):
    Mux_in_headers = np.array([f'Mux_in_{i}' for i in range(48)])
    
    x3 = (df_ePortRxDataGroup.values>>21) & 127
    x2 = (df_ePortRxDataGroup.values>>14) & 127
    x1 = (df_ePortRxDataGroup.values>>7) & 127
    x0 = (df_ePortRxDataGroup.values) & 127

    df_Mux_in = pd.DataFrame(x0,columns=Mux_in_headers[::4],index=df_ePortRxDataGroup.index)
    df_Mux_in[Mux_in_headers[1::4]] = pd.DataFrame(x1,columns=Mux_in_headers[1::4],index=df_ePortRxDataGroup.index)
    df_Mux_in[Mux_in_headers[2::4]] = pd.DataFrame(x2,columns=Mux_in_headers[2::4],index=df_ePortRxDataGroup.index)
    df_Mux_in[Mux_in_headers[3::4]] = pd.DataFrame(x3,columns=Mux_in_headers[3::4],index=df_ePortRxDataGroup.index)

    return df_Mux_in
