mkdir converter/inputs
mkdir converter/outputs
mkdir converter/outputs/reference
mkdir converter/outputs/implementation

mkdir encoder/inputs
mkdir encoder/inputs/weights
mkdir encoder/inputs/features

mkdir encoder/outputs  
mkdir encoder/outputs/implementation  
mkdir encoder/outputs/reference

touch converter/outputs/implementation/tb_converter_outputs.dat
cd encoder/inputs/features
ln -s ../../../converter/outputs/implementation/tb_converter_outputs.dat tb_converter_outputs.dat
cd ../../..

