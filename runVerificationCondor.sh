#!/bin/bash

#extra=$@
subdet=$1
layer=$2
jobN=$3
jobTot=$3


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

    source /cvmfs/sft.cern.ch/lcg/views/LCG_95apython3/x86_64-centos7-gcc8-opt/setup.sh;
    xrdcp root://cmseos.fnal.gov//store/user/dnoonan/HGCAL_Concentrator/localFiles_python36.tgz .
    tar -zxf localFiles_python36.tgz
    export PYTHONPATH=$PYTHONPATH:${_CONDOR_SCRATCH_DIR}/python3.6/site-packages/
    rm localFiles_python36.tgz ;
fi

subdetName=("NONE" "NONE" "NONE" "EE" "EH")

#run isolation script"

python verify.py -o ttbarData_subdet_${subdetName[subdet]}_layer_${layer} -d $subdet -l $layer --jobSplit ${jobN}/${jobTot}

if [ -z ${_CONDOR_SCRATCH_DIR} ] ; then 
    echo "Running Interactively" ; 
else
    echo "Send data to eos and cleanup" 
    tar -zcf ttbarData_subdet_${subdetName[subdet]}_layer_${layer}_job${jobN}of${jobTot}.tgz ttbarData_subdet_${subdetName[subdet]}_layer_${layer}

    xrdcp -rf ttbarData_subdet_${subdetName[subdet]}_layer_${layer}_job${jobN}of${jobTot}.tgz root://cmseos.fnal.gov//store/user/lpchgcal/ECON_Verification_Data
    rm ttbarData_subdet_${subdetName[subdet]}_layer_${layer}_job${jobN}of${jobTot}.tgz
    rm -rf ttbarData_subdet_${subdetName[subdet]}_layer_${layer}
    rm -rf python3.6/site-packages ;
fi
