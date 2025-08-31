# -*- coding: utf-8 -*-

# ============================================================
# DEPRECATED
# ============================================================

import warnings
warnings.warn(
    "This file is deprecated",
    DeprecationWarning
)

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
import subprocess

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
        
    @staticmethod
    def cleanup_camera_processes():
        """Kill any existing camera processes that might be blocking the camera"""
        try:
            subprocess.run(['sudo', 'pkill', '-f', 'libcamera'], capture_output=True, text=True)
            subprocess.run(['sudo', 'pkill', '-f', 'picamera2'], capture_output=True, text=True)
            time.sleep(1)
            print("Cleaned up existing camera processes")
        except Exception as e:
            print(f"Process cleanup warning: {e}")
        
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
                    time.sleep(2)
                except:
                    pass
            
            SmartGlassesCameraServer.cleanup_camera_processes()
            time.sleep(1)
            
            print("Initializing Raspberry Pi camera...")
            self.picamera2 = Picamera2()

            if self.picamera2 is None:
                print("Failed to create Picamera2 instance")
                return False

            try:
                camera_config = self.picamera2.create_preview_configuration(
                    main={"format": "RGB888", "size": (self.camera_width, self.camera_height)}
                )
            except Exception as e:
                camera_config = self.picamera2.create_preview_configuration(
                main={"size": (self.camera_width, self.camera_height)}
            )
                
            print(f"Camera config: {camera_config}")
            try:
                self.picamera2.configure(camera_config)
                print("Camera configured successfully")
            except Exception as e:
                print(f"Error configuring camera: {e}")
                return False
            
            self.rpi_camera_config = camera_config
            
            print("Starting RPi camera...")
            try:
                self.picamera2.start()
                print("Camera start() called")
            except Exception as e:
                print(f"Error starting camera: {e}")
                return False

            print("Waiting for camera to stabilize...")
            for i in range(10):
                time.sleep(1)
                print(f"Stabilization wait: {i+1}/10 seconds")
            
            
                if hasattr(self.picamera2, '_camera'):
                    camera_active = self.picamera2._camera is not None
                    print(f"Camera state check {i+1}: _camera exists = {camera_active}")
                    if camera_active:
                        print(f"Camera became active after {i+1} seconds")
                        break
                else:
                    print(f"Camera state check {i+1}: no _camera attribute yet")


            print(f"Camera object: {self.picamera2}")
            camera_started = hasattr(self.picamera2, '_camera') and self.picamera2._camera is not None
            print(f"Final camera started state: {camera_started}")
            if not camera_started:
                print("WARNING: Camera did not start properly, but attempting to continue...")

            print("Testing RPi camera capture...")
            
            test_frame = None
            for attempt in range(5):
                print(f"Capture attempt {attempt + 1}/5")
                try:
                    time.sleep(1)
                    test_frame = self.picamera2.capture_array()
                    print(f"Capture attempt {attempt + 1} result: {type(test_frame)} {test_frame.shape if test_frame is not None else 'None'}")
                    if test_frame is not None and test_frame.size > 0:
                        break
                except Exception as capture_e:
                    print(f"Capture attempt {attempt + 1} failed: {capture_e}")
                    time.sleep(2)
                    
            if test_frame is None:
                print("All capture attempts failed - test_frame is None")
                return False
                
            if test_frame.size == 0:
                print("Captured frame is empty")
                return False
                
            self.camera_mode = 'rpi'
            self.camera_index = 0
            print(f"RPi camera initialized successfully with index {self.camera_index}")
            return True
    
        except Exception as e:
            print(f"RPi camera initialization failed: {e}")
            print(f"Exception type: {type(e)}")
            import traceback
            traceback.print_exc()
        
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

            backends = [cv2.CAP_V4L2, cv2.CAP_ANY]

            for backend in backends:
                for camera_index in range(4):  # Check more indices
                    print(f"Trying USB camera {camera_index} with backend {backend}")

                    test_camera = cv2.VideoCapture(camera_index, backend)
                    if not test_camera.isOpened():
                        test_camera.release()
                        continue

                    ret, test_frame = test_camera.read()
                    test_camera.release()

                    if ret and test_frame is not None:
                        self.camera = cv2.VideoCapture(camera_index, backend)

                        if self.camera.isOpened():
                            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.camera_width)
                            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.camera_height)
                            self.camera.set(cv2.CAP_PROP_FPS, self.fps)
                            self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)

                            ret, final_test = self.camera.read()
                            if ret and final_test is not None:
                                self.camera_index = camera_index
                                self.camera_mode = 'usb'
                                print(f"USB camera {camera_index} initialized successfully")
                                return True
                            else:
                                self.camera.release()
                                self.camera = None

            print("No working USB camera found")
            return False

        except Exception as e:
            print(f"Failed to initialize USB camera: {e}")
            if self.camera:
                self.camera.release()
                self.camera = None
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
        print(f"start_streaming called - current state: streaming={self.is_streaming}, thread_alive={self.camera_thread.is_alive() if self.camera_thread else False}")
    
        if self.is_streaming and self.camera_thread and self.camera_thread.is_alive():
            print("Camera already streaming and thread is alive")
            return True
            
        if self.is_streaming:
            print("Stopping existing stream before starting new one...")
            self.stop_streaming()
            time.sleep(1)

        if not self.init_camera():
            print("Failed to initialize camera")
            return False
            
        print("Setting streaming flag and starting thread...")
        self.is_streaming = True
        self.camera_thread = threading.Thread(target=self._camera_capture_loop)
        self.camera_thread.daemon = True
        self.camera_thread.start()
        
        time.sleep(0.5)
        if not self.camera_thread.is_alive():
            print("Camera thread failed to start!")
            self.is_streaming = False
            return False
    
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
        max_failures = 5
        thread_name = threading.current_thread().name

        print(f"[{thread_name}] Starting camera capture loop (mode: {self.camera_mode})")

        if self.camera_mode == 'rpi' and self.picamera2:
            print(f"[{thread_name}] Pre-loop camera state verification...")
        
            camera_ready = hasattr(self.picamera2, '_camera') and self.picamera2._camera is not None
            print(f"[{thread_name}] Camera ready state: {camera_ready}")
        
            if not camera_ready:
                print(f"[{thread_name}] Camera not ready, attempting restart...")
                try:
                    
                    self.picamera2.start()
                    time.sleep(3)
                
                    camera_ready = hasattr(self.picamera2, '_camera') and self.picamera2._camera is not None
                    print(f"[{thread_name}] After restart, camera ready: {camera_ready}")
                
                    if not camera_ready:
                        print(f"[{thread_name}] Camera restart failed, exiting loop")
                        self.is_streaming = False
                        return
                    
                except Exception as e:
                    print(f"[{thread_name}] Camera restart error: {e}")
                    self.is_streaming = False
                    return
            
        while self.is_streaming:
            try:
                frame = None
            
                if self.camera_mode == 'rpi' and self.picamera2:
                    try:
                        if self.picamera2 is None:
                            print("RPi camera object became None")
                            break

                        if not hasattr(self.picamera2, '_camera') or self.picamera2._camera is None:
                            print("RPi camera stopped unexpectedly")
                            break

                        if self.picamera2._camera is None:
                            print("RPi camera _camera is None")
                            break

                        frame_rgb = self.picamera2.capture_array()
                        
                        if frame_rgb is None:
                            print(f"RPi camera capture returned None (attempt {consecutive_failures + 1})")
                            consecutive_failures += 1
                            time.sleep(0.1)
                            continue
                        
                        if frame_rgb.size == 0:
                            print(f"RPi camera capture returned empty array (attempt {consecutive_failures + 1})")
                            consecutive_failures += 1
                            time.sleep(0.1)
                            continue
                        
                        frame = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
                        consecutive_failures = 0
                    except Exception as e:
                        print(f"RPi camera capture error: {e}")
                        consecutive_failures += 1

                        if "not started" in str(e).lower():
                            print("Attempting to restart RPi camera...")
                            try:
                                self.picamera2.start()
                                time.sleep(2)
                                continue
                            except:
                                print("Failed to restart RPi camera")
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
                        consecutive_failures += 1
                        frame = None
                else:
                    print(f"[{thread_name}] No valid camera mode")
                    break
            
                if frame is None:
                    if consecutive_failures >= max_failures:
                        print(f"[{thread_name}] Maximum failures reached, stopping")
                        break
                    time.sleep(0.2)
                    continue

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
                    if not self.frame_queue.empty():
                        self.frame_queue.get_nowait()  
                    self.frame_queue.put_nowait({
                        'frame': frame,
                        'timestamp': timestamp,
                        'frame_count': frame_count,
                        'camera_mode': self.camera_mode
                    })
                except:
                    pass
            
                frame_count += 1

                sleep_time = max(0.01, 1.0 / self.fps)
                time.sleep(sleep_time)
            
            except Exception as e:
                print(f"Error in camera capture loop: {e}")
                consecutive_failures += 1
                if consecutive_failures >= max_failures:
                    print("Too many errors in capture loop, stopping")
                    break
                time.sleep(0.1)
    
        print(f"Camera capture loop ended (mode: {self.camera_mode})")
        
    
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
        
        if client_id in camera_server.connected_clients:
            print(f"Client {client_id} already connected")
            return jsonify({
                'success': True,
                'message': f'Client {client_id} already connected',
                'stream_url': '/api/camera/frame',
                'camera_mode': camera_server.camera_mode,
                'resolution': f"{camera_server.camera_width}x{camera_server.camera_height}",
                'fps': camera_server.fps,
                'camera_index': camera_server.camera_index,
                'optimized_for': 'smart_glasses'
            })
        
        camera_server.add_client(client_id)

        if not camera_server.start_streaming():
            print("Starting camera streaming for new client...")
            if not camera_server.start_streaming():
                camera_server.remove_client(client_id)  
                return jsonify({
                    'success': False,
                    'message': 'Failed to start camera streaming - no camera available'
                }), 500
            else:
                print("Camera already streaming, client added to existing stream")
        
        
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
        if not camera_server.is_streaming:
            print(f"Frame request denied - camera not streaming. Current state: streaming={camera_server.is_streaming}, mode={camera_server.camera_mode}")
            return jsonify({
                'success': False, 
                'error': 'Camera not streaming',
                'debug': {
                    'is_streaming': camera_server.is_streaming,
                    'camera_mode': camera_server.camera_mode,
                    'connected_clients': len(camera_server.connected_clients),
                    'has_latest_frame': camera_server.latest_frame is not None
                }
            }), 400
        
        frame_data = camera_server.get_latest_frame_base64()
        
        if frame_data is None:
            print("Frame request - no frame available")
            return jsonify({
                'success': False, 
                'error': 'No frame available',
                'debug': {
                    'is_streaming': camera_server.is_streaming,
                    'camera_mode': camera_server.camera_mode,
                    'latest_frame_exists': camera_server.latest_frame is not None
                }
            }), 404

        if hasattr(get_camera_frame, 'success_count'):
            get_camera_frame.success_count += 1
        else:
            get_camera_frame.success_count = 1
            
        if get_camera_frame.success_count % 20 == 0:
            print(f"Frame #{get_camera_frame.success_count} delivered successfully")
        
        return jsonify({
            'success': True,
            'frame_data': frame_data,
            'timestamp': time.time()
        })
        
    except Exception as e:
        print(f"Frame endpoint error: {e}")
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