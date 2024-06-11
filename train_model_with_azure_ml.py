import os
from azureml.core import Workspace, Experiment, ScriptRunConfig, Environment, Model, Run
from azureml.core.compute import ComputeTarget, AmlCompute
from azureml.exceptions import ComputeTargetException


ws = Workspace.from_config()


experiment = Experiment(workspace=ws, name='sinkhole-training')


compute_name = ''
try:
    compute_target = ComputeTarget(workspace=ws, name=compute_name)
    print("Found existing compute target.")
except ComputeTargetException:
    print("Creating a new compute target...")
    compute_config = AmlCompute.provisioning_configuration(vm_size='STANDARD_DS11_V2', max_nodes=4)
    compute_target = ComputeTarget.create(ws, compute_name, compute_config)
    compute_target.wait_for_completion(show_output=True)


env = Environment.from_conda_specification(name='sinkhole-env', file_path='conda_env.yml')

# Prepare the script for training
src = ScriptRunConfig(source_directory='.',
                      script='train.py',
                      arguments=[
                          '--csv_blob_name', '',
                          '--raster_blob_names', '',
                          '--iterations', 2000,
                          '--output_folder', 'output',
                          '--container_name', '',
                          '--connection_string', ''
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
    model_path=model_path,  
    model_name="sinkhole-model", 
    tags={"area": "sinkhole detection", "type": "classification"},
    description="Sinkhole detection model"
)

print(f"Model registered: {model.name} with version: {model.version}")
