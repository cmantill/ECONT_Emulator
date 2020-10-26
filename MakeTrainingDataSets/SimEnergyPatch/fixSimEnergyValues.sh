#!/bin/bash

#If running on condor, checkout CMSSW and get extra libraries
if [ -z ${_CONDOR_SCRATCH_DIR} ] ; then 
    echo "Running Interactively" ; 
else
    echo "Running In Batch"
    (>&2 echo "Starting job on " `date`) # Date/time of start of job
    (>&2 echo "Running on: `uname -a`") # Condor job is running on this node
    (>&2 echo "System software: `cat /etc/redhat-release`") # Operating System on that node

    cd ${_CONDOR_SCRATCH_DIR}
    echo ${_CONDOR_SCRATCH_DIR}
    xrdcp root://cmseos.fnal.gov//store/user/dnoonan/envhgcalPythonEnv.tar.gz .
    tar -zxf envhgcalPythonEnv.tar.gz
    source hgcalPythonEnv/bin/activate

    rm envhgcalPythonEnv.tar.gz;
fi


job=$1
sample=$2

for layer in 1 3 5 7 9 11 13 15 17 19 21 23 25 27 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50
#for layer in 1 3 5
do
    echo $layer
    xrdcp root://cmseos.fnal.gov//store/user/lpchgcal/ECON_Verification_Data/${sample}Data_v11Geom_layer_${layer}_job${job}.tgz .
done


python3 findEventTotal.py $job $sample

python3 mergeSimEnergy.py $job $sample

for layer in 1 3 5 7 9 11 13 15 17 19 21 23 25 27 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50
do
    xrdcp -f ${sample}Data_v11Geom_layer_${layer}_job${job}.tgz root://cmseos.fnal.gov//store/user/lpchgcal/ECON_Verification_Data/v2/${sample}Data_v11Geom_layer_${layer}_job${job}.tgz
done

if [ -z ${_CONDOR_SCRATCH_DIR} ] ; then 
    echo "Running Interactively" ; 
else
    rm *.py
    rm *tgz
    rm -rf hgcalPythonEnv;
fi
