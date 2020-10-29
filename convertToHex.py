import argparse
import pandas as pd
import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument('-i','--input', dest='input', required=True, help='input dir file name')
args = parser.parse_args()

inputFile = args.input

df = pd.read_csv(inputFile,skipinitialspace=True)

vHex = np.vectorize(hex)

cols = [f'ePortRxDataGroup_{i}' for i in range(12)]

df[cols] = vHex(df[cols])

df.to_csv(inputFile.replace('.csv','_HEX.csv'),index=None)

