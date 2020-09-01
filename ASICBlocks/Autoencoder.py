from tensorflow.keras.models import model_from_json  
import numpy as np
import pandas as pd

import numba

from Utils.encode import encode, decode

encodeV = np.vectorize(encode)

import re
def atoi(text):
    return int(text) if text.isdigit() else text
def natural_keys(text):
    return [ atoi(c) for c in re.split('(\d+)',text) ]

def loadModelBase(f_model="Utils/encoder_model_architecture_quantized.json"):
    with open(f_model,'r') as f:
        if 'QActivation' in f.read():
            from qkeras import QDense, QConv2D, QActivation,quantized_bits,Clip
            f.seek(0)
            model = model_from_json(f.read(),
                                    custom_objects={'QActivation':QActivation,
                                                    'quantized_bits':quantized_bits,
                                                    'QConv2D':QConv2D,
                                                    'QDense':QDense,
                                                    'Clip':Clip})
        else:
            f.seek(0)
            model = model_from_json(f.read())

    return model


def loadWeightsFromHDF5(model,fName="Utils/testWeightsQuantiazed.hdf5"):
    model.load_weights(fName)

#write weights to a csv file 
def exportWeightsToRegisters(model, fName=None):
    weights = model.get_weights()

    convWeights = weights[0]
    convBiases = weights[1]
    denseWeights = weights[2]
    denseBiases = weights[3]

    registerNames = []
    registerValues = []

    for i in range(3):
        for j in range(3):
            for k in range(3):
                for l in range(8):
                    registerNames.append(f'ConvWeight_{i}_{j}_{k}_{l}')
                    registerValues.append(convWeights[i][j][k][l])
    for i in range(8):
        registerNames.append(f'ConvBias_{i}')
        registerValues.append(convBiases[i])
    for i in range(128):
        for j in range(16):
            registerNames.append(f'DenseWeight_{i}_{j}')
            registerValues.append(denseWeights[i][j])
    for i in range(16):
        registerNames.append(f'DenseBias_{i}')
        registerValues.append(denseBiases[i])

    registerValues = np.array(registerValues)
    registerValues.shape = (1,2288)
    df_registers = pd.DataFrame(registerValues,columns=registerNames)

    if not fName is None:
        df_registers.to_csv(fName,index=None)

    return df_registers

#load weights from a csv file of registers
def loadWeightsFromRegisters(model,fName):

    df_registers = pd.read_csv(fName)

    columnNames = df_registers.columns.values

    convWeightCols = [x for x in columnNames if 'ConvWeight' in x]
    convBiasCols = [x for x in columnNames if 'ConvBias' in x]
    denseWeightCols = [x for x in columnNames if 'DenseWeight' in x]
    denseBiasCols = [x for x in columnNames if 'DenseBias' in x]

    convWeightCols.sort(key=natural_keys)
    convBiasCols.sort(key=natural_keys)
    denseWeightCols.sort(key=natural_keys)
    denseBiasCols.sort(key=natural_keys)

    convWeightValues = df_registers[convWeightCols].values[0]
    convBiasValues = df_registers[convBiasCols].values[0]
    denseWeightValues = df_registers[denseWeightCols].values[0]
    denseBiasValues = df_registers[denseBiasCols].values[0]

    convWeightValues.shape=(3,3,3,8)
    convBiasValues.shape=(8,)
    denseWeightValues.shape=(128,16)
    denseBiasValues.shape=(16,)

    weights = [convWeightValues,
               convBiasValues,
               denseWeightValues,
               denseBiasValues]

    model.set_weights(weights)


def evaluateAE(row, model):
    normedValues = row[[f'CALQ_{i}' for i in range(48)]].values.astype(np.float32)
    normedValues = normedValues/normedValues.sum()
    normedValues *= np.round(normedValues * 2**8)/2**8
    normedValues.shape=(3,16)
    normedValues = normedValues.transpose()
    normedValues.shape=(1,4,4,3)
    return model.predict(normedValues)[0]

from ASICBlocks.Formatter import binFormat

def formatOutputBits(row, NbitDecimal=8):
    latentSpaceVals = (row[[f'ENCODED_{i}' for i in range(15,-1,-1)]] * 2**NbitDecimal).astype(int)

    latentSpaceBits = ''.join(binFormat(latentSpaceVals,N=9).tolist())
    modSum = ''.join(binFormat(int(row['ModSum']),9).tolist())

    outputBits = '0000000' + latentSpaceBits
    outputBits = outputBits+ modSum


    outputBytes = [outputBits[x*8:(x+1)*8] for x in range(20)]

    return outputBytes



def Autoencoder(df_CALQ, modelJSON=None, Weights_Registers=None, Weights_HDF5=None, registerFileNameOutput=None):
    if modelJSON is None:
        model=loadModelBase()
    else:
        model=loadModelBase(modelJSON)

    if Weights_Registers is None:
        if Weights_HDF5 is None:
            print("Need to specify either HDF5 or Register csv file for weights")
            exit()
        loadWeightsFromHDF5(model, Weights_HDF5)
        if not registerFileNameOutput is None:
            exportWeightsToRegisters(model, registerFileNameOutput)
    else:
        loadWeightsFromRegisters(model, Weights_Registers)

    df_Encoded = pd.DataFrame(df_CALQ.apply(evaluateAE,model=model,axis=1).tolist(), columns=[f'ENCODED_{i}' for i in range(16)],index=df_CALQ.index)

    df_Encoded['ModSum'] = encodeV(df_CALQ.sum(axis=1),dropBits=0,expBits=5,mantBits=4,roundBits=False,asInt=True)

    ae_output = pd.DataFrame(df_Encoded.apply(formatOutputBits, axis=1).tolist(),columns=[f'AE_BYTE{i}' for i in range(19,-1,-1)],index=df_Encoded.index)

    return ae_output[[f'AE_BYTE{i}' for i in range(20)]]


