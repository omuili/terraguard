from azureml.core import Workspace, Webservice

ws = Workspace.from_config() 
service = Webservice(name='sinkhole-service-new', workspace=ws)
service.delete()
