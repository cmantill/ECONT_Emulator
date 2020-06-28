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


def loadEportRXData(_inputDir, headers = None):
    df = None
    for fileName in ['EPORTRX_data','EPORTRX_output']:
        try:
            df = pd.read_csv(f"{_inputDir}/{fileName}.csv")
            break
        except:
            continue
    if df is None:
        raise AttributeError("Input data not found")
    df['Orbit'] = (np.arange(len(df))/3564).astype(int)
    df['BX'] = np.arange(len(df),dtype=int)%3564
    df.set_index(['Orbit','BX'], inplace=True)

    if headers is None:
        df_BX_CNT = pd.DataFrame(np.arange(len(df))%32, columns=['BX_CNT'], index=df.index)

    columns = [f'ePortRxDataGroup_{i}' for i in range(12)] + ['entry']
    return df[columns], df_BX_CNT

def splitEportRXData(df_ePortRxDataGroup):
    Mux_in_headers = np.array([f'Mux_in_{i}' for i in range(48)])
    
    x0 = df_ePortRxDataGroup.values>>21
    x1 = (df_ePortRxDataGroup.values%2**21)>>14
    x2 = (df_ePortRxDataGroup.values%2**14)>>7
    x3 = (df_ePortRxDataGroup.values%2**7)

    df_Mux_in = pd.DataFrame(x0,columns=Mux_in_headers[::4],index=df_ePortRxDataGroup.index)
    df_Mux_in[Mux_in_headers[1::4]] = pd.DataFrame(x1,columns=Mux_in_headers[1::4],index=df_ePortRxDataGroup.index)
    df_Mux_in[Mux_in_headers[2::4]] = pd.DataFrame(x2,columns=Mux_in_headers[2::4],index=df_ePortRxDataGroup.index)
    df_Mux_in[Mux_in_headers[3::4]] = pd.DataFrame(x3,columns=Mux_in_headers[3::4],index=df_ePortRxDataGroup.index)

    return df_Mux_in
