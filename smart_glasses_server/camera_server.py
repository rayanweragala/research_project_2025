# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify, Response, send_from_directory
import cv2
import numpy as np
import base64
import json
import threading
import time
import logging
from queue import Queue
import socket
import os

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

@app.route('/')
def index():
    """Serve the main control panel interface"""
    return send_from_directory('.', 'index.html')

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
    
    if not os.path.exists('index.html'):
        print("⚠️  WARNING: index.html not found in current directory!")
        print("   Please save the HTML content to 'index.html' file")
    
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