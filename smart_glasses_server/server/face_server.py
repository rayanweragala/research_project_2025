"""
Enhanced Face Recognition Server with Multi-Face Support
Place this in: smart_glasses_server/server/face_server.py
"""

import statistics
from flask import Flask, Response, request, jsonify, render_template
import cv2
import numpy as np
import base64
import json
import os
import sqlite3
from datetime import datetime, timedelta
import logging
import time
from flask_cors import CORS
import io
from PIL import Image
import PIL.Image
import sys
if not hasattr(PIL.Image, 'Image'):
    sys.modules['PIL.Image'].Image = PIL.Image
import traceback
import atexit
import threading
import socket
from collections import defaultdict, deque
import random

try:
    from picamera2 import Picamera2
    from libcamera import controls
    RPI_CAMERA_AVAILABLE = True
    print("Picamera2 available - Raspberry Pi camera support enabled")
except ImportError:
    RPI_CAMERA_AVAILABLE = False
    print("Picamera2 not available - falling back to OpenCV")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

BASE_DIR = '/opt/research_project'
TEMPLATES_DIR = '/opt/research_project/templates'
STATIC_DIR = '/opt/research_project/static'

app = Flask(
    __name__,
    template_folder=TEMPLATES_DIR,
    static_folder=STATIC_DIR
)
CORS(app)

PERSON_DESCRIPTIONS = [
    "{name} is here",
    "I see {name}",
    "That's {name}",
    "{name} detected",
    "Hello {name}",
    "I recognize {name}",
    "{name} is in front of you",
    "Found {name}"
]

MULTI_PERSON_TEMPLATES = [
    "I see {count} people: {names}",
    "Found {count} people - {names}",
    "{count} people detected: {names}",
    "Multiple people found: {names}",
    "I recognize {count} people: {names}"
]

UNKNOWN_TEMPLATES = [
    "I see {count} unknown person" if "{count}" == "1" else "I see {count} unknown people",
    "{count} unrecognized face detected" if "{count}" == "1" else "{count} unrecognized faces detected",
    "Found {count} unknown person" if "{count}" == "1" else "Found {count} unknown people"
]


