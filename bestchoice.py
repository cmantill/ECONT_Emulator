#!/usr/bin/env python3

import optparse
import numpy as np
import pandas as pd
import math as m

def sort(df):
    # minus sign to sort in descending order
    # FIXME: should find a way to apply the indices instead of sorting twice
    ar_sorted_index = np.array(np.argsort(-df, axis=1))
    ar_sorted = -np.sort(-df, axis=1)
    return pd.DataFrame(ar_sorted, index=df.index), pd.DataFrame(ar_sorted_index)

def sorter(ar, adr):
    N = int(ar.shape[0])
    t = int(m.ceil(m.log(N)/m.log(2)))
    p = int(2**(t-1))
    while p>=1:
        q = 2**(t-1)
        r = 0
        d = p
        while q>=p:
            for i in range(N-d):
                if i & p != r: continue
                if ar[i] < ar[i+d]:
                    ar[i+d], ar[i] = ar[i], ar[i+d]
                    adr[i+d], adr[i] = adr[i], adr[i+d]
            d = q - p
            q = q//2
            r = p
        p = p//2
    return ar, adr

def merger(ar, adr):
    N = int(ar.shape[0])
    t = int(m.ceil(m.log(N)/m.log(2)))
    p = 1
    q = 2**(t-1)
    r = 0
    d = p
    while q>=p:
        for i in range(N-d):
            if i & p != r: continue
            if ar[i] < ar[i+d]:
                ar[i+d], ar[i] = ar[i], ar[i+d]
                adr[i+d], adr[i] = adr[i], adr[i+d]
        d = q - p
        q = q//2
        r = p
    return ar, adr

# TODO: cleaning
def batcher_sort(row):
    ar = np.array(row)
    N = int(ar.shape[0])
    adr = np.array(range(0, N))
    # sort 4 sub arrays
    subars = []
    subadrs = []
    for s in range(4):
        subar = ar[s*12:(s+1)*12]
        subadr = adr[s*12:(s+1)*12]
        subar, subadr = sorter(subar, subadr)
        subars.append(subar)
        subadrs.append(subadr)
    # Prepare mergerA inputs
    merger_ars = []
    merger_adrs = []
    merger_ars.append(np.zeros(24, dtype=int))
    merger_ars.append(np.zeros(24, dtype=int))
    merger_adrs.append(np.zeros(24, dtype=int))
    merger_adrs.append(np.zeros(24, dtype=int))
    for s in range(2):
        for i in range(12):
            merger_ars[0][i*2+s] = subars[s][i]
            merger_adrs[0][i*2+s] = subadrs[s][i]

    for s in range(2,4):
        for i in range(12):
            merger_ars[1][(i-1)*2+s] = subars[s][i]
            merger_adrs[1][(i-1)*2+s] = subadrs[s][i]
    # First stage mergers
    for m in range(2):
        merger_ars[m], merger_adrs[m] = merger(merger_ars[m], merger_adrs[m])
    # Prepare mergerB inputs
    merger_ars.append(np.zeros(48, dtype=int))
    merger_adrs.append(np.zeros(48, dtype=int))
    for m in range(2):
        for i in range(24):
            merger_ars[2][i*2+m] = merger_ars[m][i]
            merger_adrs[2][i*2+m] = merger_adrs[m][i]
    # Second stage mergers
    merger_ars[2], merger_adrs[2] = merger(merger_ars[2], merger_adrs[2])
    return pd.Series(merger_adrs[2])#, merger_ars[2]


def main(input_file, output_charge_file, output_address_file):
    df_in = pd.read_csv(input_file )
    df_sorted, _ = sort(df_in)
    df_sorted_index = pd.DataFrame(df_in.apply(batcher_sort, axis=1))
    df_sorted.columns = ['BC_Charge_{}'.format(i) for i in range(0, df_sorted.shape[1])]
    df_sorted.index.name = 'BC'
    df_sorted_index.columns = ['BC_Address_{}'.format(i) for i in range(0, df_sorted_index.shape[1])]
    df_sorted_index.index.name = 'BC'
    df_sorted.to_csv(output_charge_file)
    df_sorted_index.to_csv(output_address_file)
    # workaround to have separators with more than one char
    # pandas to_csv cannot to that
    with open(output_charge_file, 'rt') as fout:
        data = fout.read()
        data = data.replace(',', ', ')
    with open(output_charge_file, 'wt') as fout:
        fout.write(data)
    with open(output_address_file, 'rt') as fout:
        data = fout.read()
        data = data.replace(',', ', ')
    with open(output_address_file, 'wt') as fout:
        fout.write(data)




if __name__=='__main__':
    parser = optparse.OptionParser()
    parser.add_option("--input", type="string", dest="input_file", help="input pattern file")
    parser.add_option("--output_charge", type="string", dest="output_charge_file", help="output charges file")
    parser.add_option("--output_address", type="string", dest="output_address_file", help="output address file")
    (opt, args) = parser.parse_args()
    main(opt.input_file, opt.output_charge_file, opt.output_address_file)
