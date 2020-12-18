import pandas as pd

import numpy as np
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('-i','--input', dest='input', required=True, help='input dir file name')
args = parser.parse_args()

dfInput = pd.read_csv(args.input)


dfSkim = dfInput[(dfInput.SimEnergyPresent==1) & (dfInput.ModType.isin(['FI','FM','FO']))]

if len(dfSkim)>0:
    dfSkim.to_csv(args.input.replace('.csv','_skimmed.csv'),index=False)
