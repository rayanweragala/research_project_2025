from flask import Flask, request, jsonify, Response
import cv2
import numpy as np
import base64
import json
import threading
import time
import logging
from queue import Queue
import socket

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

class SmartGlassesCameraServer:
    def __init__(self):
        self.camera = None
        self.is_streaming = False
        self.connected_clients = set()
        self.frame_queue = Queue(maxsize=10)
        self.latest_frame = None
        self.camera_lock = threading.Lock()

        self.camera_width = 640
        self.camera_height = 480
        self.fps = 15
        
        self.init_camera()
        
    def init_camera(self):
        """Initialize camera with optimal settings"""
        try:
            # Try different camera indices (0, 1, 2) in case of multiple cameras
            for camera_index in range(3):
                self.camera = cv2.VideoCapture(camera_index)
                if self.camera.isOpened():
                    print(f"Camera {camera_index} opened successfully")
                    break
            
            if not self.camera.isOpened():
                raise Exception("No camera found")

            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.camera_width)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.camera_height)
            self.camera.set(cv2.CAP_PROP_FPS, self.fps)

            self.camera.set(cv2.CAP_PROP_AUTOFOCUS, 1)
            self.camera.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
            
            print(f"Camera initialized: {self.camera_width}x{self.camera_height} @ {self.fps}fps")
            
        except Exception as e:
            print(f"Failed to initialize camera: {e}")
            self.camera = None
    
    def start_streaming(self):
        """Start camera streaming in a separate thread"""
        if self.camera is None:
            return False
            
        if self.is_streaming:
            return True
            
        self.is_streaming = True
        self.camera_thread = threading.Thread(target=self._camera_capture_loop)
        self.camera_thread.daemon = True
        self.camera_thread.start()
        
        print("Camera streaming started")
        return True
    
    def stop_streaming(self):
        """Stop camera streaming"""
        self.is_streaming = False
        self.connected_clients.clear()
        
        if hasattr(self, 'camera_thread'):
            self.camera_thread.join(timeout=2)
            
        print("Camera streaming stopped")
    
    def _camera_capture_loop(self):
        """Main camera capture loop"""
        frame_count = 0
        start_time = time.time()
        
        while self.is_streaming and self.camera is not None:
            try:
                with self.camera_lock:
                    ret, frame = self.camera.read()
                
                if not ret:
                    print("Failed to read frame from camera")
                    time.sleep(0.1)
                    continue

                frame = cv2.flip(frame, 1)

                timestamp = time.time()
                frame_info = f"Frame: {frame_count} | FPS: {frame_count/(time.time()-start_time):.1f}"
                cv2.putText(frame, frame_info, (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                self.latest_frame = frame.copy()
                
                try:
                    self.frame_queue.put_nowait({
                        'frame': frame,
                        'timestamp': timestamp,
                        'frame_count': frame_count
                    })
                except:
                    pass
                
                frame_count += 1

                time.sleep(1.0 / self.fps)
                
            except Exception as e:
                print(f"Error in camera capture loop: {e}")
                time.sleep(0.1)
    
    def get_latest_frame_base64(self):
        """Get the latest frame as base64 encoded JPEG"""
        if self.latest_frame is None:
            return None
            
        try:
            _, buffer = cv2.imencode('.jpg', self.latest_frame, 
                                   [cv2.IMWRITE_JPEG_QUALITY, 85])
            
            frame_base64 = base64.b64encode(buffer).decode('utf-8')
            
            return {
                'image': frame_base64,
                'timestamp': time.time(),
                'width': self.latest_frame.shape[1],
                'height': self.latest_frame.shape[0]
            }
            
        except Exception as e:
            print(f"Error encoding frame: {e}")
            return None
    
    def add_client(self, client_id):
        """Add a connected client"""
        self.connected_clients.add(client_id)
        print(f"Client {client_id} connected. Total clients: {len(self.connected_clients)}")
    
    def remove_client(self, client_id):
        """Remove a disconnected client"""
        self.connected_clients.discard(client_id)
        print(f"Client {client_id} disconnected. Total clients: {len(self.connected_clients)}")

        if len(self.connected_clients) == 0:
            self.stop_streaming()
    
    def cleanup(self):
        """Cleanup resources"""
        self.stop_streaming()
        
        if self.camera is not None:
            with self.camera_lock:
                self.camera.release()
            self.camera = None
        
        print("Camera server cleaned up")

camera_server = SmartGlassesCameraServer()

@app.route('/api/camera/health', methods=['GET'])
def camera_health():
    """Check camera server health"""
    print("Health check requested")
    response = {
        'status': 'healthy',
        'camera_available': camera_server.camera is not None,
        'is_streaming': camera_server.is_streaming,
        'connected_clients': len(camera_server.connected_clients),
        'resolution': f"{camera_server.camera_width}x{camera_server.camera_height}",
        'fps': camera_server.fps
    }
    print(f"Health response: {response}")
    return jsonify(response)

@app.route('/api/camera/connect', methods=['POST'])
def connect_client():
    """Connect a client to the camera stream"""
    try:
        data = request.json or {}
        client_id = data.get('client_id', 'unknown')
        print(f"Connect request from client: {client_id}")
        
        if camera_server.camera is None:
            return jsonify({
                'success': False,
                'message': 'Camera not available'
            }), 500

        if not camera_server.start_streaming():
            return jsonify({
                'success': False,
                'message': 'Failed to start camera streaming'
            }), 500
        
        camera_server.add_client(client_id)
        
        return jsonify({
            'success': True,
            'message': f'Client {client_id} connected successfully',
            'stream_url': '/api/camera/frame',
            'resolution': f"{camera_server.camera_width}x{camera_server.camera_height}",
            'fps': camera_server.fps
        })
        
    except Exception as e:
        print(f"Connect error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/camera/disconnect', methods=['POST'])
def disconnect_client():
    """Disconnect a client from the camera stream"""
    try:
        data = request.json or {}
        client_id = data.get('client_id', 'unknown')
        print(f"Disconnect request from client: {client_id}")
        
        camera_server.remove_client(client_id)
        
        return jsonify({
            'success': True,
            'message': f'Client {client_id} disconnected'
        })
        
    except Exception as e:
        print(f"Disconnect error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/camera/frame', methods=['GET'])
def get_camera_frame():
    """Get the latest camera frame as base64 encoded image"""
    try:
        print("Frame request received")
        if not camera_server.is_streaming:
            return jsonify({'error': 'Camera not streaming'}), 400
        
        frame_data = camera_server.get_latest_frame_base64()
        
        if frame_data is None:
            return jsonify({'error': 'No frame available'}), 404
        
        return jsonify({
            'success': True,
            'frame_data': frame_data,
            'timestamp': time.time()
        })
        
    except Exception as e:
        print(f"Frame error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/camera/preview', methods=['GET'])
def camera_preview():
    """Get camera preview stream for web browser testing"""
    print("Preview stream requested")
    def generate_frames():
        while camera_server.is_streaming:
            try:
                if not camera_server.frame_queue.empty():
                    frame_info = camera_server.frame_queue.get_nowait()
                    frame = frame_info['frame']

                    _, buffer = cv2.imencode('.jpg', frame, 
                                           [cv2.IMWRITE_JPEG_QUALITY, 80])
                    
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                
                time.sleep(1.0 / camera_server.fps)
                
            except Exception as e:
                print(f"Preview stream error: {e}")
                break
    
    if not camera_server.is_streaming:
        camera_server.start_streaming()
        time.sleep(1)
    
    return Response(generate_frames(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/camera/stop', methods=['POST'])
def stop_camera():
    """Stop camera streaming completely"""
    try:
        camera_server.stop_streaming()
        return jsonify({
            'success': True,
            'message': 'Camera streaming stopped'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/camera/settings', methods=['GET', 'POST'])
def camera_settings():
    """Get or update camera settings"""
    if request.method == 'GET':
        return jsonify({
            'width': camera_server.camera_width,
            'height': camera_server.camera_height,
            'fps': camera_server.fps,
            'is_streaming': camera_server.is_streaming
        })
    
    elif request.method == 'POST':
        try:
            data = request.json

            if 'fps' in data:
                camera_server.fps = max(1, min(30, int(data['fps'])))
            
            return jsonify({
                'success': True,
                'message': 'Settings updated',
                'settings': {
                    'width': camera_server.camera_width,
                    'height': camera_server.camera_height,
                    'fps': camera_server.fps
                }
            })
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500

def get_local_ip():
    """Get local IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return "127.0.0.1"

# Fixed HTML with proper JavaScript function definitions
INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Smart Glasses Camera Simulation</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            min-height: 100vh;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }
        
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        
        .header h1 {
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
        }
        
        .subtitle {
            opacity: 0.8;
            font-size: 1.1em;
            margin-top: 10px;
        }
        
        .grid {
            display: grid;
            grid-template-columns: 1fr 300px;
            gap: 30px;
            margin-top: 30px;
        }
        
        .camera-section {
            background: rgba(0, 0, 0, 0.2);
            border-radius: 15px;
            padding: 20px;
            text-align: center;
        }
        
        #cameraStream {
            width: 100%;
            max-width: 640px;
            height: auto;
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
            background: #333;
        }
        
        .controls-section {
            background: rgba(0, 0, 0, 0.2);
            border-radius: 15px;
            padding: 20px;
        }
        
        .status-card {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 20px;
        }
        
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }
        
        .status-online { background-color: #4CAF50; }
        .status-offline { background-color: #f44336; }
        .status-warning { background-color: #ff9800; }
        
        .btn {
            background: linear-gradient(45deg, #ff6b6b, #ee5a24);
            border: none;
            color: white;
            padding: 12px 24px;
            border-radius: 25px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 500;
            transition: all 0.3s ease;
            width: 100%;
            margin: 10px 0;
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
        }
        
        .btn:active {
            transform: translateY(0);
        }
        
        .btn-success {
            background: linear-gradient(45deg, #4CAF50, #45a049);
        }
        
        .btn-warning {
            background: linear-gradient(45deg, #ff9800, #f57c00);
        }
        
        .info-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin-top: 15px;
        }
        
        .info-item {
            background: rgba(255, 255, 255, 0.1);
            padding: 10px;
            border-radius: 8px;
            text-align: center;
        }
        
        .info-label {
            font-size: 0.8em;
            opacity: 0.7;
            margin-bottom: 5px;
        }
        
        .info-value {
            font-weight: bold;
            font-size: 1.1em;
        }
        
        .connection-info {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
            padding: 15px;
            margin-top: 20px;
        }
        
        .connection-info h4 {
            margin-top: 0;
            color: #ffd700;
        }
        
        .ip-address {
            font-family: 'Courier New', monospace;
            background: rgba(0, 0, 0, 0.3);
            padding: 8px;
            border-radius: 5px;
            margin: 5px 0;
            word-break: break-all;
        }
        
        .debug-log {
            background: rgba(0, 0, 0, 0.3);
            border-radius: 10px;
            padding: 15px;
            margin-top: 20px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            max-height: 200px;
            overflow-y: auto;
        }
        
        @media (max-width: 768px) {
            .grid {
                grid-template-columns: 1fr;
            }
            
            .header h1 {
                font-size: 2em;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎥 Smart Glasses Camera Simulation</h1>
            <div class="subtitle">Testing interface for face recognition system</div>
        </div>
        
        <div class="grid">
            <div class="camera-section">
                <h3>Live Camera Feed</h3>
                <img id="cameraStream" src="/api/camera/preview" alt="Camera Stream" 
                     onerror="this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjQwIiBoZWlnaHQ9IjQ4MCIgdmlld0JveD0iMCAwIDY0MCA0ODAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSI2NDAiIGhlaWdodD0iNDgwIiBmaWxsPSIjMzMzIi8+Cjx0ZXh0IHg9IjMyMCIgeT0iMjQwIiBmaWxsPSIjNjY2IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMjQiPkNhbWVyYSBOb3QgQXZhaWxhYmxlPC90ZXh0Pgo8L3N2Zz4K'">
                <div style="margin-top: 15px; opacity: 0.7;">
                    Resolution: <span id="resolution">640x480</span> | 
                    FPS: <span id="fps">15</span>
                </div>
            </div>
            
            <div class="controls-section">
                <div class="status-card">
                    <h4>Server Status</h4>
                    <div id="serverStatus">
                        <span class="status-indicator status-warning"></span>
                        Checking...
                    </div>
                </div>
                
                <div class="info-grid">
                    <div class="info-item">
                        <div class="info-label">Connected Clients</div>
                        <div class="info-value" id="clientCount">-</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Camera Status</div>
                        <div class="info-value" id="cameraStatus">-</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Streaming</div>
                        <div class="info-value" id="streamingStatus">-</div>
                    </div>
                    <div class="info-item">
                        <div class="info-label">Server Health</div>
                        <div class="info-value" id="healthStatus">-</div>
                    </div>
                </div>
                
                <button class="btn btn-success" onclick="window.refreshStatus ? window.refreshStatus() : refreshStatus()">
                    🔄 Refresh Status
                </button>
                
                <button class="btn" onclick="window.testConnection ? window.testConnection() : testConnection()">
                    🔗 Test Connection
                </button>
                
                <button class="btn btn-warning" onclick="window.restartStream ? window.restartStream() : restartStream()">
                    📹 Restart Stream
                </button>

                <button class="btn" onclick="window.stopCamera ? window.stopCamera() : stopCamera()">
                    ⏹️ Stop Camera
                </button>
                
                <div class="connection-info">
                    <h4>📱 Android App Setup</h4>
                    <div>Update your MockSmartGlassesConnector:</div>
                    <div class="ip-address" id="serverUrl">Loading...</div>
                    <div style="font-size: 0.9em; margin-top: 10px; opacity: 0.8;">
                        Replace the CAMERA_SERVER_URL in your Android code with the URL above.
                    </div>
                </div>
                
            </div>
        </div>
    </div>

    <script>
    
        var serverUrl = window.location.origin;
        var healthCheckInterval;
        
        function logDebug(message) {
            try {
                var debugLog = document.getElementById('debugLog');
                if (debugLog) {
                    var timestamp = new Date().toLocaleTimeString();
                    debugLog.innerHTML += '[' + timestamp + '] ' + message + '<br>';
                    debugLog.scrollTop = debugLog.scrollHeight;
                }
                console.log('[' + new Date().toLocaleTimeString() + '] ' + message);
            } catch (error) {
                console.error('Error logging debug message:', error);
            }
        }

        function refreshStatus() {
            logDebug('Manual refresh requested...');
            checkServerHealth();
  
            var img = document.getElementById('cameraStream');
            if (img) {
                var currentSrc = img.src;
                img.src = '';
                setTimeout(function() {
                    img.src = currentSrc.split('?')[0] + '?t=' + Date.now();
                    logDebug('Camera stream refreshed');
                }, 100);
            }
        }

        function stopCamera() {
            logDebug('Stop camera requested...');
            
            fetch('/api/camera/stop', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(function(response) {
                return response.json();
            })
            .then(function(data) {
                logDebug('Stop camera response: ' + JSON.stringify(data));
                if (data.success) {
                    var img = document.getElementById('cameraStream');
                    if (img) {
                        img.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjQwIiBoZWlnaHQ9IjQ4MCIgdmlld0JveD0iMCAwIDY0MCA0ODAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSI2NDAiIGhlaWdodD0iNDgwIiBmaWxsPSIjMzMzIi8+Cjx0ZXh0IHg9IjMyMCIgeT0iMjQwIiBmaWxsPSIjNjY2IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMjQiPkNhbWVyYSBTdG9wcGVkPC90ZXh0Pgo8L3N2Zz4K';
                    }
                    
                    var streamingStatus = document.getElementById('streamingStatus');
                    if (streamingStatus) {
                        streamingStatus.textContent = '⚪ Stopped';
                    }
                    
                    alert('📴 Camera streaming stopped successfully.');
                    logDebug('Camera stopped successfully');
                } else {
                    alert('❌ Failed to stop camera: ' + (data.message || 'Unknown error'));
                    logDebug('Failed to stop camera: ' + (data.message || 'Unknown error'));
                }
            })
            .catch(function(error) {
                logDebug('Stop camera error: ' + error.message);
                alert('❌ Error stopping camera: ' + error.message);
            });
        }
        
        function testConnection() {
            var testClientId = 'web_test_' + Date.now();
            logDebug('Testing connection with client ID: ' + testClientId);
            
            fetch('/api/camera/connect', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    client_id: testClientId
                })
            })
            .then(function(response) {
                logDebug('Connect response status: ' + response.status);
                return response.json();
            })
            .then(function(data) {
                logDebug('Connect response: ' + JSON.stringify(data));
                if (data.success) {
                    alert('✅ Connection test successful!\n' + data.message);
                    logDebug('Connection test PASSED');
                    
                    setTimeout(function() {
                        fetch('/api/camera/disconnect', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json'
                            },
                            body: JSON.stringify({
                                client_id: testClientId
                            })
                        }).then(function() {
                            logDebug('Test client disconnected');
                        }).catch(function(err) {
                            logDebug('Error disconnecting test client: ' + err.message);
                        });
                    }, 1000);
                } else {
                    alert('❌ Connection test failed!\n' + (data.message || 'Unknown error'));
                    logDebug('Connection test FAILED: ' + (data.message || 'Unknown error'));
                }
            })
            .catch(function(error) {
                logDebug('Connection test error: ' + error.message);
                alert('❌ Connection test error!\n' + error.message);
            });
        }
        
        function restartStream() {
            logDebug('Stream restart requested...');

            fetch('/api/camera/stop', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            })
            .then(function() {
                setTimeout(function() {
                    refreshStatus();
                    var img = document.getElementById('cameraStream');
                    if (img) {
                        img.src = '/api/camera/preview?t=' + Date.now();
                    }
                    alert('🔄 Stream restarted. Check the camera feed.');
                    logDebug('Stream restart completed');
                }, 1000);
            })
            .catch(function(error) {
                logDebug('Error during restart: ' + error.message);
                refreshStatus();
            });
        }
        
        function checkServerHealth() {
            logDebug('Making health check request...');
            fetch('/api/camera/health')
                .then(function(response) {
                    logDebug('Health check response status: ' + response.status);
                    if (!response.ok) {
                        throw new Error('HTTP ' + response.status);
                    }
                    return response.json();
                })
                .then(function(data) {
                    logDebug('Health check data received: ' + JSON.stringify(data));
                    updateStatusUI(data);
                })
                .catch(function(error) {
                    logDebug('Health check failed: ' + error.message);
                    console.error('Health check failed:', error);
                    updateStatusUI({
                        status: 'error',
                        camera_available: false,
                        is_streaming: false,
                        connected_clients: 0
                    });
                });
        }
        
        function updateStatusUI(data) {
            try {
                logDebug('Updating UI with health data...');
                
                var serverStatus = document.getElementById('serverStatus');
                var clientCount = document.getElementById('clientCount');
                var cameraStatus = document.getElementById('cameraStatus');
                var streamingStatus = document.getElementById('streamingStatus');
                var healthStatus = document.getElementById('healthStatus');
                var resolution = document.getElementById('resolution');
                var fps = document.getElementById('fps');

                if (data.status === 'healthy') {
                    if (serverStatus) {
                        serverStatus.innerHTML = '<span class="status-indicator status-online"></span>Server Online';
                    }
                    if (healthStatus) {
                        healthStatus.textContent = '✅ Healthy';
                    }
                    logDebug('Server status: HEALTHY');
                } else {
                    if (serverStatus) {
                        serverStatus.innerHTML = '<span class="status-indicator status-offline"></span>Server Offline';
                    }
                    if (healthStatus) {
                        healthStatus.textContent = '❌ Error';
                    }
                    logDebug('Server status: ERROR');
                }

                if (clientCount) {
                    clientCount.textContent = data.connected_clients || 0;
                }
                
                if (cameraStatus) {
                    cameraStatus.textContent = data.camera_available ? '✅ Available' : '❌ No Camera';
                }
                
                if (streamingStatus) {
                    streamingStatus.textContent = data.is_streaming ? '🔴 Live' : '⚪ Stopped';
                }
                
                if (data.resolution && resolution) {
                    resolution.textContent = data.resolution;
                }
                
                if (data.fps && fps) {
                    fps.textContent = data.fps;
                }
                
            } catch (error) {
                logDebug('Error updating UI: ' + error.message);
                console.error('Error updating UI:', error);
            }
        }

        function initializePage() {
            try {
                logDebug('Initializing page...');
                
                var serverUrlElement = document.getElementById('serverUrl');
                if (serverUrlElement) {
                    serverUrlElement.textContent = serverUrl;
                }
                logDebug('Server URL detected: ' + serverUrl);

                checkServerHealth();

                if (healthCheckInterval) {
                    clearInterval(healthCheckInterval);
                }
                healthCheckInterval = setInterval(checkServerHealth, 5000);
                
                var cameraStream = document.getElementById('cameraStream');
                if (cameraStream) {
                    cameraStream.onerror = function() {
                        logDebug('Camera stream error - camera may not be available');
                        this.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjQwIiBoZWlnaHQ9IjQ4MCIgdmlld0JveD0iMCAwIDY0MCA0ODAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSI2NDAiIGhlaWdodD0iNDgwIiBmaWxsPSIjMzMzIi8+Cjx0ZXh0IHg9IjMyMCIgeT0iMjQwIiBmaWxsPSIjNjY2IiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMjQiPkNhbWVyYSBOb3QgQXZhaWxhYmxlPC90ZXh0Pgo8L3N2Zz4K';
                    };
                }
                
                var buttons = document.querySelectorAll('.btn');
                for (var i = 0; i < buttons.length; i++) {
                    buttons[i].addEventListener('click', function() {
                        var btn = this;
                        btn.style.transform = 'scale(0.95)';
                        setTimeout(function() {
                            btn.style.transform = '';
                        }, 150);
                    });
                }
                
                logDebug('Page initialization complete');
                
            } catch (error) {
                logDebug('Error during initialization: ' + error.message);
                console.error('Initialization error:', error);
            }
        }

        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initializePage);
        } else {
            initializePage();
        }
        
        window.addEventListener('load', initializePage);
        
        window.addEventListener('beforeunload', function() {
            if (healthCheckInterval) {
                clearInterval(healthCheckInterval);
            }
        });
        
        window.refreshStatus = refreshStatus;
        window.stopCamera = stopCamera;
        window.testConnection = testConnection;
        window.restartStream = restartStream;
        window.checkServerHealth = checkServerHealth;
        
        logDebug('JavaScript functions defined and ready');
    </script>
    
    <script>

        if (typeof refreshStatus === 'undefined') {
            window.refreshStatus = function() {
                console.log('Refresh Status clicked');
                fetch('/api/camera/health')
                    .then(function(response) { return response.json(); })
                    .then(function(data) {
                        console.log('Health check:', data);
                        location.reload();
                    })
                    .catch(function(error) {
                        console.error('Error:', error);
                        alert('Error checking server health');
                    });
            };
        }
        
        if (typeof stopCamera === 'undefined') {
            window.stopCamera = function() {
                console.log('Stop Camera clicked');
                fetch('/api/camera/stop', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                })
                .then(function(response) { return response.json(); })
                .then(function(data) {
                    console.log('Stop camera:', data);
                    alert(data.success ? '✅ Camera stopped' : '❌ Failed to stop camera');
                    if (data.success) {
                        document.getElementById('cameraStream').src = '';
                    }
                })
                .catch(function(error) {
                    console.error('Error:', error);
                    alert('Error stopping camera');
                });
            };
        }
        
        if (typeof testConnection === 'undefined') {
            window.testConnection = function() {
                console.log('Test Connection clicked');
                var clientId = 'test_' + Date.now();
                fetch('/api/camera/connect', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ client_id: clientId })
                })
                .then(function(response) { return response.json(); })
                .then(function(data) {
                    console.log('Connection test:', data);
                    alert(data.success ? '✅ Connection successful!' : '❌ Connection failed!');
                })
                .catch(function(error) {
                    console.error('Error:', error);
                    alert('❌ Connection test failed');
                });
            };
        }
        
        if (typeof restartStream === 'undefined') {
            window.restartStream = function() {
                console.log('Restart Stream clicked');
                fetch('/api/camera/stop', { method: 'POST' })
                    .then(function() {
                        setTimeout(function() {
                            document.getElementById('cameraStream').src = '/api/camera/preview?t=' + Date.now();
                            alert('🔄 Stream restarted');
                        }, 1000);
                    })
                    .catch(function(error) {
                        console.error('Error:', error);
                        alert('Error restarting stream');
                    });
            };
        }
        
        console.log('Backup functions loaded successfully');
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Serve the main control panel interface"""
    return INDEX_HTML

if __name__ == '__main__':
    print("="*60)
    print("🎥 Smart Glasses Camera Simulation Server")
    print("="*60)
    print(f"Camera Status: {'✅ Available' if camera_server.camera else '❌ Not Available'}")
    
    local_ip = get_local_ip()
    port = 5001
    
    print(f"\n📱 Android App Configuration:")
    print(f"   Server IP: {local_ip}")
    print(f"   Server Port: {port}")
    print(f"   Full URL: http://{local_ip}:{port}")
    
    print(f"\n🌐 Web Preview:")
    print(f"   Control Panel: http://{local_ip}:{port}")
    print(f"   Camera Preview: http://{local_ip}:{port}/api/camera/preview")
    print(f"   Health Check: http://{local_ip}:{port}/api/camera/health")
    
    print(f"\n⚙️  API Endpoints:")
    print(f"   Connect: POST /api/camera/connect")
    print(f"   Get Frame: GET /api/camera/frame")
    print(f"   Disconnect: POST /api/camera/disconnect")
    print(f"   Stop Camera: POST /api/camera/stop")
    
    print("\n" + "="*60)
    print("Server starting... Press Ctrl+C to stop")
    print("="*60)
    
    try:
        app.run(
            host='0.0.0.0',
            port=port,
            debug=False,
            threaded=True
        )
    except KeyboardInterrupt:
        print("\nShutting down camera server...")
        camera_server.cleanup()
        print("Camera server stopped.")