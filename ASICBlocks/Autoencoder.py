import pandas as pd
import numpy as np

from subprocess import Popen, PIPE
import os

from Utils.encode import encode

def toDecimal(x):
    w = -1. if x[0]=='1' else 0
    w += int(x[1:],2)/2**5
    return w

def convertI2CtoWeights(inputDir):
    I2C_values = pd.read_csv(f'{inputDir}/AE_Input_weights_auto_encoder.csv',skipinitialspace=True,comment='#').values[0]
    I2C_bits = ''

    for weight in I2C_values:
        I2C_bits = format(int(weight,16),'01072b') + I2C_bits

    w2_bits = I2C_bits[-432:]
    b2_bits = I2C_bits[-480:-432]
    w4_bits = I2C_bits[-12768:-480]
    b4_bits = I2C_bits[:-12768]

    w2_values = [toDecimal(w2_bits[i:i+6]) for i in range(0,len(w2_bits),6)]
    b2_values = [toDecimal(b2_bits[i:i+6]) for i in range(0,len(b2_bits),6)]
    w4_values = [toDecimal(w4_bits[i:i+6]) for i in range(0,len(w4_bits),6)]
    b4_values = [toDecimal(b4_bits[i:i+6]) for i in range(0,len(b4_bits),6)]

    w2_values = w2_values[::-1]
    b2_values = b2_values[::-1]
    w4_values = w4_values[::-1]
    b4_values = b4_values[::-1]

    return [w2_values, b2_values, w4_values, b4_values]

def convertWeightsFromFiles(inputDir):
    return


def bin9(x):
    return format(x, '09b')
bin9 = np.vectorize(bin9)

def toHex(row):
    return format(int(row['binary'],2),'039x')

encode = np.vectorize(encode)

def Autoencoder(df_CalQ, weights=None):
    df = df_CalQ.copy()
    calColumns = df.columns
    cwd = os.path.dirname(__file__)

    if not os.path.exists(f'{cwd}/cpp_executables_AutoEncoder/'):
        print(os.getcwd())
        print(cwd) 
        print('Executables directory for autoencoder does not exist')
        print('Exitting')
        exit()

    df.to_csv(f'{cwd}/cpp_executables_AutoEncoder/converter/inputs/tb_converter_inputs.dat',sep=' ',header=False, index=False)
    convertOut = Popen('converter.x',cwd=f"{cwd}/cpp_executables_AutoEncoder/converter",stdout=PIPE).communicate()

    sumDF = pd.read_csv(f'{cwd}/cpp_executables_AutoEncoder/converter/outputs/implementation/tb_converter_sum_outputs.dat',header=None,names=['encodedSUM'])

    df['SUM'] = df[[f'CALQ_{i}' for i in range(48)]].sum(axis=1)
    df['encodedSUM'] = encode(df.SUM,0,5,4,asInt=True)

    
    agreement_SUM = (sumDF==df[['encodedSUM']]).values.all()

    if not agreement_SUM:
        print('ERROR IN ENCODED SUMS')
        exit()

    if not weights is None:
        np.array(weights[0]).tofile(f'{cwd}/cpp_executables_AutoEncoder/encoder/inputs/weights/w2.txt',sep=', ')
        np.array(weights[1]).tofile(f'{cwd}/cpp_executables_AutoEncoder/encoder/inputs/weights/b2.txt',sep=', ')
        np.array(weights[2]).tofile(f'{cwd}/cpp_executables_AutoEncoder/encoder/inputs/weights/w4.txt',sep=', ')
        np.array(weights[3]).tofile(f'{cwd}/cpp_executables_AutoEncoder/encoder/inputs/weights/b4.txt',sep=', ')

    encodeOut = Popen('encoder.x',cwd=f"{cwd}/cpp_executables_AutoEncoder/encoder",stdout=PIPE).communicate()

    columns = [f'OUT_{i}' for i in range(16)]

    df[columns] = pd.read_csv(f'{cwd}/cpp_executables_AutoEncoder/encoder/outputs/implementation/tb_encoder_outputs.dat',sep=' ',index_col=False, names=columns)

    df_out = (df[columns]*2**8).astype(int)

    df_out[columns] = bin9(df_out[columns])

#    df_out['SUM'] = df['SUM'].apply(encode,dropBits=0, expBits=5, mantBits=4)
    df_out['SUM'] = bin9(sumDF)

    #sumDF.apply(encode,dropBits=0, expBits=5, mantBits=4)

    concat = df_out['SUM']
    for c in columns:
        concat = df_out[c] + concat

    df_out['binary'] = concat

    df_out['AE_OUTPUT_OUTENCODER'] = df_out.apply(toHex,axis=1)

    return df_out[['AE_OUTPUT_OUTENCODER']]



# from tensorflow.keras.models import model_from_json  
# import numpy as np
# import pandas as pd

# import numba

# from Utils.encode import encode, decode

# encodeV = np.vectorize(encode)

# import re
# def atoi(text):
#     return int(text) if text.isdigit() else text
# def natural_keys(text):
#     return [ atoi(c) for c in re.split('(\d+)',text) ]

# def loadModelBase(f_model="Utils/encoder_model_architecture_quantized.json"):
#     with open(f_model,'r') as f:
#         if 'QActivation' in f.read():
#             from qkeras import QDense, QConv2D, QActivation,quantized_bits,Clip
#             f.seek(0)
#             model = model_from_json(f.read(),
#                                     custom_objects={'QActivation':QActivation,
#                                                     'quantized_bits':quantized_bits,
#                                                     'QConv2D':QConv2D,
#                                                     'QDense':QDense,
#                                                     'Clip':Clip})
#         else:
#             f.seek(0)
#             model = model_from_json(f.read())

