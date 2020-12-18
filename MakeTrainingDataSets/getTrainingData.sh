#!/bin/bash

#extra=$@

subdet=$1

layer=$2

datasetName=$3

jobSplit=$4

jobCount=$5

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

    ls
    ls hgcalPythonEnv

    rm envhgcalPythonEnv.tar.gz
    tar -zxf code.tgz ;
fi

subdetName=("NONE" "EE" "EH" "EE" "EH")

if [ "$datasetName" == "ttbar200PU" ]
then
    echo "TTbar"

    dataType="ttbarData"
    eosInputDir="/store/user/lpchgcal/ConcentratorNtuples/L1THGCal_Ntuples/TTbar_v11"
    inputFileFormat="ntuple_ttbar_ttbar_v11_aged_unbiased_20191101_"
    chunkSize=100

elif [ "$datasetName" == "ele0PU" ]
then
    echo "ele 0PU"

    dataType="ele0PUData"
    eosInputDir="/store/user/lpchgcal/ConcentratorNtuples/L1THGCal_Ntuples/TrainingSamples_Sept2020"
    inputFileFormat="ntuple_SingleElectron_PT2to200_0PU_0threshold_"
    chunkSize=1000

elif [ "$datasetName" == "ele200PU" ]
then
    echo "ele 200PU"

    dataType="ele200PUData"
    eosInputDir="/store/user/lpchgcal/ConcentratorNtuples/L1THGCal_Ntuples/TrainingSamples_Sept2020"
    inputFileFormat="ntuple_SingleElectron_PT2to200_200PU_0threshold_"
    chunkSize=100

fi

echo "python3 getDataFromMC.py -o ${dataType}_v11Geom_layer_${layer} -d $subdet -l $layer -w -1  --Nfiles -1 --Nevents -1 --eosDir ${eosInputDir} --inputFileFormat ${inputFileFormat} --jobSplit ${jobSplit}/${jobCount} --zeroSuppress --chunkSize ${chunkSize}"
python3 getDataFromMC.py -o ${dataType}_v11Geom_layer_${layer} -d $subdet -l $layer -w -1  --Nfiles -1 --Nevents -1 --eosDir ${eosInputDir} --inputFileFormat ${inputFileFormat} --jobSplit ${jobSplit}/${jobCount} --zeroSuppress --chunkSize ${chunkSize}

FILES=${dataType}_v11Geom_layer_${layer}/*
for f in $FILES
do
    echo "Processing $f file..."
    echo "python3 ECONT_Emulator.py --NoAlgo --AEMuxOrdering -i $f --SimEnergyFlag"
    python3 ECONT_Emulator.py --NoAlgo --AEMuxOrdering -i $f --SimEnergyFlag
done

if [ -z ${_CONDOR_SCRATCH_DIR} ] ; then 
    echo "Running Interactively" ; 
else
    echo "Send data to eos and cleanup" 
    tar -zcf ${dataType}_v11Geom_layer_${layer}_job${jobSplit}.tgz ${dataType}_v11Geom_layer_${layer}

    xrdcp -rf ${dataType}_v11Geom_layer_${layer}_job${jobSplit}.tgz root://cmseos.fnal.gov//store/user/lpchgcal/ECON_Verification_Data
    rm ${dataType}_v11Geom_layer_${layer}_job${jobSplit}.tgz
    rm -rf ${dataType}_v11Geom_layer_${layer}
    rm -rf hgcalPythonEnv
    rm *.tgz
    rm -rf Utils
    rm -rf ASICBlocks
    rm *py
fi
