import numpy as np
import pandas as pd

stc2x2_Map  = np.array([np.arange(0,4),
                        np.arange(4,8),
                        np.arange(8,12),
                        np.arange(12,16),
                        np.arange(16,20),
                        np.arange(20,24),
                        np.arange(24,28),
                        np.arange(28,32),
                        np.arange(32,36),
                        np.arange(36,40),
                        np.arange(40,44),
                        np.arange(44,48)])

stc4x4_Map = np.array([np.arange(0,16),
                       np.arange(16,32),
                       np.arange(32,48)])

cols = [f'CALQ_{i}' for i in range(48)]

def supertriggercell_2x2(row):

    stcMap = stc2x2_Map

    chargeQ = row[cols].values
    stc_Charges = chargeQ[stcMap]

    stc_sum=stc_Charges.sum(axis=1)
    stc_idx=stc_Charges.argmax(axis=1)

    return np.append(stc_sum,stc_idx)


def supertriggercell_4x4(row):

    stcMap = stc4x4_Map

    chargeQ = row[cols].values
    stc_Charges = chargeQ[stcMap]

    stc_sum=stc_Charges.sum(axis=1)
    stc_idx=stc_Charges.argmax(axis=1)

    return np.append(stc_sum,stc_idx)

