import os
import subprocess
from flask import Flask, request, render_template, jsonify
import pandas as pd
from pyproj import Transformer
from azure.storage.blob import BlobServiceClient
from utils import read_raster_files, predict, process_predictions

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
STATIC_FOLDER = 'static/maps'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(STATIC_FOLDER, exist_ok=True)

# Azure Blob Storage setup
AZURE_CONNECTION_STRING = ''
CONTAINER_NAME = 'sinkholedata'
blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
container_client = blob_service_client.get_container_client(CONTAINER_NAME)

# Azure ML endpoint information
AZURE_ML_SCORING_URI = ''
AZURE_ML_API_KEY = ''

csv_path = None
raster_paths = []

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload_csv', methods=['POST'])
def upload_csv():
    global csv_path
    csv_file = request.files['sinkhole_data']
    csv_path = os.path.join(UPLOAD_FOLDER, csv_file.filename)
    csv_file.save(csv_path)
    return jsonify({'status': 'success', 'message': 'CSV uploaded successfully'}), 200

@app.route('/upload_rasters', methods=['POST'])
def upload_rasters():
    global raster_paths
    raster_files = request.files.getlist('rasterfile')
    raster_paths = []
    for raster_file in raster_files:
        raster_path = os.path.join(UPLOAD_FOLDER, raster_file.filename)
        raster_file.save(raster_path)
        raster_paths.append(raster_path)
    return jsonify({'status': 'success', 'message': 'Rasters uploaded successfully'}), 200

@app.route('/train_model', methods=['POST'])
def run_analysis():
    global csv_path, raster_paths
    iterations = int(request.form['iterations'])
    output_folder = request.form['output_folder']
    os.makedirs(output_folder, exist_ok=True)

    if not csv_path or not raster_paths:
        return jsonify({'status': 'error', 'message': 'Please upload or select both CSV and raster files before running the analysis'}), 400

    # Extract blob names from file paths
    csv_blob_name = os.path.basename(csv_path)
    raster_blob_names = ','.join([os.path.basename(path) for path in raster_paths])

    # Run the training script
    subprocess.run([
        'python', 'train.py',
        '--csv_blob_name', csv_blob_name,
        '--raster_blob_names', raster_blob_names,
        '--iterations', str(iterations),
        '--output_folder', output_folder,
        '--container_name', CONTAINER_NAME,
        '--connection_string', AZURE_CONNECTION_STRING
    ], check=True)

    return jsonify({'status': 'success', 'message': 'Model training initiated'}), 200

@app.route('/datasets', methods=['GET'])
def list_datasets():
    blob_list = container_client.list_blobs()
    datasets = [blob.name for blob in blob_list]
    return jsonify(datasets), 200

@app.route('/load_dataset', methods=['GET'])
def load_dataset():
    dataset_name = request.args.get('name')
    if not dataset_name:
        return jsonify({"status": "error", "message": "Dataset name is required"}), 400

    blob_client = container_client.get_blob_client(blob=dataset_name)
    download_stream = blob_client.download_blob()
    dataset_content = download_stream.readall()
    
    # Save the dataset to the upload folder
    dataset_path = os.path.join(UPLOAD_FOLDER, dataset_name)
    with open(dataset_path, 'wb') as file:
        file.write(dataset_content)

    if dataset_name.endswith('.csv'):
        global csv_path
        csv_path = dataset_path
        sinkhole_data_df = pd.read_csv(csv_path)
        transformer = Transformer.from_crs("epsg:", "epsg:", always_xy=True)
        sinkhole_data_df[['lon', 'lat']] = sinkhole_data_df.apply(
            lambda row: pd.Series(transformer.transform(row['X'], row['Y'])), axis=1
        )
        preview_data = sinkhole_data_df.head().to_dict(orient='records')
    else:
        global raster_paths
        if not raster_paths:
            raster_paths = []
        raster_paths.append(dataset_path)
        # For simplicity, we'll just return the filename as preview data for rasters
        preview_data = {"file": dataset_name}

    return jsonify({
        'status': 'success',
        'preview_data': preview_data
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
