import os

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
