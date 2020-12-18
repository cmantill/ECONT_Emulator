cd ..
tar -zcf MakeTrainingDataSets/code.tgz getDataFromMC.py ECONT_Emulator.py ASICBlocks/ Utils/
cd MakeTrainingDataSets

condor_submit submitTrainingData.jdl
