import os
from azureml.core import Workspace, Experiment, ScriptRunConfig, Environment, Model, Run
from azureml.core.compute import ComputeTarget, AmlCompute
from azureml.exceptions import ComputeTargetException

# Connect to your workspace
ws = Workspace.from_config() 

# Create an experiment
experiment = Experiment(workspace=ws, name='sinkhole-training')

# Define the compute target
compute_name = 'cpu-cluster'
try:
    compute_target = ComputeTarget(workspace=ws, name=compute_name)
    print("Found existing compute target.")
except ComputeTargetException:
    print("Creating a new compute target...")
    compute_config = AmlCompute.provisioning_configuration(vm_size='STANDARD_DS11_V2', max_nodes=4)
    compute_target = ComputeTarget.create(ws, compute_name, compute_config)
    compute_target.wait_for_completion(show_output=True)

# Define the environment
env = Environment.from_conda_specification(name='sinkhole-env', file_path='conda_env.yml')

# Prepare the script for training
src = ScriptRunConfig(source_directory='.',
                      script='train.py',
                      arguments=[
                          '--csv_blob_name', 'sinkhole_data.csv',
                          '--raster_blob_names', 'geology.tif,fault.tif,river.tif','caveDensity.tif','DEM.tif','depthToBedrock.tif','inventoryOfMinesOccu,tif','losingAndGainingStream,tif','naturalco.tif','quality.tif','satherm.tif',
                          '--iterations', 2000,
                          '--output_folder', 'output',
                          '--container_name', 'sinkholedata',
                          '--connection_string', 'DefaultEndpointsProtocol=https;AccountName=neuralrocksml1301062558;AccountKey=/0jJ6uHQJ1t/7RjOfcOtzHtiOltXn79tMBvENwAHZIQNfy6SXh54qSkWgSUH9HiC0SdFMCRDonRv+ASt53heNg==;EndpointSuffix=core.windows.net'
                      ],
                      compute_target=compute_target,
                      environment=env)

# Submit the experiment
run = experiment.submit(src)
run.wait_for_completion(show_output=True)

# Download the model file from the run's outputs
output_dir = 'output'
os.makedirs(output_dir, exist_ok=True)
model_path = os.path.join(output_dir, 'model.pkl')
run.download_file(name='outputs/model.pkl', output_file_path=model_path)

print(f"Model downloaded to: {model_path}")

# Register the model
model = Model.register(
    workspace=ws,
    model_path=model_path,  # Local path to the downloaded model
    model_name="sinkhole-model",  # Name of the model in Azure ML
    tags={"area": "sinkhole detection", "type": "classification"},
    description="Sinkhole detection model"
)

print(f"Model registered: {model.name} with version: {model.version}")
