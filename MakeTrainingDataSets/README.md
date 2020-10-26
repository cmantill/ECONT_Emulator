# Produce Autoencoder training datasets

Scripts for producing datasets used in training of autoencoder algorithm.  Multiple steps are involved:

 * submitTrainingData.sh : Script to start jobs to run the ECON-T emulator producing CALQ input data (produces tar of necessary emulator scripts to be sent as well)
 * submitByLink.jdl : condor submission for splitting datasets based on link allocations
 * submitSkim.jdl : condor submission script to begin the skim of training data, removing partials and modules without sim energy


