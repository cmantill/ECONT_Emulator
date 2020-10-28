#!/usr/bin/env bash                                                                                                                                                                                       
NAME=hgcalPythonEnv

python3 -m venv --copies $NAME
source $NAME/bin/activate

python3 -m pip install setuptools pip --upgrade
python3 -m pip install uproot
python3 -m pip install numpy
python3 -m pip install pandas==0.25.3
