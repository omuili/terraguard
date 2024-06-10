import argparse
import os
import pandas as pd
import numpy as np
from azureml.core.run import Run
from azure.storage.blob import BlobServiceClient
from catboost import CatBoostClassifier, Pool
from sklearn.model_selection import train_test_split
from utils import process_raster, read_raster_files, resample_raster

def download_blob(blob_client, download_path):
    with open(download_path, 'wb') as f:
        f.write(blob_client.download_blob().readall())

def train_and_predict(sinkhole_data_df, rasters_data, iterations, output_folder):
    print(f"Output folder: {output_folder}")
    processed_rasters = [process_raster(data, nodata) for data, profile, nodata, transform, path in rasters_data]

    geology_data, geology_profile, geology_nodata, geology_transform, geology_path = rasters_data[0]
    resampled_rasters = [resample_raster(data, transform, profile['crs'], geology_data.shape, geology_transform, geology_profile['crs']) for data, profile, nodata, transform, path in rasters_data[1:]]
    data_ar = np.stack([geology_data] + resampled_rasters)

    xmin, xmax = geology_transform[2], geology_transform[2] + geology_transform[0] * geology_data.shape[1]
    ymin, ymax = geology_transform[5] + geology_transform[4] * geology_data.shape[0], geology_transform[5]
    cell_x = geology_transform[0]
    cell_y = -geology_transform[4]

    search_dist = 300
    pred_rh_inside = np.empty(shape=(len(geology_data), len(geology_data[0]))) * np.nan
    nulls = np.isnan(data_ar[0])
    non_min_ar = np.array(nulls, copy=True)
    min_ar = non_min_ar * -1
    x_ar = np.linspace(start=xmin, stop=xmax, num=geology_data.shape[1])
    y_ar = np.linspace(start=ymin, stop=ymax, num=geology_data.shape[0])

    for x, y in sinkhole_data_df[['X', 'Y']].values:
        ix = np.argmin(np.abs(x_ar - x))
        iy = np.argmin(np.abs(np.flip(y_ar) - y))
        x_buff = int(search_dist / cell_x)
        y_buff = int(search_dist / cell_y)
        non_min_ar[iy - y_buff:iy + y_buff, ix - x_buff:ix + x_buff] = True
        min_ar[iy - y_buff:iy + y_buff, ix - x_buff:ix + x_buff] = 1

    min_idx = np.argwhere(min_ar.flatten() == 1)[:, 0]
    inside_dat = np.zeros(shape=(len(min_idx), data_ar.shape[0]))
    for i in range(data_ar.shape[0]):
        inside_dat[:, i] = data_ar[i].flatten()[min_idx]

    non_min_idx = np.argwhere(non_min_ar.flatten() == False)[:, 0]
    non_min_idx = np.random.choice(non_min_idx, len(min_idx), replace=True)
    outside_dat = np.zeros(shape=(len(inside_dat), data_ar.shape[0]))
    for i in range(data_ar.shape[0]):
        outside_dat[:, i] = data_ar[i].flatten()[non_min_idx]

    inside_lab = np.array(['min' for _ in range(len(inside_dat))])
    outside_lab = np.array(['non_min' for _ in range(len(outside_dat))])
    mod_dat = np.concatenate([inside_dat, outside_dat])
    mod_lab = np.concatenate([inside_lab, outside_lab])

    if len(mod_dat) > 0 and len(mod_lab) > 0:
        X_train, X_test, y_train, y_test = train_test_split(mod_dat, mod_lab, test_size=0.3, shuffle=True)
        train_pool = Pool(data=X_train, label=y_train)
        test_pool = Pool(data=X_test, label=y_test)

        params = {
            'loss_function': 'MultiClass',
            'eval_metric': 'Accuracy',
            'verbose': 200,
            'iterations': iterations,
            'task_type': 'CPU'
        }

        model_rh = CatBoostClassifier(**params)
        model_rh.fit(train_pool, eval_set=test_pool)

        train_acc = model_rh.get_best_score()['learn']['Accuracy']
        test_acc = model_rh.get_best_score()['validation']['Accuracy']

        # Save the model to the outputs directory
        model_path = os.path.join(output_folder, 'model.pkl')
        model_rh.save_model(model_path)
        print(f"Model saved to: {model_path}")
        print(f"Training Accuracy: {train_acc}")
        print(f"Test Accuracy: {test_acc}")
    else:
        print("Insufficient data for training")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv_blob_name', type=str, help='Name of the CSV blob.')
    parser.add_argument('--raster_blob_names', type=str, help='Comma-separated names of raster blobs.')
    parser.add_argument('--iterations', type=int, default=1000, help='Number of iterations.')
    parser.add_argument('--output_folder', type=str, help='Output folder path.')
    parser.add_argument('--container_name', type=str, help='Azure Blob container name.')
    parser.add_argument('--connection_string', type=str, help='Azure Blob Storage connection string.')

    args = parser.parse_args()

    # Create the output folder if it doesn't exist
    output_folder = 'outputs'
    os.makedirs(output_folder, exist_ok=True)
    
    blob_service_client = BlobServiceClient.from_connection_string(args.connection_string)
    container_client = blob_service_client.get_container_client(args.container_name)

    # Download the CSV file
    csv_blob_client = container_client.get_blob_client(args.csv_blob_name)
    csv_path = os.path.join(output_folder, args.csv_blob_name)
    download_blob(csv_blob_client, csv_path)

    # Download raster files
    raster_blob_names = args.raster_blob_names.split(',')
    raster_paths = []
    for raster_blob_name in raster_blob_names:
        raster_blob_client = container_client.get_blob_client(raster_blob_name)
        raster_path = os.path.join(output_folder, raster_blob_name)
        download_blob(raster_blob_client, raster_path)
        raster_paths.append(raster_path)

    sinkhole_data_df = pd.read_csv(csv_path)
    rasters_data = read_raster_files(raster_paths)

    train_and_predict(
        sinkhole_data_df, 
        rasters_data, 
        args.iterations, 
        output_folder
    )
