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

extraName=$1

layer=$2

Njobs=$3

mkdir ${extraName}_TrainingData_PUAllocation
mkdir ${extraName}_TrainingData_PUAllocation/nElinks_1
mkdir ${extraName}_TrainingData_PUAllocation/nElinks_2
mkdir ${extraName}_TrainingData_PUAllocation/nElinks_3
mkdir ${extraName}_TrainingData_PUAllocation/nElinks_4
mkdir ${extraName}_TrainingData_PUAllocation/nElinks_5
mkdir ${extraName}_TrainingData_PUAllocation/nElinks_6
mkdir ${extraName}_TrainingData_PUAllocation/nElinks_7
mkdir ${extraName}_TrainingData_PUAllocation/nElinks_8
mkdir ${extraName}_TrainingData_PUAllocation/nElinks_9
mkdir ${extraName}_TrainingData_PUAllocation/nElinks_10
mkdir ${extraName}_TrainingData_PUAllocation/nElinks_11
mkdir ${extraName}_TrainingData_PUAllocation/nElinks_12
mkdir ${extraName}_TrainingData_PUAllocation/nElinks_13
mkdir ${extraName}_TrainingData_SignalAllocation
mkdir ${extraName}_TrainingData_SignalAllocation/nElinks_2
mkdir ${extraName}_TrainingData_SignalAllocation/nElinks_3
mkdir ${extraName}_TrainingData_SignalAllocation/nElinks_4
mkdir ${extraName}_TrainingData_SignalAllocation/nElinks_5



#for jobN in (1 2 3 4 5 6 7 8 9 10; do
for jobN in $(seq $Njobs); do    
    echo "xrdcp -f root://cmseos.fnal.gov//store/user/lpchgcal/ECON_Verification_Data/v2/${extraName}Data_v11Geom_layer_${layer}_job${jobN}.tgz ."
    xrdcp -f root://cmseos.fnal.gov//store/user/lpchgcal/ECON_Verification_Data/v2/${extraName}Data_v11Geom_layer_${layer}_job${jobN}.tgz .
    
    tar -zxf ${extraName}Data_v11Geom_layer_${layer}_job${jobN}.tgz
    rm ${extraName}Data_v11Geom_layer_${layer}_job${jobN}.tgz
    
    FILES=${extraName}Data_v11Geom_layer_${layer}/*

    for f in $FILES;
    do
	echo $f
	python3 sortByLinks.py -i $f --name $extraName -N 20
    done;
    
    rm -rf ${extraName}Data_v11Geom_layer_${layer}

done;

FILES=${extraName}_TrainingData_PUAllocation/*
for f in $FILES;
do
    x=$(ls $f | wc -l)
    echo $x
    if [ $x -eq "0" ];
    then
        echo "Skipping $f";
    else
        echo $f;        
        tar -zcf ${f}_layer${layer}.tgz ${f}
        xrdcp -f ${f}_layer${layer}.tgz root://cmseos.fnal.gov//store/user/dnoonan/AE_TrainingData/${extraName}/PUAllocation
    fi
done;


FILES=${extraName}_TrainingData_SignalAllocation/*
for f in $FILES;
do
    x=$(ls $f | wc -l)
    echo $x
    if [ $x -eq "0" ];
    then
        echo "Skipping $f";
    else
        echo $f;        
        CSVFILES=$f/*
        for csvF in $CSVFILES;
        do
            python3 mixFile.py -i $csvF
        done;
        tar -zcf ${f}_layer${layer}.tgz ${f}
        xrdcp -f ${f}_layer${layer}.tgz root://cmseos.fnal.gov//store/user/dnoonan/AE_TrainingData/${extraName}/SignalAllocation
    fi
done;




rm -rf ${extraName}_TrainingData_SignalAllocation
rm -rf ${extraName}_TrainingData_PUAllocation

if [ -z ${_CONDOR_SCRATCH_DIR} ] ; then 
    echo "Running Interactively" ; 
else
    rm *.py
    rm *csv
    rm -rf hgcalPythonEnv;
fi
