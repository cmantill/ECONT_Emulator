import pandas as pd

import numpy as np
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('-i','--input', dest='input', required=True, help='input dir file name')
args = parser.parse_args()

dfInput = pd.read_csv(args.input)


dfSkim = dfInput[(dfInput.SimEnergyTotal>0) & (dfInput.ModType.isin(['FI','FM','FO']))]

dfSkim.to_csv(args.input,index=False)