#     return model


# def loadWeightsFromHDF5(model,fName="Utils/testWeightsQuantiazed.hdf5"):
#     model.load_weights(fName)

# #write weights to a csv file 
# def exportWeightsToRegisters(model, fName=None):
#     weights = model.get_weights()

#     convWeights = weights[0]
#     convBiases = weights[1]
#     denseWeights = weights[2]
#     denseBiases = weights[3]

#     registerNames = []
#     registerValues = []

#     for i in range(3):
#         for j in range(3):
#             for k in range(3):
#                 for l in range(8):
#                     registerNames.append(f'ConvWeight_{i}_{j}_{k}_{l}')
#                     registerValues.append(convWeights[i][j][k][l])
#     for i in range(8):
#         registerNames.append(f'ConvBias_{i}')
#         registerValues.append(convBiases[i])
#     for i in range(128):
#         for j in range(16):
#             registerNames.append(f'DenseWeight_{i}_{j}')
#             registerValues.append(denseWeights[i][j])
#     for i in range(16):
#         registerNames.append(f'DenseBias_{i}')
#         registerValues.append(denseBiases[i])

#     registerValues = np.array(registerValues)
#     registerValues.shape = (1,2288)
#     df_registers = pd.DataFrame(registerValues,columns=registerNames)

#     if not fName is None:
#         df_registers.to_csv(fName,index=None)

#     return df_registers

# #load weights from a csv file of registers
# def loadWeightsFromRegisters(model,fName):

#     df_registers = pd.read_csv(fName)

#     columnNames = df_registers.columns.values

#     convWeightCols = [x for x in columnNames if 'ConvWeight' in x]
#     convBiasCols = [x for x in columnNames if 'ConvBias' in x]
#     denseWeightCols = [x for x in columnNames if 'DenseWeight' in x]
#     denseBiasCols = [x for x in columnNames if 'DenseBias' in x]

#     convWeightCols.sort(key=natural_keys)
#     convBiasCols.sort(key=natural_keys)
#     denseWeightCols.sort(key=natural_keys)
#     denseBiasCols.sort(key=natural_keys)

#     convWeightValues = df_registers[convWeightCols].values[0]
#     convBiasValues = df_registers[convBiasCols].values[0]
#     denseWeightValues = df_registers[denseWeightCols].values[0]
#     denseBiasValues = df_registers[denseBiasCols].values[0]

#     convWeightValues.shape=(3,3,3,8)
#     convBiasValues.shape=(8,)
#     denseWeightValues.shape=(128,16)
#     denseBiasValues.shape=(16,)

#     weights = [convWeightValues,
#                convBiasValues,
#                denseWeightValues,
#                denseBiasValues]

#     model.set_weights(weights)


# def evaluateAE(row, model):
#     normedValues = row[[f'CALQ_{i}' for i in range(48)]].values.astype(np.float32)
#     normedValues = normedValues/normedValues.sum()
#     normedValues *= np.round(normedValues * 2**8)/2**8
#     normedValues.shape=(3,16)
#     normedValues = normedValues.transpose()
#     normedValues.shape=(1,4,4,3)
#     return model.predict(normedValues)[0]

# from ASICBlocks.Formatter import binFormat

# def formatOutputBits(row, NbitDecimal=8):
#     latentSpaceVals = (row[[f'ENCODED_{i}' for i in range(15,-1,-1)]] * 2**NbitDecimal).astype(int)

#     latentSpaceBits = ''.join(binFormat(latentSpaceVals,N=9).tolist())
#     modSum = ''.join(binFormat(int(row['ModSum']),9).tolist())

#     outputBits = '0000000' + latentSpaceBits
#     outputBits = outputBits+ modSum


#     outputBytes = [outputBits[x*8:(x+1)*8] for x in range(20)]

#     return outputBytes



# def Autoencoder(df_CALQ, modelJSON=None, Weights_Registers=None, Weights_HDF5=None, registerFileNameOutput=None):
#     if modelJSON is None:
#         model=loadModelBase()
#     else:
#         model=loadModelBase(modelJSON)

#     if Weights_Registers is None:
#         if Weights_HDF5 is None:
#             print("Need to specify either HDF5 or Register csv file for weights")
#             exit()
#         loadWeightsFromHDF5(model, Weights_HDF5)
#         if not registerFileNameOutput is None:
#             exportWeightsToRegisters(model, registerFileNameOutput)
#     else:
#         loadWeightsFromRegisters(model, Weights_Registers)

#     df_Encoded = pd.DataFrame(df_CALQ.apply(evaluateAE,model=model,axis=1).tolist(), columns=[f'ENCODED_{i}' for i in range(16)],index=df_CALQ.index)

#     df_Encoded['ModSum'] = encodeV(df_CALQ.sum(axis=1),dropBits=0,expBits=5,mantBits=4,roundBits=False,asInt=True)

#     ae_output = pd.DataFrame(df_Encoded.apply(formatOutputBits, axis=1).tolist(),columns=[f'AE_BYTE{i}' for i in range(19,-1,-1)],index=df_Encoded.index)

#     return ae_output[[f'AE_BYTE{i}' for i in range(20)]]


