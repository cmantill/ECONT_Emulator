import argparse
import pandas as pd
import numpy as np

parser = argparse.ArgumentParser()
parser.add_argument('-i','--input', dest='input', required=True, help='input dir file name')
parser.add_argument('--col', dest='col', required=True, help='name of column to extract')
parser.add_argument('-n', dest='n', type=int, required=True, help='number of channels')
args = parser.parse_args()

inputFile = args.input

df = pd.read_csv(inputFile,skipinitialspace=True)

vHex = np.vectorize(hex)

# e.g. ePortRxDataGroup_
cols = [f'%s_{i}'%args.col for i in range(args.n)]
print(cols)
df[cols] = vHex(df[cols])

df.to_csv(inputFile.replace('.csv','_HEX.csv'),index=None)

