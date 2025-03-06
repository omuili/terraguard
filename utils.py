import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling
import requests
import json

def process_raster(data, nodata): 
    data = data.astype('float32')
    data[data == nodata] = np.nan
    return data

def read_raster(file_path):
    with rasterio.open(file_path) as src:
        data = src.read(1)
        profile = src.profile
        nodata = src.nodata
        transform = src.transform
    return data, profile, nodata, transform

def read_raster_files(raster_paths):
    rasters_data = []
    for path in raster_paths:
        data, profile, nodata, transform = read_raster(path)
        rasters_data.append((data, profile, nodata, transform, path))
    return rasters_data

def resample_raster(src_data, src_transform, src_crs, dst_shape, dst_transform, dst_crs):
    resampled_data = np.empty(dst_shape, dtype='float32')
    reproject(
        source=src_data,
        destination=resampled_data,
        src_transform=src_transform,
        src_crs=src_crs,
        dst_transform=dst_transform,
        dst_crs=dst_crs,
        resampling=Resampling.nearest
    )
    return resampled_data

def predict(scoring_uri, api_key, input_data):
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    response = requests.post(scoring_uri, data=json.dumps(input_data), headers=headers)
    if response.status_code != 200:
        raise Exception(f"Request failed with status code {response.status_code}: {response.text}")
    return response.json()

def process_predictions(predictions, raster_paths):
    # Process the predictions to create a map or any other output
    results = []
    for i, prediction in enumerate(predictions):
        raster_path = raster_paths[i]
        results.append({
            'raster_path': raster_path,
            'prediction': prediction
        })
    return results
