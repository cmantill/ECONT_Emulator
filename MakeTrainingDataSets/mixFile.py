import pandas as pd
import numpy as np
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('-i','--input', dest='input', required=True, help='input dir file name')
args = parser.parse_args()


dfInput = pd.read_csv(args.input)
indexList = dfInput.index.values.copy()
np.random.shuffle(indexList)
dfInput.loc[indexList].to_csv(args.input,index=False)
