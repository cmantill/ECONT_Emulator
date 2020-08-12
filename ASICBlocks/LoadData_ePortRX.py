import pandas as pd
import numpy as np

def loadMetaData(_inputDir):
    metaDataFile = f"{_inputDir.replace('/','.')}.metaData"
    subdet=getattr(__import__(metaDataFile,fromlist=["subdet"]),"subdet")
    layer=getattr(__import__(metaDataFile,fromlist=["layer"]),"layer")
    wafer=getattr(__import__(metaDataFile,fromlist=["wafer"]),"wafer")
    isHDM=getattr(__import__(metaDataFile,fromlist=["isHDM"]),"isHDM")
    geomVersion=getattr(__import__(metaDataFile,fromlist=["geomVersion"]),"geomVersion")
    
    return subdet, layer, wafer, isHDM, geomVersion


def loadEportRXData(_inputDir):
    df = None
    for fileName in ['EPORTRX_data','EPORTRX_output']:
        try:
            df = pd.read_csv(f"{_inputDir}/{fileName}.csv")
            break
        except:
            continue
    if df is None:
        raise AttributeError("Input data not found")

    if not 'Orbit' in df.columns:
        df['Orbit'] = (np.arange(len(df))/3564).astype(int)
        df['BX'] = np.arange(len(df),dtype=int)%3564

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

    
    df.set_index(['Orbit','BX'], inplace=True)

    df_BX_CNT = pd.DataFrame(headers, columns=['BX_CNT'], index=df.index)

    return df[columns], df_BX_CNT

def splitEportRXData(df_ePortRxDataGroup):
    Mux_in_headers = np.array([f'Mux_in_{i}' for i in range(48)])
    
    x0 = (df_ePortRxDataGroup.values>>21) & 127
    x1 = (df_ePortRxDataGroup.values>>14) & 127
    x2 = (df_ePortRxDataGroup.values>>7) & 127
    x3 = (df_ePortRxDataGroup.values) & 127

    df_Mux_in = pd.DataFrame(x0,columns=Mux_in_headers[::4],index=df_ePortRxDataGroup.index)
    df_Mux_in[Mux_in_headers[1::4]] = pd.DataFrame(x1,columns=Mux_in_headers[1::4],index=df_ePortRxDataGroup.index)
    df_Mux_in[Mux_in_headers[2::4]] = pd.DataFrame(x2,columns=Mux_in_headers[2::4],index=df_ePortRxDataGroup.index)
    df_Mux_in[Mux_in_headers[3::4]] = pd.DataFrame(x3,columns=Mux_in_headers[3::4],index=df_ePortRxDataGroup.index)

    return df_Mux_in
