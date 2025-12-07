#deploy model
from azureml.core import Workspace, Environment, Model
from azureml.core.webservice import AciWebservice, Webservice
from azureml.core.model import InferenceConfig


ws = Workspace.from_config() 


env = Environment.from_conda_specification(name='sinkhole-env', file_path='environment.yml')


inference_config = InferenceConfig(entry_script='inference.py', environment=env)


deployment_config = AciWebservice.deploy_configuration(cpu_cores=1, memory_gb=1, auth_enabled=True)


model = Model(ws, 'sinkhole-model')
service = Model.deploy(workspace=ws,
                       name='sinkhole-service-new',
                       models=[model],
                       inference_config=inference_config,
                       deployment_config=deployment_config)

service.wait_for_deployment(show_output=True)
print(service.state)
print(service.scoring_uri)
print(service.swagger_uri)
print(service.get_keys())
