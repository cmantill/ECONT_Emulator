#!/usr/bin/env bash

source hgcalPythonEnv/bin/activate


#startup offset in orbit and bucket
GOD_ORBIT_OFFSET=1
GOD_BUCKET_OFFSET=660

#location to look for "clean" input data, which is modified by the fast commands
INPUT_DATA_LOCATION="/fasic_home/dnoonan/UVM_Datasets/DATA_V4/HighOccupancy_10Orbits_NoAlgorithm"

OUTPUT_LOCATION="NewVerificationData"

#can be replaced with "None" to no issue any commands
FAST_COMMAND_CONFIG="exampleFastCommandConfig.txt"

#bx to issue orbit sync command (BCR) in
ORBIT_SYNC_COMMAND_BUCKET=3513

python3 simulateFastCommands.py -i ${INPUT_DATA_LOCATION} -o ${OUTPUT_LOCATION} --NoAlgo -c ${FAST_COMMAND_CONFIG} --GodOrbitOffset ${GOD_ORBIT_OFFSET} --GodBucketOffset ${GOD_BUCKET_OFFSET} --counterReset ${ORBIT_SYNC_COMMAND_BUCKET}

python3 convertToHex.py -i ${OUTPUT_LOCATION}/EPortRX_Input_EPORTRX_data.csv

deactivate
