import statistics
from flask import Flask, request, jsonify, send_from_directory
import cv2
import numpy as np
import base64
import json
import os
import sqlite3
from datetime import datetime
import logging
import time
from flask_cors import CORS
import io
from PIL import Image
import traceback
import atexit
import threading
import socket
from collections import defaultdict, deque

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = Flask(__name__)
CORS(app) 

class EnhancedFaceRecognitionServer:
    def __init__(self):
        self.model = None
        self.model_loaded = False
        self.db_path = "face_database.db"
        self.face_encodings = {}

        self.recognition_threshold = 0.60
        self.quality_threshold = 0.35
        self.min_face_size = 50
        self.max_embeddings_per_person = 12

        self.recognition_cache = {}
        self.cache_duration = 3.0 

        self.camera= None
        self.camera_active = False
        self.camera_lock = threading.Lock()
        self.last_frame = None
        self.frame_capture_thread = None
        self.stop_capture = False

        self.temporal_window = 5
        self.temporal_results = deque(maxlen=self.temporal_window)
        self.confidence_boost_threshold = 0.55

        self.camera_error = None
        
        self.recognition_stats = {
            'total_requests': 0,
            'successful_recognitions': 0,
            'cache_hits': 0,
            'avg_processing_time': 0.0,
            'errors': 0,
            'high_confidence_recognitions': 0,
            'low_quality_rejections': 0,
            'temporal_smoothing_applied': 0 
        }
        
        self.recognition_history = defaultdict(list)
        self.history_window = 10
        self.temporal_threshold = 0.6

        self.confidence_levels = {
            'high': 0.80,
            'medium': 0.65,
            'low': 0.50
        }

        self.camera_settings = {
            'width': 640,
            'height': 480,
            'fps': 20,
            'brightness': 50,
            'contrast': 50,
            'saturation': 50
        }

        self.init_database()
        self.init_face_model()
        self.load_face_database()

    def init_face_model(self):
        """Initialize InsightFace model with error handling"""
        try:
            logging.info("Initializing InsightFace model...")
            
            try:
                import insightface
                logging.info("InsightFace imported successfully")
            except ImportError as e:
                logging.error(f"InsightFace not installed: {e}")
                logging.info("Please install with: pip install insightface")
                return False
            
            try:
                self.model = insightface.app.FaceAnalysis(
                    providers=['CPUExecutionProvider'],
                    allowed_modules=['detection','recognition']
                )
                self.model.prepare(ctx_id=0, det_size=(320, 320))
                self.model_loaded = True
                logging.info("InsightFace model loaded successfully")
                return True
                
            except Exception as e:
                logging.error(f"Failed to initialize InsightFace model: {e}")
                logging.error(f"Traceback: {traceback.format_exc()}")
                self.model_loaded = False
                return False
                
        except Exception as e:
            logging.error(f"Unexpected error in model initialization: {e}")
            self.model_loaded = False
            return False

    def init_database(self):
        """Initialize SQLite database for face storage"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS people (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    photo_count INTEGER DEFAULT 0
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS face_encodings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    person_id INTEGER,
                    encoding BLOB NOT NULL,
                    image_quality REAL DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (person_id) REFERENCES people (id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS recognition_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    person_name TEXT,
                    confidence REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    source TEXT DEFAULT 'realtime'
                )
            ''')
            
            conn.commit()
            conn.close()
            logging.info("Database initialized successfully")
            
        except Exception as e:
            logging.error(f"Database initialization error: {e}")

    def load_face_database(self):
        """Load existing face encodings from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT p.name, fe.encoding FROM people p
                JOIN face_encodings fe ON p.id = fe.person_id
            ''')
            
            results = cursor.fetchall()
            
            for name, encoding_blob in results:
                encoding = np.frombuffer(encoding_blob, dtype=np.float32)
                if name not in self.face_encodings:
                    self.face_encodings[name] = []
                self.face_encodings[name].append(encoding)
            
            conn.close()
            logging.info(f"Loaded {len(self.face_encodings)} people from database")
            
        except Exception as e:
            logging.error(f"Error loading face database: {e}")

    def extract_face_encoding(self, image):
        """Extract face encoding from image using InsightFace with fallback"""
        try:
            if not self.model_loaded:
                logging.warning("InsightFace model not loaded, using fallback")
                return self.fallback_face_detection(image)
            
            faces = self.model.get(image)
            if len(faces) == 0:
                return None, 0.0, None

            face = max(faces, key=lambda x: (x.bbox[2] - x.bbox[0]) * (x.bbox[3] - x.bbox[1]))
            
            face_area = (face.bbox[2] - face.bbox[0]) * (face.bbox[3] - face.bbox[1])
            image_area = image.shape[0] * image.shape[1]
            size_ratio = face_area / image_area

            blur_score = self._calculate_blur_score(image,face.bbox)
            lightning_score = self._calculate_lightning_score(image, face.bbox)
            angle_score = self._calculate_face_angle_score(face)

            quality_score = min(1.0, (size_ratio * 8 + blur_score + lightning_score + angle_score))
            
            face_info = {
                'bbox': face.bbox.tolist(),
                'area_ratio': float(size_ratio),
                'landmarks': face.kps.tolist() if hasattr(face, 'kps') else None
            }
            
            return face.embedding, quality_score, face_info
            
        except Exception as e:
            logging.error(f"Error extracting face encoding: {e}")
            logging.error(f"Traceback: {traceback.format_exc()}")
            return None, 0.0, None

    def _calculate_blur_score(self,image,bbox):
        """Calculate blur score for face region"""
        try:
            x1, y1, x2, y2 = map(int,bbox)
            face_roi = image[y1:y2, x1:x2]
            gray_face = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
            laplacian_var = cv2.Laplacian(gray_face, cv2.CV_64F).var()
            return min(1.0, laplacian_var / 500.0)
        except:
            return 0.5
        
    def _calculate_lightning_score(self, image, bbox):
        """Calculate lighting quality score"""
        try:
            x1, y1, x2, y2 = map(int, bbox)
            face_roi = image[y1:y2, x1:x2]
            gray_face = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
            mean_brightness = np.mean(gray_face)
            if 80 <= mean_brightness <= 180:
                return 1.0
            else:
                return max(0.3,0.1 - abs(mean_brightness - 130) / 130)
        
        except:
            return 0.5
        
    def _calculate_face_angle_score(self, face):
        """Calculate face angle qality score using landmarks"""
        try:
            if hasattr(face,'kps') and face.kps is not None:
                landmarks = face.kps
                left_eye = landmarks[0]
                right_eye = landmarks[1]
                eye_angle = abs(np.arctan2(right_eye[1] - left_eye[1], right_eye[0] - left_eye[0]))
                angle_score = max(0.3, 1.0 - (eye_angle /0.5))
                return min(1.0, angle_score)
            return 0.7
        except:
            return 0.7


    def fallback_face_detection(self, image):
        """Fallback face detection using OpenCV when InsightFace fails"""
        try:
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            
            if len(faces) == 0:
                return None, 0.0, None
            
            largest_face = max(faces, key=lambda x: x[2] * x[3])
            x, y, w, h = largest_face
            
            face_area = w * h
            image_area = image.shape[0] * image.shape[1]
            size_ratio = face_area / image_area
            quality_score = min(1.0, size_ratio * 5)
            
            face_roi = gray[y:y+h, x:x+w]
            face_resized = cv2.resize(face_roi, (128, 128))
            encoding = face_resized.flatten().astype(np.float32) / 255.0
            
            face_info = {
                'bbox': [x, y, x+w, y+h],
                'area_ratio': float(size_ratio),
                'landmarks': None,
                'fallback_mode': True
            }
            
            return encoding, quality_score, face_info
            
        except Exception as e:
            logging.error(f"Fallback face detection error: {e}")
            return None, 0.0, None

    def recognize_face_realtime(self, image):
        """Enhanced face recognition for real-time use with better error handling"""
        start_time = time.time()
        self.recognition_stats['total_requests'] += 1
        
        try:
            if image is None:
                raise ValueError("Image is None")
            
            if len(image.shape) != 3:
                raise ValueError(f"Invalid image shape: {image.shape}")
            
            try:
                image_hash = hash(image.tobytes()[:1000])
            except Exception as e:
                logging.warning(f"Could not create image hash: {e}")
                image_hash = hash(str(time.time()))
            
            cached_result = self.check_cache(image_hash)
            if cached_result:
                return cached_result
            
            encoding, quality, face_info = self.extract_face_encoding(image)
            
            if encoding is None:
                result = {
                    'recognized': False,
                    'name': None,
                    'confidence': 0.0,
                    'message': "No face detected",
                    'quality_score': 0.0,
                    'processing_time': float(time.time() - start_time),
                    'model_loaded': self.model_loaded
                }
                self.cache_result(image_hash, result)
                return result
            
            if quality < 0.3:
                result = {
                    'recognized': False,
                    'name': None,
                    'confidence': float(quality),
                    'message': "Face quality too low for recognition",
                    'quality_score': float(quality),
                    'processing_time': float(time.time() - start_time),
                    'face_info': face_info,
                    'model_loaded': self.model_loaded
                }
                self.cache_result(image_hash, result)
                return result
            
            best_match = None
            best_similarity = 0.0
            
            if self.model_loaded:
                try:
                    from sklearn.metrics.pairwise import cosine_similarity
                    
                    for name, stored_encodings in self.face_encodings.items():
                        confidences = []
                        for stored_encoding in stored_encodings:
                            cosine_sim  = cosine_similarity([encoding], [stored_encoding])[0][0]
                            
                            euclidean_dist = np.linalg.norm(encoding - stored_encoding)
                            euclidean_sim = 1.0 / (1.0 + euclidean_dist)

                            combined_similarity = (cosine_sim * 0.7) + (euclidean_sim * 0.3)
                            confidences.append(combined_similarity)

                        max_confidence = max(confidences) if confidences else 0.0
                        if max_confidence > best_similarity:
                            best_similarity = max_confidence
                            best_match = name
                                
                except ImportError:
                    logging.warning("sklearn not available, using basic similarity")
                    best_similarity = 0.0
            else:
                best_similarity = 0.0
            
            if best_similarity > 0.4:
                self.temporal_results.append({
                    'name':best_match,
                    'confidence': best_similarity,
                    'timestamp': time.time()
                })

                if len(self.temporal_results) >= 3:
                    recent_results = [r for r in self.temporal_results if r['name'] == best_match]
                    if len(recent_results) >= 2:
                        avg_confidence = statistics.mean([r['confidence'] for r in recent_results])
                        if avg_confidence > self.confidence_boost_threshold:
                            best_similarity = min(0.95,avg_confidence * 1.1)
                            self.recognition_stats['temporal_smoothing_applied'] +=1

            processing_time = time.time() - start_time
            
            if best_similarity > self.recognition_threshold:
                self.recognition_stats['successful_recognitions'] += 1
                self.log_recognition(best_match, best_similarity)
                
                result = {
                    'recognized': True,
                    'name': best_match,
                    'confidence': float(best_similarity),
                    'message': f"Recognized {best_match}",
                    'quality_score': float(quality),  
                    'processing_time': float(processing_time),
                    'face_info': face_info,
                    'model_loaded': self.model_loaded
                }
            else:
                result = {
                    'recognized': False,
                    'name': None,
                    'confidence': float(best_similarity),
                    'message': "Unknown person" if self.model_loaded else "Model not loaded - detection only",
                    'quality_score': float(quality),
                    'processing_time': float(processing_time),
                    'face_info': face_info,
                    'model_loaded': self.model_loaded
                }
            
            total_requests = self.recognition_stats['total_requests']
            current_avg = self.recognition_stats['avg_processing_time']
            self.recognition_stats['avg_processing_time'] = (
                (current_avg * (total_requests - 1) + processing_time) / total_requests
            )
            
            self.cache_result(image_hash, result)
            return result
            
        except Exception as e:
            self.recognition_stats['errors'] += 1
            logging.error(f"Recognition error: {e}")
            logging.error(f"Traceback: {traceback.format_exc()}")
            
            return {
                'recognized': False,
                'name': None,
                'confidence': 0.0,
                'message': f"Error: {str(e)}",
                'quality_score': 0.0,
                'processing_time': float(time.time() - start_time),
                'error': True,
                'model_loaded': self.model_loaded
            }

    def check_cache(self, image_hash):
        """Check if we have a recent recognition for similar image"""
        try:
            current_time = time.time()
            
            expired_keys = [k for k, v in self.recognition_cache.items() 
                           if current_time - v['timestamp'] > self.cache_duration]
            for key in expired_keys:
                del self.recognition_cache[key]
            
            if image_hash in self.recognition_cache:
                self.recognition_stats['cache_hits'] += 1
                return self.recognition_cache[image_hash]['result']
            
            return None
        except Exception as e:
            logging.error(f"Cache check error: {e}")
            return None

    def cache_result(self, image_hash, result):
        """Cache recognition result"""
        try:
            self.recognition_cache[image_hash] = {
                'result': result,
                'timestamp': time.time()
            }
        except Exception as e:
            logging.error(f"Cache store error: {e}")

    def log_recognition(self, person_name, confidence):
        """Log recognition for analytics"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO recognition_logs (person_name, confidence)
                VALUES (?, ?)
            ''', (person_name, confidence))
            conn.commit()
            conn.close()
        except Exception as e:
            logging.error(f"Error logging recognition: {e}")

    def start_camera(self):
        """Enhanced camera initialization with multiple backends"""
        try:
            with self.camera_lock:
                if self.camera_active:
                    logging.info("Camera already active")
                    return True
            
                backends_to_try = [cv2.CAP_DSHOW, cv2.CAP_MSMF, cv2.CAP_V4L2, cv2.CAP_ANY]
            
                for camera_id in [0, 1, 2]:
                    logging.info(f"Trying camera {camera_id}...")
                
                    for backend in backends_to_try:
                        try:
                            test_camera = cv2.VideoCapture(camera_id, backend)
                        
                            if test_camera.isOpened():
                                test_camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                                test_camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                                test_camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                                test_camera.set(cv2.CAP_PROP_FPS, 30)
                            
                                valid_frames = 0
                                for test_attempt in range(5):
                                    ret, frame = test_camera.read()
                                    if ret and frame is not None and frame.size > 0:
                                        if np.mean(frame) > 10:
                                            valid_frames += 1
                                    time.sleep(0.1)

                                test_camera.release()
                            
                                if valid_frames >= 2:
                                    self.camera = cv2.VideoCapture(camera_id, backend)
                                    if self.configure_camera():  
                                        if self._validate_camera():
                                            self.camera_active = True
                                            self.stop_capture = False
                                            self.camera_error = None

                                            self.frame_capture_thread = threading.Thread(
                                                target=self._continuous_capture,
                                                daemon=True
                                            )
                                            self.frame_capture_thread.start()
                                            time.sleep(0.5)
                                    
                                            logging.info(f"Camera {camera_id} initialized successfully with backend {backend}")
                                            return True
                                        else:
                                            self.camera.release()
                                            self.camera = None
                                    else:
                                        self.camera.release()
                                        self.camera = None
                            else:
                                test_camera.release()
                            
                        except Exception as e:
                            logging.debug(f"Backend {backend} failed for camera {camera_id}: {e}")
                            continue
            
                self.camera_error = "No working cameras found"
                logging.error(self.camera_error)
                return False
            
        except Exception as e:
            logging.error(f"Camera initialization error: {e}")
            self.camera_error = f"Camera initialization failed: {str(e)}"
            return False
        
    def configure_camera(self):
        """Configure camera with validation"""
        try:
            if not self.camera or not self.camera.isOpened():
                return False  
          
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)  
            self.camera.set(cv2.CAP_PROP_FPS, 30)

            optional_settings = [
                (cv2.CAP_PROP_BRIGHTNESS, 0.5),
                (cv2.CAP_PROP_CONTRAST, 0.5),
                (cv2.CAP_PROP_SATURATION, 0.5),
                (cv2.CAP_PROP_AUTO_EXPOSURE, 0.25), 
                (cv2.CAP_PROP_EXPOSURE, -6),
            ]
        
            for prop, value in optional_settings:
                try:
                    self.camera.set(prop,value)
                except:
                    pass
            
            logging.info("camera configured successfull")
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
                ret,frame = self.camera.read()

                if ret and frame is not None and frame.size > 0:
                    mean_intensity = np.mean(frame)
                    if mean_intensity > 15 and mean_intensity < 240:
                        valid_frames += 1
                        logging.debug(f"Frame {i+1}: valid (mean intensity: {mean_intensity:1f})")

                    else:
                        logging.warning(f"Frame {i+1}: Invalid intensity {mean_intensity:.1f}")
                else:
                    logging.warning(f"Frame {i+1}: Failed to capture")
                
                time.sleep(0.05)

            success_rate = valid_frames /10
            logging.info(f"Camera validation: {valid_frames}/10 valid frames ({success_rate*100:.1f}%)")
        
            return success_rate >= 0.6
        
        except Exception as e:
            logging.error(f"camera validation error: {e}")
            return False

    def _safe_camera_config(self):
        """Safely configure camera settings"""
        try:
            if self.camera and self.camera.isOpened():
                self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.camera_settings['width'])
                self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.camera_settings['height'])
                self.camera.set(cv2.CAP_PROP_FPS, self.camera_settings['fps'])
                self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                
                # Optional settings that might not be supported
                try:
                    self.camera.set(cv2.CAP_PROP_BRIGHTNESS, self.camera_settings['brightness'])
                    self.camera.set(cv2.CAP_PROP_CONTRAST, self.camera_settings['contrast'])
                    self.camera.set(cv2.CAP_PROP_SATURATION, self.camera_settings['saturation'])
                except Exception as e:
                    logging.debug(f"Some camera settings not supported: {e}")
                    
                logging.info("Camera configured successfully")
        except Exception as e:
            logging.warning(f"Error configuring camera: {e}")
    
    def _continuous_capture(self):
        """Continuosly capture frames in background thread"""

        frame_count = 0
        error_count = 0
        max_errors = 10
        last_good_frame_time = time.time()

        logging.info("Starting continuous capture thread")

        while not self.stop_capture and error_count < max_errors:
            try:
                if self.camera and self.camera.isOpened():
                    ret, frame = self.camera.read()
                    if ret and frame is not None and frame.size > 0:
                        mean_intensity = np.mean(frame)

                        if mean_intensity > 15 and mean_intensity <240:

                            with self.camera_lock:
                                self.last_frame = frame.copy()
                            frame_count += 1
                            error_count = 0
                            last_good_frame_time = time.time()


                            if(frame_count % 100 == 0):
                                logging.info(f"Captured {frame_count} frames")
                        else:
                            error_count += 1
                            logging.warning("Failed to read frame from camera")
                            time.sleep(0.1)
                    else:
                        error_count += 1
                        logging.warning("Camera not opened or already released")
                    
                    if time.time() - last_good_frame_time > 5.0:
                        logging.error("No good frames for 5 seconds, attempting camera restart")
                        self._restart_camera_internal()
                        last_good_frame_time = time.time()

                    if error_count > 5:
                        time.sleep(0.1)
                    else:
                        time.sleep(0.033)
                
                else:
                    error_count += 1
                    logging.warning(f"Camera not available (attempt {error_count}/{max_errors})")
                    time.sleep(0.5)
                
            except Exception as e:
                error_count += 1
                logging.error(f"Error capturing frame: {e}")
                time.sleep(0.1)
        
        if error_count >= max_errors:
            logging.error("Max frame capture errors reached, stopping camera")
            self.camera_error = "Camera capture failed"
            self.camera_active = False

    def _release_camera_safely(self):
        """Safely release camera resources"""
        try:
            if self.camera:
                self.camera.release()
                self.camera = None
            time.sleep(0.5)
            cv2.destroyAllWindows()
        except Exception as e:
            logging.debug(f"Camera release error: {e}")

    def _restart_camera_internal(self):
        """Internal camera restart without external locking"""
        try:
        
            if self.camera:
                self.camera.release()
                time.sleep(0.5)

            self._release_camera_safely()
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
                                self._configure_camera()
                                logging.info("Camera restarted successfully")
                                return True
                    except:
                        continue
        
            logging.error("Failed to restart camera")
            return False
        
        except Exception as e:
            logging.error(f"Camera restart error: {e}")
            return False
    
    def stop_camera(self):
        """Stop camera and cleanup"""
        try:
            with self.camera_lock:
                self.stop_capture = True
                self.camera_active = False

                if self.camera:
                    self.camera.release()
                    self.camera = None

                self.last_frame = None
                 
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
                elif self.camera and self.camera.isOpened():
                    ret, frame = self.camera.read()
                    if ret and frame is not None:
                        self.last_frame = frame.copy()
                        return self.last_frame
                    else:
                        logging.warning("Direct camera read failed")
                        return None
                else:
                    logging.warning("No camera available for frame capture")
                    return None
        except Exception as e:
            logging.error(f"Error capturing frame: {e}")
            return None
        
    def frame_to_base64(self, frame):
        """Convert frame to base64 string"""
        try:
            if frame is None:
                return None
            
            ret,buffer = cv2.imencode('.jpg',frame, [cv2.IMWRITE_JPEG_QUALITY,80])
            if not ret:
                logging.error("Failed to encode frame to JPEG")
                return None
            
            jpg_as_text = base64.b64encode(buffer).decode('utf-8')
            return jpg_as_text
        
        except Exception as e:
            logging.error(f"Error converting frame to base64: {e}")
            return None

    def add_person(self, name, images_base64):
        """Add new person with multiple images"""
        try:
            if not self.model_loaded:
                return {
                    'success': False,
                    'message': 'Face recognition model not loaded. Please check server logs.',
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
                cursor.execute("INSERT INTO people (name) VALUES (?)", (name,))
                person_id = cursor.lastrowid
            
            successful_encodings = []
            total_quality = 0.0
            
            for i, img_base64 in enumerate(images_base64):
                try:
                    img_data = base64.b64decode(img_base64)
                    nparr = np.frombuffer(img_data, np.uint8)
                    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                    
                    if image is None:
                        logging.warning(f"Could not decode image {i+1} for {name}")
                        continue

                    encoding, quality, _ = self.extract_face_encoding(image)
                    
                    if encoding is not None and quality > 0.3:
                        encoding_blob = encoding.tobytes()
                        cursor.execute('''
                            INSERT INTO face_encodings (person_id, encoding, image_quality)
                            VALUES (?, ?, ?)
                        ''', (person_id, encoding_blob, quality))
                        
                        successful_encodings.append(encoding)
                        total_quality += quality
                        
                        logging.info(f"Processed image {i+1} for {name}, quality: {quality:.2f}")
                    else:
                        logging.warning(f"Poor quality or no face in image {i+1} for {name}")
                    
                except Exception as e:
                    logging.error(f"Error processing image {i+1} for {name}: {e}")
                    continue
            
            if successful_encodings:
                cursor.execute('''
                    UPDATE people SET photo_count = ? WHERE id = ?
                ''', (len(successful_encodings), person_id))

                self.face_encodings[name] = successful_encodings
                
                conn.commit()
                avg_quality = total_quality / len(successful_encodings)
                
                self.recognition_cache.clear()
                
                return {
                    'success': True,
                    'message': f'Successfully registered {name}',
                    'photos_processed': len(successful_encodings),
                    'average_quality': float(avg_quality)
                }
            else:
                conn.rollback()
                return {
                    'success': False,
                    'message': 'No suitable face images found',
                    'photos_processed': 0
                }
                
        except Exception as e:
            conn.rollback()
            logging.error(f"Error adding person: {e}")
            return {
                'success': False,
                'message': f'Database error: {str(e)}',
                'photos_processed': 0
            }
        finally:
            conn.close()

face_server = EnhancedFaceRecognitionServer()


@app.route('/')
def web_interface():
    """Web interface for testing"""
    return send_from_directory('.', 'face_server_index.html')

@app.route('/api/health', methods=['GET'])
def health_check():
    """Enhanced health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'model_loaded': face_server.model_loaded,
        'people_count': len(face_server.face_encodings),
        'camera_active': face_server.camera_active,
        'camera_error': face_server.camera_error,
        'recognition_stats': face_server.recognition_stats,
        'cache_size': len(face_server.recognition_cache)
    })

@app.route('/api/recognize_realtime', methods=['POST'])
def recognize_realtime():
    """Real-time recognition endpoint with enhanced error handling"""
    try:
        data = request.json
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        if 'image' not in data:
            return jsonify({'error': 'No image data provided'}), 400

        try:
            img_data = base64.b64decode(data['image'])
            nparr = np.frombuffer(img_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        except Exception as e:
            logging.error(f"Image decoding error: {e}")
            return jsonify({'error': f'Image decoding failed: {str(e)}'}), 400

        if image is None:
            return jsonify({'error': 'Invalid image data - could not decode'}), 400

        result = face_server.recognize_face_realtime(image)
        result['timestamp'] = datetime.now().isoformat()
        
        return jsonify(result)

    except Exception as e:
        logging.error(f"Recognition endpoint error: {e}")
        logging.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'error': str(e),
            'recognized': False,
            'name': None,
            'confidence': 0.0,
            'message': f'Server error: {str(e)}',
            'quality_score': 0.0,
            'processing_time': 0.0,
            'model_loaded': face_server.model_loaded
        }), 500

@app.route('/api/recognize', methods=['POST'])
def recognize_person():
    """Original recognition endpoint - keeping for compatibility"""
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400

        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        image_bytes = file.read()
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if image is None:
            return jsonify({'error': 'Invalid image file'}), 400

        result = face_server.recognize_face_realtime(image)
        result['timestamp'] = datetime.now().isoformat()

        return jsonify({
            'recognized': result['recognized'],
            'name': result['name'],
            'confidence': result['confidence'],
            'message': result['message'],
            'timestamp': result['timestamp'],
            'model_loaded': result.get('model_loaded', False)
        })

    except Exception as e:
        logging.error(f"File recognition error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/register', methods=['POST'])
def register_person():
    """Register new person with enhanced error handling"""
    try:
        data = request.json
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        if 'name' not in data or 'images' not in data:
            return jsonify({'error': 'Name and images required'}), 400
        
        name = data['name'].strip()
        images = data['images']
        
        if not name:
            return jsonify({'error': 'Name cannot be empty'}), 400
        
        if not isinstance(images, list) or len(images) == 0:
            return jsonify({'error': 'At least one image required'}), 400
 
        result = face_server.add_person(name, images)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logging.error(f"Registration error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/people', methods=['GET'])
def list_people():
    """List all registered people"""
    try:
        conn = sqlite3.connect(face_server.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT name, photo_count, created_at FROM people
            ORDER BY created_at DESC
        ''')
        
        people = []
        for row in cursor.fetchall():
            people.append({
                'name': row[0],
                'photo_count': row[1],
                'created_at': row[2]
            })
        
        conn.close()
        
        return jsonify({
            'people': people,
            'total_count': len(people)
        })
        
    except Exception as e:
        logging.error(f"List people error: {e}")
        return jsonify({'error': str(e)}), 500

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

@app.route('/api/analytics', methods=['GET'])
def get_analytics():
    """Get recognition analytics"""
    try:
        conn = sqlite3.connect(face_server.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT person_name, COUNT(*) as recognition_count, 
                   AVG(confidence) as avg_confidence, 
                   MAX(timestamp) as last_seen
            FROM recognition_logs 
            WHERE timestamp > datetime('now', '-24 hours')
            GROUP BY person_name
            ORDER BY recognition_count DESC
        ''')
        
        recent_recognitions = []
        for row in cursor.fetchall():
            recent_recognitions.append({
                'name': row[0],
                'recognition_count': row[1],
                'avg_confidence': row[2],
                'last_seen': row[3]
            })
        
        conn.close()
        
        return jsonify({
            'recognition_stats': face_server.recognition_stats,
            'recent_recognitions': recent_recognitions,
            'cache_performance': {
                'cache_size': len(face_server.recognition_cache),
                'cache_hit_rate': (face_server.recognition_stats['cache_hits'] / 
                                 max(face_server.recognition_stats['total_requests'], 1)) * 100
            }
        })
        
    except Exception as e:
        logging.error(f"Analytics error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/test', methods=['GET'])
def test_endpoint():
    """Test endpoint to check if server is working"""
    return jsonify({
        'status': 'Server is working',
        'model_loaded': face_server.model_loaded,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/camera/start',methods=['POST'])
def start_camera():
    """start camera endpoint"""
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
        if success:
            return jsonify({
                'success': True,
                'message': 'Camera stopped successfully',
                'camera_active': False,
                'timestamp': datetime.now().isoformat()
            })
        else:
            logging.error("Failed to stop camera")
            return jsonify({
                'success': False,
                'message': 'No active camera found',
                'camera_active': True
            }), 500
    except Exception as e:
        logging.error(f"Camera stop endpoint error: {e}")
        return jsonify({
            'success': True,
            'message': 'Camera stop requested',
            'camera_active': False,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logging.error(f"Camera stop endpoint error: {e}")
        return jsonify({
            'success': False,
            'message': f'Camera error: {str(e)}'
        }), 500
    
    
@app.route('/api/camera/frame', methods=['GET'])
def get_camera_frame():
    """Get current camera frame with face recognition"""
    try:
        if not face_server.camera_active:
            logging.warning("Camera not active")
            return jsonify({
                'error': 'Camera not active',
                'image': '',
                'recognized': False,
                'message': 'Camera not available',
                'confidence': 0.0,
                'timestamp': datetime.now().isoformat()
            }), 500
        
        if face_server.camera_error:
            logging.error(f"Camera error: {face_server.camera_error}")
            return jsonify({
                'error': face_server.camera_error,
                'image': '',
                'recognized': False,
                'message': 'Camera error',
                'confidence': 0.0,
                'timestamp': datetime.now().isoformat()
            }), 500
        
        frame = face_server.capture_frame()
        if frame is None:
            logging.info("Attempting to restart camera...")
            if face_server.start_camera():
                frame = face_server.capture_frame()
                
            if frame is None:
                return jsonify({
                    'error': 'Failed to capture frame',
                    'image': '',
                    'recognized': False,
                    'message': 'Frame capture failed',
                    'confidence': 0.0,
                    'timestamp': datetime.now().isoformat()
                }), 500
        
        frame_base64 = face_server.frame_to_base64(frame)
        if frame_base64 is None:
            return jsonify({
                'error': 'Failed to encode frame',
                'image': '',
                'recognized': False,
                'message': 'Frame encoding failed',
                'confidence': 0.0,
                'timestamp': datetime.now().isoformat()
            }), 500
        
        recognition_result = face_server.recognize_face_realtime(frame)
        
        return jsonify({
            'image': frame_base64,
            'recognized': recognition_result.get('recognized', False),
            'message': recognition_result.get('message', 'Processing...'),
            'confidence': recognition_result.get('confidence', 0.0),
            'quality_score': recognition_result.get('quality_score', 0.0),
            'processing_time': recognition_result.get('processing_time', 0.0),
            'name': recognition_result.get('name', None),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logging.error(f"Frame endpoint error: {e}")
        logging.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({
            'error': f'Frame capture error: {str(e)}',
            'image': '',
            'recognized': False,
            'message': 'Server error',
            'confidence': 0.0,
            'timestamp': datetime.now().isoformat()
        }), 500
    
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

def cleanup_camera():
    """Cleanup camera resources"""
    if hasattr(face_server, 'camera') and face_server.camera:
        face_server.stop_camera()
        logging.info("Camera resources cleaned up")

atexit.register(cleanup_camera)

if __name__ == '__main__':
    print("="*60)

    camera_available = False
    for i in range(3):
        test_cam = cv2.VideoCapture(i)
        if test_cam.isOpened():
            camera_available = True
            test_cam.release()
            time.sleep(0.1)
            break
    
    print(f"Camera Status: {'✅ Available' if camera_available else '❌ Not Available'}")
    
    local_ip = get_local_ip()
    port = 5000
    
    print(f"\n📱 Android App Configuration:")
    print(f"   Server IP: {local_ip}")
    print(f"   Server Port: {port}")
    print(f"   Full URL: http://{local_ip}:{port}")
    
    print(f"\n🔗 API Endpoints:")
    print(f"   Web Interface: GET /")
    print(f"   Test Server: GET /api/test")
    print(f"   Real-time Recognition: POST /api/recognize_realtime")
    print(f"   File Recognition: POST /api/recognize")
    print(f"   Register Person: POST /api/register")
    print(f"   Server Health: GET /api/health")
    print(f"   Analytics: GET /api/analytics")
    print(f"   List People: GET /api/people")
    print(f"   Delete Person: DELETE /api/delete_person")
    print(f"   Camera Start: POST /api/camera/start")
    print(f"   Camera Stop: POST /api/camera/stop")
    print(f"   Camera Frame: GET /api/camera/frame")
    
    print(f"\n📦 Checking dependencies...")
    try:
        import insightface
        print("  ✅ InsightFace available")
    except ImportError:
        print("  ❌ InsightFace not installed - pip install insightface")
    
    try:
        from sklearn.metrics.pairwise import cosine_similarity
        print("  ✅ scikit-learn available")
    except ImportError:
        print("  ❌ scikit-learn not installed - pip install scikit-learn")
    
    try:
        import cv2
        print("  ✅ OpenCV available")
    except ImportError:
        print("  ❌ OpenCV not installed - pip install opencv-python")
        
    
    print("\n" + "="*60)
    print("Server starting... Press Ctrl+C to stop")
    print("="*60)
    
    if not os.path.exists('face_server_index.html'):
        print("⚠️  WARNING: face_server_index.html not found in current directory!")
        print("   Web interface may not be available")
    
    try:
        app.run(
            host='0.0.0.0',
            port=port,
            debug=False,
            threaded=True
        )
    except KeyboardInterrupt:
        print("\n\nShutting down face recognition server...")
        cleanup_camera()
        print("Face recognition server stopped and resources released.")