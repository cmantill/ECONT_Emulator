#!/usr/bin/env python                                                                                                                                                                     
import numpy as np
import math

def encode(value, dropBits=1, expBits=4, mantBits=3, roundBits=False, asInt=False):
    
    binCode=bin(value)[2:]
    
    if len(binCode) <= (mantBits+dropBits):
        if roundBits and dropBits>0:
            value += 2**(dropBits-1)
        value = value>>dropBits
        binCode=bin(value)[2:]
        
        mantissa = format(value, '#0%ib'%(mantBits+2))[2:]
        exponent = '0'*expBits
    elif len(binCode)==mantBits+dropBits+1:
        if roundBits and dropBits>0:
            value += 2**(dropBits-1)
        value = value>>dropBits
        binCode=bin(value)[2:]
        exponent = '0001'
        mantissa = binCode[1:1+mantBits]
    else:
        if roundBits:
            vTemp = int(binCode,2) + int(2**(len(binCode)-2-mantBits))
            binCode = bin(vTemp)[2:]
        firstZero = len(binCode)-mantBits-dropBits
        if firstZero<1:
            print ("PROBLEM")
        if firstZero<2**expBits:
            exponent = format(firstZero, '#0%ib'%(expBits+2))[2:]
            mantissa = binCode[1:1+mantBits]

        else:
            exponent = '1'*expBits
            mantissa = '1'*mantBits
            
    if asInt:
        return int(exponent + mantissa,2)
    else:
        return exponent + mantissa
        

def decode(val,droppedBits=1,expBits=4,mantBits=3):
    if(type(val)==type(0)):
        val=format(val, '#0%ib'%(expBits+mantBits+2))[2:]
    exp = val[:expBits]
    mant = val[expBits:]
    shift = int(exp,2)
    data = ((int(mant,2)<<(shift-1) if shift>0 else int(mant,2)) + (0 if shift==0 else (1<<(shift+mantBits-1))))<<droppedBits
    return data
