import json
import numpy as np
from catboost import CatBoostClassifier
from azureml.core.model import Model

def init():
    global model
    model_path = Model.get_model_path('sinkhole-model')
    model = CatBoostClassifier()
    model.load_model(model_path)

def run(raw_data):
    try:
        data = np.array(json.loads(raw_data)['data'])
        predictions = model.predict(data)
        return json.dumps({'predictions': predictions.tolist()})
    except Exception as e:
        error = str(e)
        return json.dumps({'error': error})
