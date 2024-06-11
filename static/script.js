// Set the Cesium Ion access token
Cesium.Ion.defaultAccessToken = 'your-cesium-ion-token';

// Initialize CesiumJS viewer with imagery and geocoding
const viewer = new Cesium.Viewer('cesiumContainer', {
    imageryProvider: new Cesium.IonImageryProvider({ assetId: 2 }), // Bing Maps Aerial imagery
    baseLayerPicker: true, // Allows users to switch base imagery layers
    geocoder: true,        // Enables geocoding for location search
    timeline: false,       // Disables the timeline
    animation: false       // Disables animation controls
});

function showTab(tabName) {
    const tabs = document.querySelectorAll('.tab-content');
    tabs.forEach(tab => tab.classList.remove('active'));
    document.querySelectorAll('.tab').forEach(tab => tab.classList.remove('active'));
    document.getElementById(`${tabName}-tab`).classList.add('active');
    document.querySelector(`[onclick="showTab('${tabName}')"]`).classList.add('active');
}

function toggleFullscreen() {
    const fullscreenMap = document.getElementById('fullscreenMap');
    const fullscreenMapFrame = document.getElementById('fullscreenMapFrame');
    const expandButton = document.getElementById('expandButton');
    const closeFullscreenButton = document.getElementById('closeFullscreenButton');

    if (fullscreenMap.style.display === 'none' || fullscreenMap.style.display === '') {
        fullscreenMap.style.display = 'block';
        fullscreenMapFrame.src = mapUrl;
        expandButton.style.display = 'none';
        closeFullscreenButton.style.display = 'block';
    } else {
        fullscreenMap.style.display = 'none';
        fullscreenMapFrame.src = '';
        expandButton.style.display = 'block';
        closeFullscreenButton.style.display = 'none';
    }
}

function checkMapExists(url, callback) {
    fetch(url, { method: 'HEAD' })
        .then(response => {
            if (response.ok) {
                callback(true);
            } else {
                callback(false);
            }
        })
        .catch(() => {
            callback(false);
        });
}

document.getElementById('csvUploadForm').onsubmit = function(event) {
    event.preventDefault();
    const formData = new FormData(this);
    fetch(this.action, {
        method: this.method,
        body: formData
    }).then(response => response.json()).then(data => {
        alert('CSV uploaded successfully');
    }).catch(error => {
        console.error('Error:', error);
    });
};

document.getElementById('rasterUploadForm').onsubmit = function(event) {
    event.preventDefault();
    const formData = new FormData(this);
    fetch(this.action, {
        method: this.method,
        body: formData
    }).then(response => response.json()).then(data => {
        alert('Rasters uploaded successfully');
    }).catch(error => {
        console.error('Error:', error);
    });
};

document.getElementById('analysisForm').onsubmit = function(event) {
    event.preventDefault();
    const formData = new FormData(this);
    fetch(this.action, {
        method: this.method,
        body: formData
    }).then(response => response.json()).then(data => {
        if (data.status === 'success') {
            document.getElementById('trainAccuracy').innerText = `Training Accuracy: ${data.train_accuracy}`;
            document.getElementById('testAccuracy').innerText = `Test Accuracy: ${data.test_accuracy}`;
            const mapUrl = data.map_url;
            console.log("Map URL:", mapUrl);  // Debugging line
            document.getElementById('mapFrame').src = mapUrl;
            document.getElementById('mapFrame').style.display = 'block';
            document.getElementById('expandButton').style.display = 'block';
        } else {
            alert(data.message);
        }
    }).catch(error => {
        console.error('Error:', error);
    });
};

// Fetch datasets and populate the dropdowns
async function fetchDatasets() {
    const response = await fetch('/datasets');
    const datasets = await response.json();
    const csvSelect = document.getElementById('existingCsvSelect');
    const rasterSelect = document.getElementById('existingRasterSelect');
    datasets.forEach(dataset => {
        const option = document.createElement('option');
        option.value = dataset;
        option.textContent = dataset;
        if (dataset.endsWith('.csv')) {
            csvSelect.appendChild(option);
        } else if (dataset.endsWith('.tif') || dataset.endsWith('.grid')) {
            rasterSelect.appendChild(option);
        }
    });
}

document.getElementById('loadCsvButton').addEventListener('click', async function() {
    const selectedCsv = document.getElementById('existingCsvSelect').value;
    const response = await fetch(`/load_dataset?name=${selectedCsv}`);
    const data = await response.json();
    if (data.status === 'success') {
        console.log(data.preview_data);
        alert('CSV loaded successfully');
    } else {
        alert('Failed to load CSV');
    }
});

document.getElementById('loadRasterButton').addEventListener('click', async function() {
    const selectedRasters = Array.from(document.getElementById('existingRasterSelect').selectedOptions).map(option => option.value);
    const rasterPromises = selectedRasters.map(async raster => {
        const response = await fetch(`/load_dataset?name=${raster}`);
        return response.json();
    });
    Promise.all(rasterPromises).then(results => {
        results.forEach(result => {
            if (result.status === 'success') {
                console.log(result.preview_data);
            } else {
                alert('Failed to load one or more rasters');
            }
        });
        alert('Rasters loaded successfully');
    }).catch(error => {
        console.error('Error:', error);
    });
});

// Fetch datasets on page load
window.onload = fetchDatasets;
