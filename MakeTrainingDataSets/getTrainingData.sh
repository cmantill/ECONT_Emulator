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

# #get data from ntuples
echo "python3 getDataFromMC.py -o ${dataType}_v11Geom_layer_${layer} -d $subdet -l $layer -w -1  --Nfiles -1 --Nevents -1 --eosDir ${eosInputDir} --inputFileFormat ${inputFileFormat} --jobSplit ${jobSplit}/${jobCount} --zeroSuppress --chunkSize ${chunkSize}"
python3 getDataFromMC.py -o ${dataType}_v11Geom_layer_${layer} -d $subdet -l $layer -w -1  --Nfiles -1 --Nevents -1 --eosDir ${eosInputDir} --inputFileFormat ${inputFileFormat} --jobSplit ${jobSplit}/${jobCount} --zeroSuppress --chunkSize ${chunkSize}

mkdir ${dataType}_TrainingData_PUAllocation
mkdir ${dataType}_TrainingData_PUAllocation/nElinks_1
mkdir ${dataType}_TrainingData_PUAllocation/nElinks_2
mkdir ${dataType}_TrainingData_PUAllocation/nElinks_3
mkdir ${dataType}_TrainingData_PUAllocation/nElinks_4
mkdir ${dataType}_TrainingData_PUAllocation/nElinks_5
mkdir ${dataType}_TrainingData_PUAllocation/nElinks_6
mkdir ${dataType}_TrainingData_PUAllocation/nElinks_7
mkdir ${dataType}_TrainingData_PUAllocation/nElinks_8
mkdir ${dataType}_TrainingData_PUAllocation/nElinks_9
mkdir ${dataType}_TrainingData_PUAllocation/nElinks_10
mkdir ${dataType}_TrainingData_PUAllocation/nElinks_11
mkdir ${dataType}_TrainingData_PUAllocation/nElinks_12
mkdir ${dataType}_TrainingData_PUAllocation/nElinks_13
mkdir ${dataType}_TrainingData_SignalAllocation
mkdir ${dataType}_TrainingData_SignalAllocation/nElinks_2
mkdir ${dataType}_TrainingData_SignalAllocation/nElinks_3
mkdir ${dataType}_TrainingData_SignalAllocation/nElinks_4
mkdir ${dataType}_TrainingData_SignalAllocation/nElinks_5


#run emulator on data from previous step
FILES=${dataType}_v11Geom_layer_${layer}/*
for f in $FILES
do
    echo "Processing $f file..."
    echo "python3 ECONT_Emulator.py --NoAlgo --AEMuxOrdering -i $f --SimEnergyFlag"
    python3 ECONT_Emulator.py --NoAlgo --AEMuxOrdering -i $f --SimEnergyFlag
    python3 sortByLinks.py -i $f --name ${dataType} --job ${jobSplit}
done


FILES=${dataType}_TrainingData_SignalAllocation/*
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
            echo "xrdcp -f ${csvF} root://cmseos.fnal.gov//store/user/dnoonan/AE_TrainingData/NewData/${f}"
            xrdcp -f ${csvF} root://cmseos.fnal.gov//store/user/dnoonan/AE_TrainingData/NewData/${f}
            python3 skimToSimOnly.py -i $csvF
            if [[ $(wc -l <${csvF}) -ge 2 ]]; then
                xrdcp -f ${csvF} root://cmseos.fnal.gov//store/user/dnoonan/AE_TrainingData/NewData/Skim/${f}
            fi
        done;
    fi
done;

FILES=${dataType}_TrainingData_PUAllocation/*
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
            echo "xrdcp -f ${csvF} root://cmseos.fnal.gov//store/user/dnoonan/AE_TrainingData/NewData/${f}"
            xrdcp -f ${csvF} root://cmseos.fnal.gov//store/user/dnoonan/AE_TrainingData/NewData/${f}
            python3 skimToSimOnly.py -i $csvF
            if [[ $(wc -l <${csvF}) -ge 2 ]]; then
                xrdcp -f ${csvF} root://cmseos.fnal.gov//store/user/dnoonan/AE_TrainingData/NewData/Skim/${f}
            fi
        done;
    fi
done;


if [ -z ${_CONDOR_SCRATCH_DIR} ] ; then 
    echo "Running Interactively" ; 
else
    echo "Send data to eos and cleanup" 
    tar -zcf ${dataType}_v11Geom_layer_${layer}_job${jobSplit}.tgz ${dataType}_v11Geom_layer_${layer}

    xrdcp -rf ${dataType}_v11Geom_layer_${layer}_job${jobSplit}.tgz root://cmseos.fnal.gov//store/user/lpchgcal/ECON_Verification_Data/v3
    rm ${dataType}_v11Geom_layer_${layer}_job${jobSplit}.tgz
    rm -rf ${dataType}_v11Geom_layer_${layer}
    rm -rf ${dataType}_TrainingData_PUAllocation
    rm -rf ${dataType}_TrainingData_SignalAllocation
    rm -rf hgcalPythonEnv
    rm *.tgz
    rm -rf Utils
    rm -rf ASICBlocks
    rm *py
fi
