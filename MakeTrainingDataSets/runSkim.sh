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

eosDir=/store/user/dnoonan/AE_TrainingData/$1
eosContents=$(xrdfs root://cmseos.fnal.gov ls ${eosDir})

for tarPath in $eosContents;
do
    echo $tarPath
    
    xrdcp root://cmseos.fnal.gov/$tarPath .
    tarFile=${tarPath#$eosDir}
    echo $tarFile;
    tar -zxf $tarFile
    
    FILES=ele*/*/*
    for f in $FILES;
    do
        echo $f;
        python3 skimToSimOnly.py -i $f
        rm $f
    done;

    DIRS=ele*/*
    for d in $DIRS;
    do
        x=$(ls $d | wc -l)
        echo $d
        echo $x
        if [ $x -eq "0" ];
        then
            echo "Skipping $d";
        else
            tar -zcf ${tarFile} $d
            xrdcp -f ${tarFile} root://cmseos.fnal.gov//store/user/dnoonan/AE_TrainingData/Skimmed/$1
        fi
    done;

    rm $tarFile
    rm -rf el*Training*
done;


