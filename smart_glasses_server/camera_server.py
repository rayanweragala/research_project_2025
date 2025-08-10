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
from flask_cors import CORS

try:
    from picamera2 import Picamera2
    from libcamera import controls
    import libcamera
    RPI_CAMERA_AVAILABLE = True
    print("Picamera2 available - Raspberry Pi camera support enabled")
except ImportError:
    RPI_CAMERA_AVAILABLE = False
    print("Picamera2 not available - falling back to OpenCV camera") 

app = Flask(__name__)
CORS(app) 
logging.basicConfig(level=logging.INFO)

class CameraSingleton:
    """Singleton to ensure only one camera instance exists globally"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.picamera2 = None
            self.usb_camera = None
            self.camera_lock = threading.Lock()
            self._initialized = True
    
    def get_rpi_camera(self):
        """Get or create RPi camera instance"""
        with self.camera_lock:
            if self.picamera2 is None and RPI_CAMERA_AVAILABLE:
                try:
                    self.picamera2 = Picamera2()
                except Exception as e:
                    print(f"Failed to create RPi camera: {e}")
                    self.picamera2 = None
            return self.picamera2
    
    def get_usb_camera(self, index=0):
        """Get or create USB camera instance"""
        with self.camera_lock:
            if self.usb_camera is None:
                try:
                    self.usb_camera = cv2.VideoCapture(index)
                    if not self.usb_camera.isOpened():
                        self.usb_camera.release()
                        self.usb_camera = None
                except Exception as e:
                    print(f"Failed to create USB camera: {e}")
                    self.usb_camera = None
            return self.usb_camera
    
    def release_rpi_camera(self):
        """Release RPi camera"""
        with self.camera_lock:
            if self.picamera2 is not None:
                try:
                    if hasattr(self.picamera2, '_camera') and self.picamera2._camera is not None:
                        self.picamera2.stop()
                    self.picamera2.close()
                except Exception as e:
                    print(f"Error releasing RPi camera: {e}")
                finally:
                    self.picamera2 = None
    
    def release_usb_camera(self):
        """Release USB camera"""
        with self.camera_lock:
            if self.usb_camera is not None:
                try:
                    self.usb_camera.release()
                except Exception as e:
                    print(f"Error releasing USB camera: {e}")
                finally:
                    self.usb_camera = None
    
    def cleanup_all(self):
        """Cleanup all camera resources"""
        self.release_rpi_camera()
        self.release_usb_camera()

camera_singleton = CameraSingleton()

class SmartGlassesCameraServer:
    def __init__(self):
        self.camera = None
        self.is_streaming = False
        self.connected_clients = set()
        self.frame_queue = Queue(maxsize=10)
        self.latest_frame = None
        self.camera_lock = threading.Lock()
        self.camera_thread = None

        self.camera_width = 640
        self.camera_height = 480
        self.fps = 15
        self.camera_index = -1  
        self.picamera2 = None
        self.camera_mode = None
        self.rpi_camera_config = None
        
        
    def init_camera(self):
        """Initialize camera with RPi camera priority, falling back to USB"""
        
        if (self.camera is not None and self.camera_mode == 'usb') or (self.picamera2 is not None and self.camera_mode == 'rpi'):
            return True
        
        try:
            if self.init_rpi_camera():
                return True
            
            return self.init_usb_camera()
            
        except Exception as e:
            print(f"Failed to initialize any camera: {e}")
            self.release_camera()
            return False
        
    def init_rpi_camera(self):
        """Initialize Raspberry Pi camera with Picamera2"""

        try:
            if not RPI_CAMERA_AVAILABLE:
                print("Raspberry Pi camera support not available")
                return False
            
            if self.picamera2 is not None:
                try:
                    self.picamera2.stop()
                    self.picamera2.close()
                    self.picamera2 = None
                    time.sleep(0.5)
                except:
                    pass
            
            print("Initializing Raspberry Pi camera...")
            self.picamera2 = Picamera2()

            camera_config = self.picamera2.create_still_configuration(
                
                main={"format":"RGB888","size": (self.camera_width, self.camera_height)},
                controls={
                    "FrameRate":self.fps,
                }
            )

            self.picamera2.configure(camera_config)
            self.rpi_camera_config = camera_config

            self.picamera2.start()
            time.sleep(2)

            print("Testing RPi camera capture...")
            test_frame = self.picamera2.capture_array()

            if test_frame is None or test_frame.size > 0:
                print(f"RPi camera test frame shape: {test_frame.shape}")
                test_frame_bgr = cv2.cvtColor(test_frame, cv2.COLOR_RGB2BGR)
                mean_intensity = np.mean(test_frame_bgr)

                if 5 < mean_intensity < 250:
                    self.camera_mode = 'rpi'
                    self.camera_index = 0
                    print(f"Raspberry Pi camera initialized successfully")
                    print(f"Camera resolution: {test_frame.shape}")
                    print(f"Frame intensity: {mean_intensity:.1f}")
                    return True
                else:
                    print(f"RPi camera test frame has invalid intensity: {mean_intensity}")

            print("RPi camera test completed with warnings but proceeding...")
            self.camera_mode = 'rpi'
            self.camera_index = 0
            return True
        
        except Exception as e:
            print(f"RPi camera initialization failed: {e}")
            if self.picamera2:
                try:
                    self.picamera2.stop()
                    self.picamera2.close()
                    self.picamera2 = None
                except:
                    pass
            return False
        
    def init_usb_camera(self):
        """Initialize USB camera as fallback"""
        try:
            print("Initializing USB camera...")
        
            for camera_index in range(3):
                test_camera = cv2.VideoCapture(camera_index)
                if test_camera.isOpened():
                    test_camera.release() 
                    time.sleep(0.1) 
                
                    self.camera = cv2.VideoCapture(camera_index)
                    if self.camera.isOpened():
                        self.camera_index = camera_index
                        self.camera_mode = 'usb'
                        print(f"USB camera {camera_index} opened successfully")
                        break
                    else:
                        self.camera = None
        
            if self.camera is None or not self.camera.isOpened():
                print("No USB camera found")
                return False

            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.camera_width)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.camera_height)
            self.camera.set(cv2.CAP_PROP_FPS, self.fps)
            self.camera.set(cv2.CAP_PROP_AUTOFOCUS, 1)
            self.camera.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)

            ret, test_frame = self.camera.read()
            if not ret:
                self.release_camera()
                print("USB camera opened but cannot read frames")
                return False
        
            print(f"USB camera initialized: {self.camera_width}x{self.camera_height} @ {self.fps}fps")
            return True
        
        except Exception as e:
            print(f"Failed to initialize USB camera: {e}")
            self.release_camera()
            return False
    
    def release_camera(self):
        """Release camera resources (RPi or USB)"""
        try:
            with self.camera_lock:
                if self.picamera2 is not None:
                    print("Releasing RPi camera...")
                    try:
                        if hasattr(self.picamera2,'_camera'):
                            self.picamera2.stop()
                        self.picamera2.close()
                        self.picamera2 = None
                        print("RPi camera released successfully")
                    except Exception as e:
                        print(f"Error releasing RPi camera: {e}")
                        self.picamera2 = None

                if self.camera is not None:
                    print(f"Releasing USB camera {self.camera_index}")
                    try:
                        self.camera.release()
                        self.camera = None
                        print("USB camera released successfully")
                    except Exception as e:
                        print(f"Error releasing USB camera: {e}")
            
                self.camera_index = -1
                self.camera_mode = None
                time.sleep(1)
        except Exception as e:
            print(f"Error releasing camera: {e}")
    
    def start_streaming(self):
        """Start camera streaming in a separate thread"""
        if self.is_streaming:
            return True
            
        if not self.init_camera():
            return False
            
        self.is_streaming = True
        self.camera_thread = threading.Thread(target=self._camera_capture_loop)
        self.camera_thread.daemon = True
        self.camera_thread.start()
        
        print("Camera streaming started")
        return True
    
    def stop_streaming(self):
        """Stop camera streaming and release camera resources"""
        print("Stopping camera streaming...")
        self.is_streaming = False
        self.connected_clients.clear()
        
        if self.camera_thread is not None:
            self.camera_thread.join(timeout=3)
            if self.camera_thread.is_alive():
                print("Warning: Camera thread did not stop gracefully")
            self.camera_thread = None
        
        self.release_camera()
  
        self.latest_frame = None
        while not self.frame_queue.empty():
            try:
                self.frame_queue.get_nowait()
            except:
                break
                
        print("Camera streaming stopped and resources released")
    
    def _camera_capture_loop(self):
        """Main camera capture loop (RPi or USB)"""
        frame_count = 0
        start_time = time.time()
        consecutive_failures = 0
        max_failures = 10


        print(f"Starting camera capture loop (mode: {self.camera_mode})")
        
        while self.is_streaming:
            try:
                frame = None
            
                if self.camera_mode == 'rpi' and self.picamera2:
                    try:
                        if not hasattr(self.picamera2, '_camera') or self.picamera2._camera is None:
                            print("RPi camera stopped unexpectedly")
                            consecutive_failures += 1
                            time.sleep(0.1)
                            continue

                        frame_rgb = self.picamera2.capture_array()
                        if frame_rgb is not None and frame_rgb.size > 0:
                            frame = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
                        else:
                            print("RPi camera: Empty frame")
                            consecutive_failures += 1
                    except Exception as e:
                        print(f"RPi camera capture error: {e}")
                        consecutive_failures += 1
                        if "allocator" in str(e).lower() or "camera in running state" in str(e).lower():
                            print("Attempting camera recovery...")
                            try:
                                self.picamera2.stop()
                                time.sleep(0.5)
                                self.picamera2.start()
                                time.sleep(1)
                                continue
                            except:
                                print("Camera recovery failed")
                                break
                    
                elif self.camera_mode == 'usb' and self.camera:
                    try:
                        with self.camera_lock:
                            if self.camera is None:
                                break
                            ret, frame = self.camera.read()
                    
                        if not ret or frame is None:
                            print("USB camera: Failed to read frame")
                            consecutive_failures += 1
                            frame = None
                    except Exception as e:
                        print(f"USB camera capture error: {e}")
                        consecutive_failures += 1
                        frame = None
                else:
                    print("No camera available for capture")
                    break
            
                if frame is None:
                    if consecutive_failures >= max_failures:
                        print("Too many consecutive failures, stopping stream")
                        break
                    time.sleep(0.1)
                    continue

                consecutive_failures = 0

                frame = cv2.flip(frame, 1)

                timestamp = time.time()
                current_fps = frame_count/(time.time()-start_time) if (time.time()-start_time) > 0 else 0
                camera_info = f"Smart Glasses | Mode: {self.camera_mode.upper()} | "
                frame_info = f"Frame: {frame_count} | FPS: {current_fps:.1f}"
            
                cv2.putText(frame, camera_info, (10, 25), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                cv2.putText(frame, frame_info, (10, 50), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

                self.latest_frame = frame.copy()
        
                try:
                    self.frame_queue.get_nowait()  # Remove oldest
                    self.frame_queue.put_nowait({
                        'frame': frame,
                        'timestamp': timestamp,
                        'frame_count': frame_count,
                        'camera_mode': self.camera_mode
                        })
                except:
                    pass
            
                frame_count += 1

                sleep_time = 1.0 / self.fps
                if consecutive_failures > 0:
                    sleep_time *= (1 + consecutive_failures * 0.1)  # Slow down on errors
                
                time.sleep(sleep_time)
            
            except Exception as e:
                print(f"Error in camera capture loop: {e}")
                consecutive_failures += 1
                if consecutive_failures >= max_failures:
                    print("Too many errors in capture loop, stopping")
                    break
                time.sleep(0.1)
    
        print(f"Camera capture loop ended (mode: {self.camera_mode})")
        if self.camera_mode == 'rpi' and self.picamera2:
            try:
                self.picamera2.stop()
            except:
                pass
    
    def get_latest_frame_base64(self):
        """Get the latest frame as base64 encoded JPEG"""
        if self.latest_frame is None:
            return None
            
        try:
            quality = 90 if self.camera_mode == 'rpi' else 85
            _, buffer = cv2.imencode('.jpg', self.latest_frame, 
                               [cv2.IMWRITE_JPEG_QUALITY, quality])
        
            frame_base64 = base64.b64encode(buffer).decode('utf-8')
            
            return {
                'image': frame_base64,
                'timestamp': time.time(),
                'width': self.latest_frame.shape[1],
                'height': self.latest_frame.shape[0],
                'camera_mode': self.camera_mode,
                'quality': quality
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
            print("No clients connected, stopping stream")
            self.stop_streaming()
    
    def cleanup(self):
        """Cleanup resources"""
        print("Cleaning up camera server...")
        self.stop_streaming()
        print("Camera server cleanup complete")

camera_server = SmartGlassesCameraServer()

@app.route('/')
def index():
    """Serve the main control panel interface"""
    return send_from_directory('.', 'camera_server_index.html')

@app.route('/api/camera/health', methods=['GET'])
def camera_health():
    """Check camera server health with RPi camera info"""
    print("Health check requested")
    
    rpi_camera_available = False
    usb_camera_available = False

    if camera_server.is_streaming and camera_server.camera_mode == 'rpi':
        rpi_camera_available = True
    elif camera_server.is_streaming and camera_server.camera_mode == 'usb':
        usb_camera_available = True
    else:

        if RPI_CAMERA_AVAILABLE:
            try:
                test_picam = Picamera2()
                test_picam.close()
                rpi_camera_available = True
                time.sleep(0.1)
            except Exception as e:
                print(f"RPi camera test failed: {e}")
                pass

    if not rpi_camera_available:
        for i in range(3):
            test_cam = cv2.VideoCapture(i)
            if test_cam.isOpened():
                usb_camera_available = True
                test_cam.release()
                time.sleep(0.1)
                break    
    response = {
        'status': 'healthy',
        'rpi_camera_available': rpi_camera_available,
        'usb_camera_available': usb_camera_available,
        'camera_available': rpi_camera_available or usb_camera_available,
        'is_streaming': camera_server.is_streaming,
        'camera_mode': camera_server.camera_mode,
        'connected_clients': len(camera_server.connected_clients),
        'resolution': f"{camera_server.camera_width}x{camera_server.camera_height}",
        'fps': camera_server.fps,
        'camera_index': camera_server.camera_index if camera_server.camera_mode else -1,
        'picamera2_available': RPI_CAMERA_AVAILABLE
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
        
        if not camera_server.start_streaming():
            return jsonify({
                'success': False,
                'message': 'Failed to start camera streaming - no camera available'
            }), 500
        
        camera_server.add_client(client_id)
        
        return jsonify({
            'success': True,
            'message': f'Client {client_id} connected successfully',
            'stream_url': '/api/camera/frame',
            'camera_mode': camera_server.camera_mode,
            'resolution': f"{camera_server.camera_width}x{camera_server.camera_height}",
            'fps': camera_server.fps,
            'camera_index': camera_server.camera_index,
            'optimized_for': 'smart_glasses'
        })
        
    except Exception as e:
        print(f"Connect error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

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
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/camera/frame', methods=['GET'])
def get_camera_frame():
    """Get the latest camera frame as base64 encoded image"""
    try:
        print("Frame request received")
        if not camera_server.is_streaming:
            return jsonify({'success': False, 'error': 'Camera not streaming'}), 400
        
        frame_data = camera_server.get_latest_frame_base64()
        
        if frame_data is None:
            return jsonify({'success': False, 'error': 'No frame available'}), 404
        
        return jsonify({
            'success': True,
            'frame_data': frame_data,
            'timestamp': time.time()
        })
        
    except Exception as e:
        print(f"Frame error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/camera/preview', methods=['GET'])
def camera_preview():
    """Get camera preview stream for web browser testing"""
    print("Preview stream requested")
    
    def generate_frames():
        if not camera_server.is_streaming:
            if not camera_server.start_streaming():
                error_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(error_frame, "Camera Not Available", (150, 240), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
                _, buffer = cv2.imencode('.jpg', error_frame)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                return
            time.sleep(1)  
        
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
    
    return Response(generate_frames(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/camera/stop', methods=['POST'])
def stop_camera():
    """Stop camera streaming completely and release camera resources"""
    try:
        print("Stop camera request received")
        camera_server.stop_streaming()
        return jsonify({
            'success': True,
            'message': 'Camera streaming stopped and camera resources released'
        })
    except Exception as e:
        print(f"Stop camera error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/camera/restart', methods=['POST'])
def restart_camera():
    """Restart camera streaming"""
    try:
        print("Restart camera request received")
        camera_server.stop_streaming()
        time.sleep(1)
        
        if camera_server.start_streaming():
            return jsonify({
                'success': True,
                'message': 'Camera restarted successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to restart camera'
            }), 500
            
    except Exception as e:
        print(f"Restart camera error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/camera/settings', methods=['GET', 'POST'])
def camera_settings():
    """Get or update camera settings"""
    if request.method == 'GET':
        return jsonify({
            'width': camera_server.camera_width,
            'height': camera_server.camera_height,
            'fps': camera_server.fps,
            'is_streaming': camera_server.is_streaming,
            'camera_mode': camera_server.camera_mode,
            'camera_index': camera_server.camera_index,
            'rpi_camera_available': RPI_CAMERA_AVAILABLE,
            'optimizations': {
                'smart_glasses_mode': True,
                'enhanced_contrast': camera_server.camera_mode == 'rpi',
                'mirror_effect': True,
                'high_quality_encoding': camera_server.camera_mode == 'rpi'
            }
        })
    
    elif request.method == 'POST':
        try:
            data = request.json

            if 'fps' in data:
                new_fps = max(5, min(30, int(data['fps'])))
                if new_fps != camera_server.fps:
                    camera_server.fps = new_fps
                    settings_changed = True
                    print(f"FPS updated to: {new_fps}")

            if settings_changed and camera_server.is_streaming:
                print("Restarting camera to apply new settings...")
                camera_server.stop_streaming()
                time.sleep(0.5)
                camera_server.start_streaming()
            
            return jsonify({
                'success': True,
                'message': 'Settings updated for smart glasses',
                'settings': {
                    'width': camera_server.camera_width,
                    'height': camera_server.camera_height,
                    'fps': camera_server.fps,
                    'camera_mode': camera_server.camera_mode,
                    'camera_index': camera_server.camera_index,
                    'restart_required': settings_changed
                }
            })
            
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

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

import atexit
atexit.register(camera_server.cleanup)

if __name__ == '__main__':
    print("="*60)
    rpi_camera_available = False
    if RPI_CAMERA_AVAILABLE:
        try:
            test_picam = Picamera2()
            test_picam.close()
            rpi_camera_available = True
        except:
            pass
    usb_camera_available = False
    for i in range(3):
        test_cam = cv2.VideoCapture(i)
        if test_cam.isOpened():
            usb_camera_available = True
            test_cam.release()
            time.sleep(0.1)
            break

    print(f"RPi Camera Status: {'Available' if rpi_camera_available else 'Not Available'}")
    print(f"USB Camera Status: {'Available' if usb_camera_available else 'Not Available'}")
    print(f"Priority: RPi Camera -> USB Camera")
    
    if not (rpi_camera_available or usb_camera_available):
        print("WARNING: No cameras detected!")
        
    local_ip = get_local_ip()
    port = 5001
    
    print(f"\n App Configuration:")
    print(f"   Server IP: {local_ip}")
    print(f"   Server Port: {port}")
    print(f"   Full URL: http://{local_ip}:{port}")
    
    print(f"\n API Endpoints:")
    print(f"   Web Interface: GET /")
    print(f"   Health Check: GET /api/camera/health")
    print(f"   Connect Client: POST /api/camera/connect")
    print(f"   Get Frame: GET /api/camera/frame")
    print(f"   Preview Stream: GET /api/camera/preview")
    print(f"   Disconnect Client: POST /api/camera/disconnect")
    print(f"   Stop Camera: POST /api/camera/stop")
    print(f"   Restart Camera: POST /api/camera/restart")
    print(f"   Camera Settings: GET/POST /api/camera/settings")
    
    print(f"\n Checking dependencies...")
    
    try:
        import cv2
        print("OpenCV available")
    except ImportError:
        print("OpenCV not installed - pip install opencv-python")
    
    print("\n" + "="*60)
    print("Server starting... Press Ctrl+C to stop")
    print("="*60)
    
    if not os.path.exists('camera_server_index.html'):
        print("camera_server_index.html not found!")
    
    try:
        app.run(
            host='0.0.0.0',
            port=port,
            debug=False,
            threaded=True
        )
    except KeyboardInterrupt:
        print("\n\nShutting down camera server...")
        camera_server.cleanup()
        print("Camera server stopped and resources released.")