class EnhancedFaceRecognitionServer:
    def __init__(self):
        self.model = None
        self.model_loaded = False
        self.db_path = "face_database.db"
        self.face_encodings = {}

        self.recognition_threshold = 0.40   
        self.quality_threshold = 0.10
        self.min_face_size = 40
        self.max_embeddings_per_person = 20

        self.max_faces_to_detect = 10
        self.min_face_distance = 50  
        
        self.recognition_cache = {}
        self.cache_duration = 2.0

        self.picamera2 = None
        self.camera_mode = None
        self.camera_width = 1920
        self.camera_height = 1080
        self.fps = 30
        self.camera = None
        self.camera_active = False
        self.camera_lock = threading.Lock()
        self.last_frame = None
        self.frame_capture_thread = None
        self.stop_capture = False
        self.camera_error = None
        
        self.processing_thread = None
        self.stop_processing = False
        self.last_recognition_result = None
        self.recognition_lock = threading.Lock()
        
        self.recognition_stats = {
            'total_requests': 0,
            'successful_recognitions': 0,
            'multi_face_detections': 0,
            'cache_hits': 0,
            'avg_processing_time': 0.0,
            'errors': 0
        }

        self.camera_settings = {
            'width': 640,
            'height': 480,
            'fps': 25,
            'brightness': 0.0,
            'contrast': 1.0,
            'saturation': 1.0
        }

        self.init_database()
        self.init_face_model()
        self.load_face_database()

    def init_database(self):
        """Initialize SQLite database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS people (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    photo_count INTEGER DEFAULT 0,
                    avg_quality REAL DEFAULT 0.0,
                    best_quality REAL DEFAULT 0.0,
                    registration_method TEXT DEFAULT 'single'
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS face_encodings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    person_id INTEGER,
                    encoding BLOB NOT NULL,
                    image_quality REAL DEFAULT 0.0,
                    weight REAL DEFAULT 1.0,
                    is_outlier BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (person_id) REFERENCES people (id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS recognition_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    person_name TEXT,
                    confidence REAL,
                    quality_score REAL DEFAULT 0.0,
                    processing_time REAL DEFAULT 0.0,
                    method_used TEXT DEFAULT 'standard',
                    face_count INTEGER DEFAULT 1,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    source TEXT DEFAULT 'realtime'
                )
            ''')
            
            conn.commit()
            conn.close()
            logging.info("Database initialized successfully")
            
        except Exception as e:
            logging.error(f"Database initialization error: {e}")

    def init_face_model(self):
        """Initialize InsightFace model"""
        try:
            logging.info("Initializing InsightFace model...")
            
            import insightface
            
            self.model = insightface.app.FaceAnalysis(
                providers=['CPUExecutionProvider'],
                allowed_modules=['detection', 'recognition']
            )
            self.model.prepare(ctx_id=0, det_size=(640, 640))
            
            test_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            test_faces = self.model.get(test_image)
            
            self.model_loaded = True
            logging.info("InsightFace model loaded successfully")
            return True
            
        except Exception as e:
            logging.error(f"Model initialization error: {e}")
            self.model_loaded = False
            return False

    def load_face_database(self):
        """Load face encodings from database - FIXED VERSION"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT p.name, fe.encoding, fe.image_quality, fe.weight, fe.is_outlier 
                FROM people p
                JOIN face_encodings fe ON p.id = fe.person_id
                WHERE fe.is_outlier = FALSE
                ORDER BY fe.image_quality DESC
            ''')
            
            results = cursor.fetchall()
            
            for name, encoding_blob, quality, weight, is_outlier in results:
                encoding = np.frombuffer(encoding_blob, dtype=np.float32)
                if name not in self.face_encodings:
                    self.face_encodings[name] = []
                
                try:
                    if isinstance(quality, bytes):
                        quality_float = float(np.frombuffer(quality, dtype=np.float32)[0])
                    elif quality is not None:
                        quality_float = float(quality)
                    else:
                        quality_float = 0.5
                        
                    if isinstance(weight, bytes):
                        weight_float = float(np.frombuffer(weight, dtype=np.float32)[0])
                    elif weight is not None:
                        weight_float = float(weight)
                    else:
                        weight_float = 1.0
                        
                except (TypeError, ValueError, IndexError) as e:
                    logging.warning(f"Invalid quality/weight for {name}: quality={type(quality)}, weight={type(weight)}, error={e}")
                    quality_float = 0.5
                    weight_float = 1.0
                
                self.face_encodings[name].append({
                    'encoding': encoding,
                    'quality': quality_float,
                    'weight': weight_float
                })
            
            conn.close()
            logging.info(f"Loaded {len(self.face_encodings)} people from database")
        
        except Exception as e:
            logging.error(f"Error loading face database: {e}")

    def recognize_multiple_faces(self, image):
        """Recognize all faces in an image - FIXED VERSION"""
        start_time = time.time()
        
        try:
            if not self.model_loaded:
                return {
                    'recognized': False,
                    'faces': [],
                    'face_count': 0,
                    'message': "Model not loaded",
                    'processing_time': time.time() - start_time
                }
            
            faces = self.model.get(image)
            
            if not faces:
                return {
                    'recognized': False,
                    'faces': [],
                    'face_count': 0,
                    'message': "No faces detected",
                    'processing_time': time.time() - start_time
                }
            
            recognized_faces = []
            unknown_count = 0
            
            for face in faces:
                bbox = face.bbox
                if not isinstance(bbox, np.ndarray):
                    bbox = np.array(bbox, dtype=np.float32)
                
                try:
                    x1, y1, x2, y2 = float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
                    face_area = (x2 - x1) * (y2 - y1)
                    image_area = float(image.shape[0] * image.shape[1])
                    size_ratio = face_area / image_area if image_area > 0 else 0
                except (IndexError, ValueError, TypeError) as e:
                    logging.error(f"Bbox calculation error: {e}, bbox={bbox}")
                    continue
                
                quality_score = min(1.0, size_ratio * 3.0 + 0.3)
                
                best_match = None
                best_confidence = 0.0
                
                encoding = face.embedding
                
                for name, stored_data in self.face_encodings.items():
                    confidences = []
                    
                    for data in stored_data:
                        stored_encoding = data['encoding']
                        
                        try:
                            stored_quality = float(data['quality'])
                        except (TypeError, ValueError):
                            logging.warning(f"Invalid quality value for {name}: {data['quality']}")
                            stored_quality = 0.5
                        
                        cosine_sim = np.dot(encoding, stored_encoding) / (
                            np.linalg.norm(encoding) * np.linalg.norm(stored_encoding)
                        )
                        
                        euclidean_dist = np.linalg.norm(encoding - stored_encoding)
                        euclidean_sim = 1.0 / (1.0 + euclidean_dist * 0.3)
                        
                        combined_similarity = (
                            cosine_sim * 0.6 + 
                            euclidean_sim * 0.4
                        )
                        
                        quality_factor = min(1.2, (quality_score * 1.1 + stored_quality * 0.9) / 1.5)
                        final_confidence = combined_similarity * quality_factor
                        
                        confidences.append(final_confidence)
                    
                    if confidences:
                        avg_confidence = sum(sorted(confidences, reverse=True)[:3]) / min(3, len(confidences))
                        
                        if avg_confidence > best_confidence:
                            best_confidence = avg_confidence
                            best_match = name
                
                face_result = {
                    'bbox': [x1, y1, x2, y2],
                    'quality_score': float(quality_score),
                    'confidence': float(best_confidence)
                }
                
                if best_confidence > 0.40:
                    face_result['recognized'] = True
                    face_result['name'] = best_match
                    face_result['confidence_level'] = self.get_confidence_level(best_confidence)
                else:
                    face_result['recognized'] = False
                    face_result['name'] = None
                    unknown_count += 1
                
                recognized_faces.append(face_result)
            
            recognized_names = [f['name'] for f in recognized_faces if f['recognized']]
            
            if recognized_names:
                if len(recognized_names) == 1:
                    template = random.choice(PERSON_DESCRIPTIONS)
                    message = template.format(name=recognized_names[0])
                else:
                    template = random.choice(MULTI_PERSON_TEMPLATES)
                    names_str = ", ".join(recognized_names[:-1]) + " and " + recognized_names[-1]
                    message = template.format(count=len(recognized_names), names=names_str)
                
                if unknown_count > 0:
                    message += f" plus {unknown_count} unknown"
            else:
                if unknown_count == 1:
                    message = "I see 1 unknown person"
                else:
                    message = f"I see {unknown_count} unknown people"
            
            processing_time = time.time() - start_time
            
            if len(recognized_faces) > 1:
                self.recognition_stats['multi_face_detections'] += 1
            
            return {
                'recognized': len(recognized_names) > 0,
                'faces': recognized_faces,
                'face_count': len(recognized_faces),
                'recognized_count': len(recognized_names),
                'unknown_count': unknown_count,
                'message': message,
                'processing_time': processing_time,
                'method_used': 'multi_face_recognition'
            }
            
        except Exception as e:
            logging.error(f"Multi-face recognition error: {e}")
            import traceback
            logging.error(traceback.format_exc())
            return {
                'recognized': False,
                'faces': [],
                'face_count': 0,
                'message': f"Error: {str(e)}",
                'processing_time': time.time() - start_time
            }

    def get_confidence_level(self, confidence):
        """Get confidence level description"""
        if confidence >= 0.85:
            return 'very_high'
        elif confidence >= 0.70:
            return 'high'
        elif confidence >= 0.50:
            return 'medium'
        elif confidence >= 0.35:
            return 'low'
        else:
            return 'very_low'

    def start_continuous_recognition(self):
        """Start continuous face recognition in background"""
        if self.processing_thread and self.processing_thread.is_alive():
            logging.info("Recognition thread already running")
            return
        
        self.stop_processing = False
        self.processing_thread = threading.Thread(
            target=self._continuous_recognition_loop,
            daemon=True
        )
        self.processing_thread.start()
        logging.info("Started continuous recognition thread")

    def stop_continuous_recognition(self):
        """Stop continuous recognition"""
        self.stop_processing = True
        if self.processing_thread:
            self.processing_thread.join(timeout=2.0)
        logging.info("Stopped continuous recognition thread")

    def _continuous_recognition_loop(self):
        """Background loop for continuous recognition"""
        while not self.stop_processing and self.camera_active:
            try:
                frame = self.capture_frame()
                if frame is not None:
                    processed_frame = self.preprocess_camera_frame(frame)
                    result = self.recognize_multiple_faces(processed_frame)
                    
                    with self.recognition_lock:
                        self.last_recognition_result = {
                            'result': result,
                            'timestamp': time.time(),
                            'frame': frame
                        }
                
                time.sleep(0.5) 
                
            except Exception as e:
                logging.error(f"Recognition loop error: {e}")
                time.sleep(1.0)

    def get_latest_recognition(self):
        """Get the latest recognition result"""
        with self.recognition_lock:
            if self.last_recognition_result:
                return self.last_recognition_result
        return None

    def add_person_enhanced(self, name, images_base64):
        """Enhanced person registration - FIXED VERSION"""
        try:
            if not self.model_loaded:
                return {
                    'success': False,
                    'message': 'Face recognition model not loaded',
                    'photos_processed': 0
                }
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT id FROM people WHERE name = ?", (name,))
            result = cursor.fetchone()
            
            if result:
                person_id = result[0]
                cursor.execute("DELETE FROM face_encodings WHERE person_id = ?", (person_id,))
            else:
                cursor.execute("INSERT INTO people (name, registration_method) VALUES (?, ?)", 
                            (name, 'enhanced'))
                person_id = cursor.lastrowid
            
            successful_encodings = []
            quality_scores = []
            
            for i, img_base64 in enumerate(images_base64):
                try:
                    img_data = base64.b64decode(img_base64)
                    nparr = np.frombuffer(img_data, np.uint8)
                    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    
                    if image is None:
                        continue

                    faces = self.model.get(image)
                    if not faces:
                        continue
                    
                    face = faces[0]  
                    encoding = face.embedding
                    
                    bbox = face.bbox
                    if not isinstance(bbox, np.ndarray):
                        bbox = np.array(bbox, dtype=np.float32)
                    
                    x1, y1, x2, y2 = float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
                    face_area = (x2 - x1) * (y2 - y1)
                    image_area = float(image.shape[0] * image.shape[1])
                    quality = min(1.0, (face_area / image_area) * 3.0 + 0.2)
                    
                    if quality > 0.20:
                        successful_encodings.append({
                            'encoding': encoding,
                            'quality': float(quality),  
                            'weight': float(quality * 1.2) 
                        })
                        quality_scores.append(float(quality))
                        
                except Exception as e:
                    logging.error(f"Error processing image {i+1}: {e}")
                    continue
            
            if len(successful_encodings) < 2:
                conn.rollback()
                conn.close()
                return {
                    'success': False,
                    'message': f'Need at least 2 good images. Got {len(successful_encodings)}',
                    'photos_processed': len(successful_encodings)
                }
            
            if len(successful_encodings) > 8:
                successful_encodings.sort(key=lambda x: x['quality'], reverse=True)
                successful_encodings = successful_encodings[:8]
            
            for enc_data in successful_encodings:
                encoding_blob = enc_data['encoding'].tobytes()
                cursor.execute('''
                    INSERT INTO face_encodings (person_id, encoding, image_quality, weight)
                    VALUES (?, ?, ?, ?)
                ''', (person_id, encoding_blob, float(enc_data['quality']), float(enc_data['weight'])))
            
            avg_quality = sum([e['quality'] for e in successful_encodings]) / len(successful_encodings)
            best_quality = max([e['quality'] for e in successful_encodings])
            
            cursor.execute('''
                UPDATE people SET photo_count = ?, avg_quality = ?, best_quality = ? WHERE id = ?
            ''', (len(successful_encodings), float(avg_quality), float(best_quality), person_id))

            self.face_encodings[name] = successful_encodings
            
            conn.commit()
            conn.close()
            
            self.recognition_cache.clear()
            
            return {
                'success': True,
                'message': f'Successfully registered {name} with {len(successful_encodings)} images',
                'photos_processed': len(successful_encodings),
                'avg_quality': round(float(avg_quality) * 100, 1),
                'best_quality': round(float(best_quality) * 100, 1)
            }
                    
        except Exception as e:
            if 'conn' in locals():
                conn.rollback()
                conn.close()
            logging.error(f"Registration error: {e}")
            logging.error(traceback.format_exc())
            return {
                'success': False,
                'message': f'Registration error: {str(e)}',
                'photos_processed': 0
            }

    def init_rpi_camera(self):
        """Initialize Raspberry Pi camera with Picamera2"""
        try:
            if not RPI_CAMERA_AVAILABLE:
                logging.warning("Picamera2 not available, falling back to USB")
                return self.init_usb_camera()
            
            logging.info("Initializing Raspberry pi camera...")

            self.picamera2 = Picamera2()

            
            config = self.picamera2.create_video_configuration(
                sensor={"output_size": (1280, 720)}, 
                main={"size": (1280, 720)},            
                lores={"size": (320, 240)},            
                buffer_count=4
            )

            self.picamera2.configure(config)
            
            self.picamera2.set_controls({
                "FrameRate": 60.0,
                "AeEnable": True,
                "AwbEnable": True,
                "Brightness": 0.0,
                "Contrast": 1.0,
                "Saturation": 1.0,
                "Sharpness": 1.2,
                "AeConstraintMode": 1,
                "AeMeteringMode": 0
        })

            self.picamera2.start()
            time.sleep(2)

            for i in range(5):
                frame = self.picamera2.capture_array()
                if frame is not None and frame.size:
                    bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    mean_intensity = np.mean(bgr)
                    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
                    sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
                    logging.info(f"Frame {i+1}: intensity={mean_intensity:.1f}, sharpness={sharpness:.1f}")
                    if 20 < mean_intensity < 230 and sharpness > 5:
                        self.camera_mode = 'rpi'
                        self.camera_width, self.camera_height = 1280, 720
                        logging.info("Raspberry Pi camera initialized successfully.")
                        return True
                time.sleep(0.5)

            self.picamera2.stop()
            self.picamera2.close()
            self.picamera2 = None
            logging.warning("Test frame failed; falling back to USB")
            return self.init_usb_camera()
                
        except Exception as e:
            logging.error(f"RPi camera initialization failed: {e}")
            if self.picamera2:
                try:
                    self.picamera2.stop()
                    self.picamera2.close()
                    self.picamera2 = None
                except:
                    pass
            return self.init_usb_camera()

        pass

    def init_usb_camera(self):
        """Initializing Opencv camera as fallback"""
        try:
            logging.info("Initializing USB camera")
            backends_to_try = [cv2.CAP_V4L2,cv2.CAP_ANY]

            for camera_id in [0,1,2]:
                logging.info(f"Trying USB camera {camera_id}...")

                for backend in backends_to_try:
                    try:
                        test_camera = cv2.VideoCapture(camera_id,backend)

                        if test_camera.isOpened():
                            test_camera.set(cv2.CAP_PROP_FRAME_WIDTH,640)
                            test_camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                            test_camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                            test_camera.set(cv2.CAP_PROP_FPS, 30)

                            ret, frame = test_camera.read()
                            test_camera.release()

                            if ret and frame is not None and np.mean(frame) > 15:
                                self.camera = cv2.VideoCapture(camera_id, backend)
                                self.configure_camera()
                                self.camera_mode = 'usb'
                                logging.info(f"USB camera {camera_id} initialized successfully")
                                return True
                        else:
                            test_camera.release()
                    except Exception as e:
                        logging.debug(f"USB camera {camera_id} backend {backend} failed: {e}")
                        continue
            logging.error("No working cameras found")
            return False
        except Exception as e:
            logging.error(f"USB camera initialization error: {e}")
            return False
        pass

    def start_camera(self):
        """ camera initialization with Rpi camera priority"""
        try:
            with self.camera_lock:
                if self.camera_active:
                    logging.info("Camera already active")
                    return True
            
                self.camera_error = None

                if self.init_rpi_camera():
                    self.camera_active = True
                    self.stop_capture = False

                    self.frame_capture_thread = threading.Thread(
                        target= self._continuous_capture,
                        daemon=True
                    )
                    self.frame_capture_thread.start()
                    time.sleep(0.5)
                    
                    self.start_continuous_recognition() 
                    logging.info("RPi camera started successfully")
                    return True
                
                if self.camera_mode == 'usb' and self.camera and self.camera.isOpened():
                    if self._validate_camera():
                        self.camera_active = True
                        self.stop_capture = False
                        
                        self.frame_capture_thread = threading.Thread(
                            target= self._continuous_capture,
                            daemon= True
                        )

                        self.frame_capture_thread.start()
                        time.sleep(0.5)

                        self.start_continuous_recognition()

                        logging.info("usb camera started successfully as fallback")
                        return True
                
                self.camera_error = "No working cameras found"
                logging.error(self.camera_error)
                return False
            
        except Exception as e:
            logging.error(f"Camera initialization error: {e}")
            self.camera_error = f"Camera initialization failed: {str(e)}"
            return False

    def stop_camera(self):
        """Stop camera and cleanup"""
        try:
            self.stop_continuous_recognition()
            
            with self.camera_lock:
                self.stop_capture = True
                self.camera_active = False

                if self.picamera2:
                    try:
                        self.picamera2.stop()
                        self.picamera2.close()
                        self.picamera2 = None
                        logging.info("RPi camera stopped")
                    except Exception as e:
                        logging.error(f"Error stopping RPi camera: {e}")

                if self.camera:
                    try:
                        self.camera.release()
                        self.camera = None
                        logging.info("USB camera stopped")
                    except Exception as e:
                        logging.error(f"Error stopping USB camera: {e}")

                self.last_frame = None
                self.camera_mode = None
             
                if self.frame_capture_thread and self.frame_capture_thread.is_alive():
                    self.frame_capture_thread.join(timeout=2.0)

            logging.info("Camera stopped successfully")
            return True
        
        except Exception as e:
            logging.error(f"Error stopping camera: {e}")
            return False
        
    def capture_frame(self):
        """Get the latest captured frame"""
        try:
            with self.camera_lock:
                if self.last_frame is not None:
                    return self.last_frame.copy()
                else:
                    logging.warning("No frame available in buffer")
                    return None
        except Exception as e:
            logging.error(f"Error capturing frame: {e}")
            return None

    def preprocess_camera_frame(self, frame):
        """Enhanced frame preprocessing for better recognition quality"""
        try:
            if frame is None:
                return None
        
            height, width = frame.shape[:2]
            if width > 1280:
                scale = 1280 / width
                new_width = int(width * scale)
                new_height = int(height * scale)
                frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
        
            denoised = cv2.bilateralFilter(frame, 9, 75, 75)
        
            lab = cv2.cvtColor(denoised, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            l = clahe.apply(l)
            enhanced = cv2.merge([l, a, b])
            enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
        
            kernel = np.array([[-1,-1,-1],
                               [-1, 9,-1],
                               [-1,-1,-1]])
            sharpened = cv2.filter2D(enhanced, -1, kernel)
        
            result = cv2.addWeighted(enhanced, 0.7, sharpened, 0.3, 0)
        
            return result
        except Exception as e:
            logging.error(f"Frame preprocessing error: {e}")
            return frame

    def frame_to_base64(self, frame):
        """Convert frame to base64 string"""
        try:
            if frame is None:
                return None
            
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if not ret:
                logging.error("Failed to encode frame to JPEG")
                return None
            
            jpg_as_text = base64.b64encode(buffer).decode('utf-8')
            return jpg_as_text
        
        except Exception as e:
            logging.error(f"Error converting frame to base64: {e}")
            return None

    def configure_camera(self):
        """Configure camera with validation"""
        try:
            if not self.camera or not self.camera.isOpened():
                return False  
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.camera_settings['width'])
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.camera_settings['height'])
            self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)  
            self.camera.set(cv2.CAP_PROP_FPS, self.camera_settings['fps'])

            optional_settings = [
                (cv2.CAP_PROP_BRIGHTNESS, self.camera_settings['brightness'] / 100.0),
                (cv2.CAP_PROP_CONTRAST, self.camera_settings['contrast'] / 100.0),
                (cv2.CAP_PROP_SATURATION, self.camera_settings['saturation'] / 100.0),
                (cv2.CAP_PROP_AUTO_EXPOSURE, 0.25), 
                (cv2.CAP_PROP_EXPOSURE, -6),
            ]
        
            for prop, value in optional_settings:
                try:
                    self.camera.set(prop, value)
                except:
                    pass
            
            logging.info("Camera configured successfully")
            return True
        
        except Exception as e:
            logging.error(f"Error configuring camera: {e}")
            return False

    def _validate_camera(self):
        """Validate camera produces good frames"""
        try:
            if not self.camera or not self.camera.isOpened():
                return False
            
            valid_frames = 0
            for i in range(10):
                ret, frame = self.camera.read()

                if ret and frame is not None and frame.size > 0:
                    mean_intensity = np.mean(frame)
                    if mean_intensity > 15 and mean_intensity < 240:
                        valid_frames += 1
                        logging.debug(f"Frame {i+1}: valid (mean intensity: {mean_intensity:.1f})")
                    else:
                        logging.warning(f"Frame {i+1}: Invalid intensity {mean_intensity:.1f}")
                else:
                    logging.warning(f"Frame {i+1}: Failed to capture")
                
                time.sleep(0.05)

            success_rate = valid_frames / 10
            logging.info(f"Camera validation: {valid_frames}/10 valid frames ({success_rate*100:.1f}%)")
        
            return success_rate >= 0.6
        
        except Exception as e:
            logging.error(f"Camera validation error: {e}")
            return False

    def _continuous_capture(self):
        """Continuously capture frames in background thread (RPi or USB)"""
        frame_count = 0
        error_count = 0
        max_errors = 10
        last_good_frame_time = time.time()

        logging.info(f"Starting continuous capture thread (mode: {self.camera_mode})")

        while not self.stop_capture and error_count < max_errors:
            try:
                if self.camera_mode == 'rpi' and self.picamera2:
                    try:
                        frame_rgb = self.picamera2.capture_array()
                        if frame_rgb is not None and frame_rgb.size > 0:
                            frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)  
                            mean_intensity = np.mean(frame_bgr)

                            if 15 < mean_intensity < 240:
                                with self.camera_lock:
                                    self.last_frame = frame_bgr.copy()
                                frame_count += 1
                                error_count = 0
                                last_good_frame_time = time.time()

                                if frame_count % 100 == 0:
                                    logging.info(f"RPi camera: captured {frame_count} frames")
                            else:
                                error_count += 1
                                logging.warning(f"RPi camera: Invalid frame mean intensity {mean_intensity}")
                        else:
                            error_count += 1
                            logging.warning("empty frame captured by RPi camera")
                    except Exception as e:
                        error_count += 1
                        logging.error(f"Error capturing frame: {e}")
                        continue
                elif self.camera_mode == 'usb' and self.camera and self.camera.isOpened():
                    ret, frame = self.camera.read()
                    if ret and frame is not None and frame.size > 0:
                        mean_intensity = np.mean(frame)
                    
                        if 15 < mean_intensity < 240:
                            with self.camera_lock:
                                self.last_frame = frame.copy()
                            frame_count += 1
                            error_count = 0
                            last_good_frame_time = time.time()
                        
                            if frame_count % 100 == 0:
                                logging.info(f"USB camera: Captured {frame_count} frames")
                        else:
                            error_count += 1
                            logging.warning(f"USB camera: Invalid frame intensity {mean_intensity}")
                    else:
                        error_count += 1
                        logging.warning("USB camera: Failed to read frame")
                else:
                    error_count += 1
                    logging.warning("No camera available for capture")
                    time.sleep(0.5)
        
                if time.time() - last_good_frame_time > 5.0:
                    logging.error("No good frames for 5 seconds, attempting camera restart")
                    self._restart_camera_internal()
                    last_good_frame_time = time.time()

                if error_count > 5:
                    time.sleep(0.1)
                else:
                    time.sleep(1.0 / self.camera_settings['fps'])
                
            except Exception as e:
                error_count += 1
                logging.error(f"Error in capture loop: {e}")
                time.sleep(0.1)

        if error_count >= max_errors:
            logging.error("Max frame capture errors reached, stopping camera")
            self.camera_error = "Camera capture failed"
            self.camera_active = False
        
    def _restart_camera_internal(self):
        """Internal camera restart without external locking"""
        try:
            if self.camera:
                self.camera.release()
                time.sleep(0.5)

            backends_to_try = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_V4L2, cv2.CAP_ANY]

            for camera_id in [0, 1, 2]:
                for backend in backends_to_try:
                    try:
                        test_camera = cv2.VideoCapture(camera_id, backend)
                        if test_camera.isOpened():
                            ret, frame = test_camera.read()
                            test_camera.release()
                        
                            if ret and frame is not None and np.mean(frame) > 15:
                                self.camera = cv2.VideoCapture(camera_id, backend)
                                self.configure_camera()
                                logging.info("Camera restarted successfully")
                                return True
                    except:
                        continue
        
            logging.error("Failed to restart camera")
            return False
        
        except Exception as e:
            logging.error(f"Camera restart error: {e}")
            return False

face_server = EnhancedFaceRecognitionServer()
connected_clients = {}

@app.route('/')
def web_interface():
    """Web interface for testing"""
    return render_template('face_server_index.html')

@app.route('/api/delete_person', methods=['DELETE'])
def delete_person():
    """Delete a person and their face data"""
    try:
        data = request.json
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
            
        name = data.get('name', '').strip()
        
        if not name:
            return jsonify({'error': 'Name required'}), 400
        
        conn = sqlite3.connect(face_server.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM people WHERE name = ?", (name,))
        result = cursor.fetchone()
        
        if not result:
            return jsonify({'error': 'Person not found'}), 404
        
        person_id = result[0]

        cursor.execute("DELETE FROM face_encodings WHERE person_id = ?", (person_id,))
        cursor.execute("DELETE FROM people WHERE id = ?", (person_id,))
        
        conn.commit()
        conn.close()

        if name in face_server.face_encodings:
            del face_server.face_encodings[name]
        
        face_server.recognition_cache.clear()
        
        return jsonify({
            'success': True,
            'message': f'Successfully deleted {name}'
        })
        
    except Exception as e:
        logging.error(f"Delete person error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/camera/start', methods=['POST'])
def start_camera():
    """Start camera endpoint"""
    try:
        success = face_server.start_camera()
        if success:
            return jsonify({
                'success': True,
                'message': 'Camera started successfully',
                'camera_active': True,
                'timestamp': datetime.now().isoformat()
            })
        else:
            logging.error("Failed to start camera")
            return jsonify({
                'success': False,
                'message': 'No available cameras found',
                'camera_active': False
            }), 500
    except Exception as e:
        logging.error(f"Camera start endpoint error: {e}")
        return jsonify({
            'success': False,
            'message': f'Camera error: {str(e)}',
            'camera_active': False
        }), 500

@app.route('/api/camera/stop', methods=['POST'])
def stop_camera():
    """Stop camera endpoint"""
    try:
        success = face_server.stop_camera()
        return jsonify({
            'success': True,
            'message': 'Camera stopped successfully',
            'camera_active': False,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logging.error(f"Camera stop endpoint error: {e}")
        return jsonify({
            'success': True,
            'message': 'Camera stop requested',
            'camera_active': False,
            'timestamp': datetime.now().isoformat()
        })

@app.route('/api/camera/frame_add_friend', methods=['GET'])
def get_camera_frame_add_friend():
    """Get camera frame for add friend"""
    try:
        if not face_server.camera_active:
            return jsonify({
                'success': False, 
                'error': 'Camera not streaming',
                'debug': {
                    'is_streaming': face_server.camera_active,
                    'camera_mode': face_server.camera_mode,
                    'connected_clients': len(connected_clients),
                    'camera_error': face_server.camera_error
                }
            }), 400
        
        frame = face_server.capture_frame()
        if frame is None:
            return jsonify({
                'success': False, 
                'error': 'No frame available'
            }), 404

        frame_base64 = face_server.frame_to_base64(frame)
        if frame_base64 is None:
            return jsonify({
                'success': False,
                'error': 'Failed to encode frame'
            }), 500
        
        return jsonify({
            'success': True,
            'frame_data': {
                'image': frame_base64,
                'timestamp': time.time()
            }
        })
        
    except Exception as e:
        logging.error(f"Java frame endpoint error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/camera/connect', methods=['POST'])
def connect_client():
    """Connect a client to the camera stream"""
    try:
        data = request.json or {}
        client_id = data.get('client_id', 'unknown')
        logging.info(f"Connect request from client: {client_id}")
        
        if client_id in connected_clients:
            logging.info(f"Client {client_id} already connected")
            return jsonify({
                'success': True,
                'message': f'Client {client_id} already connected',
                'stream_url': '/api/camera/frame',
                'camera_mode': face_server.camera_mode or 'smart_glasses',
                'resolution': f"{face_server.camera_width}x{face_server.camera_height}",
                'fps': face_server.fps,
                'camera_index': 0,
                'optimized_for': 'smart_glasses'
            })
        
        connected_clients[client_id] = {
            'connected_at': time.time(),
            'last_request': time.time()
        }
        
        if not face_server.camera_active:
            success = face_server.start_camera()
            if not success:
                del connected_clients[client_id]
                return jsonify({
                    'success': False,
                    'message': 'Failed to start camera streaming - no camera available'
                }), 500
        
        return jsonify({
            'success': True,
            'message': f'Client {client_id} connected successfully',
            'stream_url': '/api/camera/frame',
            'camera_mode': face_server.camera_mode or 'smart_glasses',
            'resolution': f"{face_server.camera_width}x{face_server.camera_height}",
            'fps': face_server.fps,
            'camera_index': 0,
            'optimized_for': 'smart_glasses'
        })
        
    except Exception as e:
        logging.error(f"Connect error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/camera/disconnect', methods=['POST'])
def disconnect_client():
    """Disconnect a client from the camera stream"""
    try:
        data = request.json or {}
        client_id = data.get('client_id', 'unknown')
        logging.info(f"Disconnect request from client: {client_id}")
        
        if client_id in connected_clients:
            del connected_clients[client_id]
        
        if not connected_clients and face_server.camera_active:
            face_server.stop_camera()
            logging.info("No clients connected, stopping camera")
        
        return jsonify({
            'success': True,
            'message': f'Client {client_id} disconnected'
        })
        
    except Exception as e:
        logging.error(f"Disconnect error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/camera/health', methods=['GET'])
def camera_health():
    """Camera health check endpoint for Java client"""
    try:
        camera_available = face_server.camera_active or (face_server.camera_error is None)
        
        return jsonify({
            'status': 'healthy',
            'camera_available': camera_available,
            'camera_mode': face_server.camera_mode or 'unknown',
            'resolution': f"{face_server.camera_width}x{face_server.camera_height}",
            'fps': face_server.fps,
            'active_clients': len(connected_clients)
        })
    except Exception as e:
        logging.error(f"Camera health check error: {e}")
        return jsonify({
            'status': 'error',
            'camera_available': False,
            'error': str(e)
        }), 500

@app.route('/api/test', methods=['GET'])
def test_endpoint():
    """Test endpoint to check if server is working"""
    return jsonify({
        'status': 'Server is working',
        'model_loaded': face_server.model_loaded,
        'features': {
            'multi_face_recognition': True,
            'enhanced_registration': True,
            'continuous_recognition': True,
            'quality_analysis': True
        },
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/camera/frame', methods=['GET'])
def get_camera_frame():
    """Get current frame with recognition results - OPTIMIZED"""
    try:
        if not face_server.camera_active:
            return jsonify({
                'error': 'Camera not active',
                'recognized': False,
                'message': 'Camera not available',
                'timestamp': datetime.now().isoformat()
            }), 500
        
        latest = face_server.get_latest_recognition()
        
        if not latest:
            return jsonify({
                'error': 'No frame available',
                'recognized': False,
                'message': 'Processing...',
                'timestamp': datetime.now().isoformat()
            }), 404
        
        result = latest['result']
        frame = latest['frame']
        
        frame_base64 = face_server.frame_to_base64(frame)
        
        return jsonify({
            'success': True,
            'image': frame_base64,
            'recognized': result.get('recognized', False),
            'faces': result.get('faces', []),
            'face_count': result.get('face_count', 0),
            'recognized_count': result.get('recognized_count', 0),
            'unknown_count': result.get('unknown_count', 0),
            'message': result.get('message', 'Processing...'),
            'processing_time': result.get('processing_time', 0),
            'method_used': result.get('method_used', 'multi_face'),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logging.error(f"Frame endpoint error: {e}")
        return jsonify({
            'error': str(e),
            'recognized': False,
            'message': 'Server error',
            'timestamp': datetime.now().isoformat()
        }), 500


@app.route('/api/register_enhanced', methods=['POST'])
def register_person_enhanced():
    """Registration endpoint"""
    try:
        data = request.json
        
        if not data or 'name' not in data or 'images' not in data:
            return jsonify({'error': 'Name and images required'}), 400
        
        name = data['name'].strip()
        images = data['images']
        
        if len(images) < 3:
            return jsonify({'error': 'Minimum 3 images required'}), 400
        
        result = face_server.add_person_enhanced(name, images)
        
        return jsonify(result), 200 if result['success'] else 400
            
    except Exception as e:
        logging.error(f"Registration error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analytics_enhanced', methods=['GET'])
def analytics_enhanced():
    """Enhanced analytics endpoint"""
    try:
        conn = sqlite3.connect(face_server.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT method_used, COUNT(*) as count
            FROM recognition_logs
            GROUP BY method_used
        ''')
        method_usage = dict(cursor.fetchall())
        
        cursor.execute('''
            SELECT person_name, confidence, 
                   CASE 
                       WHEN confidence >= 0.85 THEN 'very_high'
                       WHEN confidence >= 0.70 THEN 'high'
                       WHEN confidence >= 0.50 THEN 'medium'
                       WHEN confidence >= 0.35 THEN 'low'
                       ELSE 'very_low'
                   END as confidence_level,
                   COUNT(*) as recognition_count
            FROM recognition_logs
            WHERE timestamp >= datetime('now', '-7 days')
            GROUP BY person_name, confidence_level
            ORDER BY timestamp DESC
        ''')
        recent_recognitions = []
        for row in cursor.fetchall():
            recent_recognitions.append({
                'person_name': row[0],
                'confidence': row[1],
                'confidence_level': row[2],
                'recognition_count': row[3]
            })
        
        # Get hourly distribution
        cursor.execute('''
            SELECT CAST(strftime('%H', timestamp) AS INTEGER) as hour, COUNT(*) as count
            FROM recognition_logs
            WHERE timestamp >= datetime('now', '-1 day')
            GROUP BY hour
        ''')
        hourly_distribution = dict(cursor.fetchall())
        
        conn.close()
        
        return jsonify({
            'recognition_stats': face_server.recognition_stats,
            'method_usage': method_usage,
            'recent_recognitions': recent_recognitions,
            'hourly_distribution': hourly_distribution
        })
        
    except Exception as e:
        logging.error(f"Analytics error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/daily_report', methods=['GET'])
def daily_report():
    """Daily report endpoint"""
    try:
        date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
        
        conn = sqlite3.connect(face_server.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                COUNT(*) as total_recognitions,
                COUNT(DISTINCT person_name) as unique_people,
                AVG(confidence) as avg_confidence,
                AVG(quality_score) as avg_quality
            FROM recognition_logs
            WHERE DATE(timestamp) = ?
        ''', (date,))
        
        row = cursor.fetchone()
        summary = {
            'total_recognitions': row[0] or 0,
            'unique_people': row[1] or 0,
            'avg_confidence': float(row[2]) if row[2] else 0.0,
            'avg_quality': float(row[3]) if row[3] else 0.0
        }
        
        cursor.execute('''
            SELECT 
                person_name,
                COUNT(*) as recognition_count,
                AVG(confidence) as avg_confidence,
                AVG(quality_score) as avg_quality,
                method_used as most_used_method,
                CASE 
                    WHEN AVG(confidence) >= 0.85 THEN 'very_high'
                    WHEN AVG(confidence) >= 0.70 THEN 'high'
                    WHEN AVG(confidence) >= 0.50 THEN 'medium'
                    WHEN AVG(confidence) >= 0.35 THEN 'low'
                    ELSE 'very_low'
                END as confidence_level
            FROM recognition_logs
            WHERE DATE(timestamp) = ?
            GROUP BY person_name
            ORDER BY recognition_count DESC
        ''', (date,))
        
        people_analysis = []
        for row in cursor.fetchall():
            people_analysis.append({
                'name': row[0],
                'recognition_count': row[1],
                'avg_confidence': float(row[2]),
                'avg_quality': float(row[3]),
                'most_used_method': row[4],
                'confidence_level': row[5]
            })
        
        cursor.execute('''
            SELECT 
                CASE 
                    WHEN confidence >= 0.85 THEN 'very_high'
                    WHEN confidence >= 0.70 THEN 'high'
                    WHEN confidence >= 0.50 THEN 'medium'
                    WHEN confidence >= 0.35 THEN 'low'
                    ELSE 'very_low'
                END as level,
                COUNT(*) as count
            FROM recognition_logs
            WHERE DATE(timestamp) = ?
            GROUP BY level
        ''', (date,))
        
        confidence_distribution = dict(cursor.fetchall())
        
        insights = []
        if summary['total_recognitions'] > 0:
            if summary['avg_confidence'] > 0.8:
                insights.append("✓ Excellent average confidence scores today")
            elif summary['avg_confidence'] < 0.5:
                insights.append("⚠ Low average confidence - consider improving lighting or re-registering people")
            
            if summary['avg_quality'] > 0.7:
                insights.append("✓ High quality images captured")
            elif summary['avg_quality'] < 0.4:
                insights.append("⚠ Poor image quality detected - check camera settings")
            
            if summary['unique_people'] > 5:
                insights.append(f"✓ Recognized {summary['unique_people']} different people today")
        
        conn.close()
        
        return jsonify({
            'date': date,
            'summary': summary,
            'people_analysis': people_analysis,
            'confidence_distribution': confidence_distribution,
            'performance_insights': insights
        })
        
    except Exception as e:
        logging.error(f"Daily report error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/recognition_logs', methods=['GET'])
def recognition_logs():
    """Recognition logs endpoint"""
    try:
        date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
        
        conn = sqlite3.connect(face_server.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT person_name, confidence, quality_score, processing_time, 
                   method_used, timestamp
            FROM recognition_logs
            WHERE DATE(timestamp) = ?
            ORDER BY timestamp DESC
            LIMIT 100
        ''', (date,))
        
        logs = []
        for row in cursor.fetchall():
            logs.append({
                'person_name': row[0],
                'confidence': float(row[1]),
                'quality_score': float(row[2]),
                'processing_time': float(row[3]),
                'method_used': row[4],
                'timestamp': row[5]
            })
        
        avg_confidence = sum([l['confidence'] for l in logs]) / len(logs) if logs else 0
        avg_quality = sum([l['quality_score'] for l in logs]) / len(logs) if logs else 0
        
        conn.close()
        
        return jsonify({
            'logs': logs,
            'avg_confidence': avg_confidence,
            'avg_quality': avg_quality
        })
        
    except Exception as e:
        logging.error(f"Recognition logs error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/historical_data', methods=['GET'])
def historical_data():
    """Historical performance data endpoint"""
    try:
        date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
        
        conn = sqlite3.connect(face_server.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                DATE(timestamp) as date,
                COUNT(*) as total_recognitions,
                COUNT(DISTINCT person_name) as unique_people,
                AVG(confidence) as avg_confidence,
                AVG(quality_score) as avg_quality
            FROM recognition_logs
            WHERE DATE(timestamp) <= ? AND DATE(timestamp) >= DATE(?, '-30 days')
            GROUP BY DATE(timestamp)
            ORDER BY date DESC
        ''', (date, date))
        
        days = []
        for row in cursor.fetchall():
            days.append({
                'date': row[0],
                'total_recognitions': row[1],
                'unique_people': row[2],
                'avg_confidence': float(row[3]) if row[3] else 0.0,
                'avg_quality': float(row[4]) if row[4] else 0.0
            })
        
        conn.close()
        
        return jsonify({'days': days})
        
    except Exception as e:
        logging.error(f"Historical data error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/analyze_person/<name>', methods=['GET'])
def analyze_person(name):
    """Analyze a specific person's registration quality"""
    try:
        conn = sqlite3.connect(face_server.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT p.id, p.photo_count, p.avg_quality, p.best_quality
            FROM people p
            WHERE p.name = ?
        ''', (name,))
        
        result = cursor.fetchone()
        if not result:
            return jsonify({'error': 'Person not found'}), 404
        
        person_id, photo_count, avg_quality, best_quality = result
        
        cursor.execute('''
            SELECT image_quality
            FROM face_encodings
            WHERE person_id = ? AND is_outlier = FALSE
            ORDER BY image_quality DESC
        ''', (person_id,))
        
        qualities = [float(row[0]) for row in cursor.fetchall()]
        
        conn.close()
        
        recommendations = {
            'should_retake_photos': avg_quality < 0.3,
            'needs_better_lighting': avg_quality < 0.5,
            'has_good_photos': any(q > 0.6 for q in qualities)
        }
        
        return jsonify({
            'name': name,
            'photo_count': photo_count,
            'avg_quality': float(avg_quality),
            'max_quality': float(best_quality),
            'min_quality': float(min(qualities)) if qualities else 0.0,
            'qualities': qualities,
            'recommendations': recommendations
        })
        
    except Exception as e:
        logging.error(f"Analyze person error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/generate_test_data', methods=['POST'])
def generate_test_data():
    """Generate test recognition data for testing reports"""
    try:
        conn = sqlite3.connect(face_server.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT name FROM people LIMIT 5')
        people = [row[0] for row in cursor.fetchall()]
        
        if not people:
            return jsonify({
                'success': False,
                'error': 'No registered people found. Register someone first.'
            })
        
        import random
        from datetime import timedelta
        
        methods = ['multi_face_recognition', 'standard', 'enhanced']
        now = datetime.now()
        
        for i in range(50):
            person = random.choice(people)
            confidence = random.uniform(0.4, 0.95)
            quality = random.uniform(0.3, 0.9)
            processing_time = random.uniform(0.1, 0.8)
            method = random.choice(methods)
            timestamp = now - timedelta(hours=random.randint(0, 23), minutes=random.randint(0, 59))
            
            cursor.execute('''
                INSERT INTO recognition_logs 
                (person_name, confidence, quality_score, processing_time, method_used, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (person, confidence, quality, processing_time, method, timestamp.isoformat()))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Generated 50 test recognition logs for {len(people)} people'
        })
        
    except Exception as e:
        logging.error(f"Generate test data error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'model_loaded': face_server.model_loaded,
        'people_count': len(face_server.face_encodings),
        'camera_active': face_server.camera_active,
        'camera_mode': face_server.camera_mode,
        'recognition_stats': face_server.recognition_stats,
        'multi_face_support': True
    })


@app.route('/api/people', methods=['GET'])
def list_people():
    """List all registered people"""
    try:
        conn = sqlite3.connect(face_server.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT name, photo_count, created_at, avg_quality, best_quality
            FROM people
            ORDER BY created_at DESC
        ''')
        
        people = []
        for row in cursor.fetchall():
            avg_quality = row[3]
            best_quality = row[4]
            
            if isinstance(avg_quality, bytes):
                avg_quality = float(np.frombuffer(avg_quality, dtype=np.float32)[0])
            elif avg_quality is None:
                avg_quality = 0.0
            else:
                avg_quality = float(avg_quality)
                
            if isinstance(best_quality, bytes):
                best_quality = float(np.frombuffer(best_quality, dtype=np.float32)[0])
            elif best_quality is None:
                best_quality = 0.0
            else:
                best_quality = float(best_quality)
            
            people.append({
                'name': row[0],
                'photo_count': row[1],
                'created_at': row[2],
                'avg_quality': round(avg_quality, 3),
                'best_quality': round(best_quality, 3)
            })
        
        conn.close()
        return jsonify({'people': people, 'total_count': len(people)})
        
    except Exception as e:
        logging.error(f"List people error: {e}")
        return jsonify({'error': str(e)}), 500

def get_local_ip():
    """Get local IP address"""
    try:
        if 'LOCAL_IP' in os.environ:
            return os.environ['LOCAL_IP']
        
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return "127.0.0.1"

def cleanup_camera():
    """Cleanup camera resources"""
    if hasattr(face_server, 'camera') and face_server.camera:
        face_server.stop_camera()
        logging.info("Camera resources cleaned up")   

atexit.register(cleanup_camera)

if __name__ == '__main__':
    print("="*80)
    print("Enhanced Multi-Face Recognition Server")
    print("="*80)
    
    local_ip = socket.gethostbyname(socket.gethostname())
    port = 5000
    
    print(f"Server IP: {local_ip}")
    print(f"Server Port: {port}")
    print(f"Multi-face support: ENABLED")
    print("="*80)
    
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
