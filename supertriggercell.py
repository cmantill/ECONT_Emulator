import numpy as np
import pandas as pd

stc2x2_Map  = np.array([[ 0,  1,  4,  5],
                        [ 2,  3,  6,  7],
                        [ 8,  9, 12, 13],
                        [10, 11, 14, 15],
                        [16, 17, 20, 21],
                        [18, 19, 22, 23],
                        [24, 25, 28, 29],
                        [26, 27, 30, 31],
                        [32, 33, 36, 37],
                        [34, 35, 38, 39],
                        [40, 41, 44, 45],
                        [42, 43, 46, 47]])

stc4x4_Map = np.array([np.arange(0,16),
                       np.arange(16,32),
                       np.arange(32,48)])

cols = [f'CALQ_{i}' for i in range(48)]
def supertriggercell(row, isHDM=True):

    stcMap = stc2x2_Map if isHDM else stc4x4_Map

    chargeQ = row[cols].values
    stc_Charges = chargeQ[stcMap]

    stc_sum=stc_Charges.sum(axis=1)
    stc_idx=stc_Charges.argmax(axis=1)

    if not isHDM:
        stc_sum = np.append(stc_sum,np.zeros(9,dtype=int))
        stc_idx = np.append(stc_idx,np.zeros(9,dtype=int))

    return np.append(stc_sum,stc_idx)

