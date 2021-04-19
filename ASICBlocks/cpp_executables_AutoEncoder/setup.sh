mkdir converter/inputs
mkdir converter/outputs/reference
mkdir converter/outputs/implementation

encoder/inputs/weights
encoder/inputs/features

encoder/outputs/implementation  
encoder/outputs/reference

touch converter/outputs/implementation/tb_converter_outputs.dat
cd encoder/inputs/features
ln -s ../../../converter/outputs/implementation/tb_converter_outputs.dat tb_converter_outputs.dat
cd ../../..

