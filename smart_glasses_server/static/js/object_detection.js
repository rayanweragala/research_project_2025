// Object Detection JavaScript
const API_BASE_URL = 'http://localhost:5005/api';
let detectionInterval = null;
let isDetecting = false;

document.addEventListener('DOMContentLoaded', function() {
    console.log('Object Detection System initialized');
    checkHealth();
    loadTranslations();
    loadStatistics();
});

async function checkHealth() {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        const data = await response.json();
        console.log('Health check:', data);
        
        if (data.model_loaded) {
            updateStatus('online', 'Model loaded - Ready');
        } else {
            updateStatus('offline', 'Model not loaded');
        }
    } catch (error) {
        console.error('Health check failed:', error);
        updateStatus('offline', 'Server offline');
    }
}

async function startDetection() {
    if (isDetecting) return;
    
    try {
        updateStatus('offline', 'Starting camera...');
        
        const response = await fetch(`${API_BASE_URL}/camera/start`, {
            method: 'POST'
        });
        const result = await response.json();
        
        if (result.success) {
            isDetecting = true;
            updateStatus('online', 'Detection active');
            detectionInterval = setInterval(getDetection, 1000);
        } else {
            updateStatus('offline', 'Failed to start: ' + result.message);
        }
    } catch (error) {
        console.error('Start error:', error);
        updateStatus('offline', 'Error starting');
    }
}

async function stopDetection() {
    if (!isDetecting) return;
    
    try {
        if (detectionInterval) {
            clearInterval(detectionInterval);
            detectionInterval = null;
        }
        
        await fetch(`${API_BASE_URL}/camera/stop`, {
            method: 'POST'
        });
        
        isDetecting = false;
        updateStatus('offline', 'Detection stopped');
        
        const cameraFeed = document.getElementById('cameraFeed');
        cameraFeed.innerHTML = '<span>Camera feed will appear here</span>';
        
        const detectionsDiv = document.getElementById('currentDetections');
        detectionsDiv.innerHTML = '<p class="text-muted text-sm">No active detections</p>';
    } catch (error) {
        console.error('Stop error:', error);
    }
}

async function getDetection() {
    try {
        const response = await fetch(`${API_BASE_URL}/camera/detect`);
        const data = await response.json();
        
        if (data.success && data.image) {
            const cameraFeed = document.getElementById('cameraFeed');
            cameraFeed.innerHTML = `<img src="data:image/jpeg;base64,${data.image}" alt="Camera feed">`;
            
            displayDetections(data.detections);
            loadStatistics();
        }
    } catch (error) {
        console.error('Detection error:', error);
    }
}

function displayDetections(detections) {
    const container = document.getElementById('currentDetections');
    
    if (!detections || detections.length === 0) {
        container.innerHTML = '<p class="text-muted text-sm">No objects detected</p>';
        return;
    }
    
    let html = '';
    detections.forEach(det => {
        const confidence = (det.confidence * 100).toFixed(1);
        html += `
            <div class="detection-item">
                <div>
                    <div class="detection-label">${det.label_sinhala}</div>
                    <div class="detection-sublabel">${det.label_english}</div>
                </div>
                <div class="detection-confidence">${confidence}%</div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

async function loadStatistics() {
    try {
        const response = await fetch(`${API_BASE_URL}/statistics`);
        const data = await response.json();
        
        if (data.stats) {
            document.getElementById('totalDetections').textContent = data.stats.total_detections || 0;
            document.getElementById('avgTime').textContent = (data.stats.avg_processing_time * 1000).toFixed(1) + 'ms';
            document.getElementById('totalRequests').textContent = data.stats.total_requests || 0;
            
            const uniqueCount = Object.keys(data.objects_detected || {}).length;
            document.getElementById('uniqueObjects').textContent = uniqueCount;
        }
    } catch (error) {
        console.error('Statistics error:', error);
    }
}

async function loadTranslations() {
    try {
        const response = await fetch(`${API_BASE_URL}/translations`);
        const data = await response.json();
        
        if (data.translations) {
            displayTranslations(data.translations);
        }
    } catch (error) {
        console.error('Translations error:', error);
    }
}

function displayTranslations(translations) {
    const container = document.getElementById('translationsList');
    const entries = Object.entries(translations);
    entries.sort((a, b) => a[0].localeCompare(b[0]));
    
    let html = '';
    entries.forEach(([english, sinhala]) => {
        html += `
            <div class="translation-card" data-english="${english.toLowerCase()}">
                <div class="translation-sinhala">${sinhala}</div>
                <div class="translation-english">${english}</div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

function filterTranslations() {
    const searchTerm = document.getElementById('searchInput').value.toLowerCase();
    const cards = document.querySelectorAll('.translation-card');
    
    cards.forEach(card => {
        const english = card.getAttribute('data-english');
        card.style.display = english.includes(searchTerm) ? 'block' : 'none';
    });
}

function updateStatus(status, text) {
    const indicator = document.getElementById('statusIndicator');
    const statusText = document.getElementById('statusText');
    
    indicator.className = 'status-indicator status-' + status;
    statusText.textContent = text;
}

window.addEventListener('beforeunload', function() {
    if (isDetecting) {
        stopDetection();
    }
});