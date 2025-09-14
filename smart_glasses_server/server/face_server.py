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

try:
    from picamera2 import Picamera2
    from libcamera import controls

    RPI_CAMERA_AVAILABLE = True;
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


class EnhancedFaceRecognitionServer:
    def __init__(self):
        self.model = None
        self.model_loaded = False
        self.db_path = "face_database.db"
        self.face_encodings = {}

        self.recognition_threshold = 0.12
        self.quality_threshold = 0.10
        self.min_face_size = 40
        self.max_embeddings_per_person = 20  

        self.recognition_cache = {}
        self.cache_duration = 3.0 

        self.picamera2 = None
        self.camera_mode = None
        self.camera_width = 1920
        self.camera_height = 1080
        self.fps = 30
        self.rpi_camera_config = None
        self.camera= None
        self.camera_active = False
        self.camera_lock = threading.Lock()
        self.last_frame = None
        self.frame_capture_thread = None
        self.stop_capture = False

        self.temporal_window = 8 
        self.temporal_results = deque(maxlen=self.temporal_window)
        self.confidence_boost_threshold = 0.50
        
        self.averaging_methods = {
            'weighted_average': True,
            'outlier_removal': True,
            'adaptive_threshold': True
        }

        self.camera_error = None
        
        self.recognition_stats = {
            'total_requests': 0,
            'successful_recognitions': 0,
            'cache_hits': 0,
            'avg_processing_time': 0.0,
            'errors': 0,
            'high_confidence_recognitions': 0,
            'low_quality_rejections': 0,
            'temporal_smoothing_applied': 0,
            'weighted_average_applied': 0,
            'outliers_removed': 0,
            'adaptive_threshold_used': 0
        }
        
        self.recognition_history = defaultdict(list)
        self.history_window = 15  
        self.temporal_threshold = 0.55

        self.confidence_levels = {
            'very_high': 0.85,
            'high': 0.75,
            'medium': 0.60,
            'low': 0.45,
            'very_low': 0.30
        }

        self.daily_stats = defaultdict(lambda: {
            'recognitions': 0,
            'unique_people': set(),
            'avg_confidence': 0.0,
            'quality_scores': []
        })

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
                logging.info("Loading InsightFace model ...")

                self.model = insightface.app.FaceAnalysis(
                    providers=['CPUExecutionProvider'],
                    allowed_modules=['detection','recognition']
                )
                self.model.prepare(ctx_id=0, det_size=(640, 640))
            
                test_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
                test_faces = self.model.get(test_image)
            
                self.model_loaded = True
                logging.info("InsightFace model loaded and tested successfully")
                return True
                
            except Exception as e:
                logging.info("Attempting to download InsightFace models...")
            try:
                import insightface.model_zoo as model_zoo
                det_model = model_zoo.get_model('retinaface_r50_v1')
                rec_model = model_zoo.get_model('arcface_r100_v1')
                logging.info("Models downloaded, retrying initialization...")
                
                self.model = insightface.app.FaceAnalysis(
                    providers=['CPUExecutionProvider'],
                    allowed_modules=['detection', 'recognition']
                )
                self.model.prepare(ctx_id=0, det_size=(640, 640))
                self.model_loaded = True
                logging.info("InsightFace model loaded successfully after manual download")
                return True
                
            except Exception as download_error:
                logging.error(f"Model download failed: {download_error}")
                self.model_loaded = False
                return False
                
        except Exception as e:
            logging.error(f"Unexpected error in model initialization: {e}")
            self.model_loaded = False
            return False

    def init_database(self):
        """Initialize SQLite database with tables"""
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
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    source TEXT DEFAULT 'realtime'
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_date DATE UNIQUE,
                    total_recognitions INTEGER DEFAULT 0,
                    unique_people_count INTEGER DEFAULT 0,
                    avg_confidence REAL DEFAULT 0.0,
                    avg_quality REAL DEFAULT 0.0,
                    avg_processing_time REAL DEFAULT 0.0,
                    top_recognized_person TEXT,
                    report_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            logging.info("Enhanced database initialized successfully")
            
        except Exception as e:
            logging.error(f"Database initialization error: {e}")

    def load_face_database(self):
        """Load existing face encodings with metadata"""
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
                
                self.face_encodings[name].append({
                    'encoding': encoding,
                    'quality': quality,
                    'weight': weight
                })
            
            conn.close()
            logging.info(f"Loaded {len(self.face_encodings)} people from database")
            
            for name in self.face_encodings:
                self.face_encodings[name].sort(key=lambda x: x['quality'], reverse=True)
                
        except Exception as e:
            logging.error(f"Error loading face database: {e}")

    def extract_face_encoding(self, image):
        """face encoding extraction with better quality assessment"""
        try:
            if not self.model_loaded:
                logging.warning("InsightFace model not loaded, using fallback")
                return self.fallback_face_detection(image)
            
            faces = self.model.get(image)
            if len(faces) == 0:
                return None, 0.0, None

            face = max(faces, key=lambda x: self._calculate_face_priority(x, image.shape))
            
            face_area = (face.bbox[2] - face.bbox[0]) * (face.bbox[3] - face.bbox[1])
            image_area = image.shape[0] * image.shape[1]
            size_ratio = face_area / image_area

            blur_score = self._calculate_blur_score(image, face.bbox)
            lightning_score = self._calculate_lightning_score(image, face.bbox)
            angle_score = self._calculate_face_angle_score(face)
            symmetry_score = self._calculate_face_symmetry_score(face)
            eye_openness_score = self._calculate_eye_openness_score(face)

            quality_score = min(1.0, 
                size_ratio * 0.30 +       
                blur_score * 0.20 +       
                lightning_score * 0.25 +   
                angle_score * 0.15 + 
                symmetry_score * 0.05 +    
                eye_openness_score * 0.05 + 
                0.15                      
            )
            
            face_info = {
                'bbox': face.bbox.tolist(),
                'area_ratio': float(size_ratio),
                'landmarks': face.kps.tolist() if hasattr(face, 'kps') else None,
                'quality_breakdown': {
                    'size': float(size_ratio * 0.30),
                    'blur': float(blur_score * 0.20),
                    'lighting': float(lightning_score * 0.25),
                    'angle': float(angle_score * 0.15),
                    'symmetry': float(symmetry_score * 0.05),
                    'eye_openness': float(eye_openness_score * 0.05),
                    'base_boost': 0.15
                }
            }
            
            return face.embedding, quality_score, face_info
            
        except Exception as e:
            logging.error(f"Error extracting face encoding: {e}")
            logging.error(f"Traceback: {traceback.format_exc()}")
            return None, 0.0, None

    def _calculate_face_priority(self, face, image_shape):
        """Calculate face priority for selection"""
        bbox = face.bbox
        face_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
        
        face_center_x = (bbox[0] + bbox[2]) / 2
        face_center_y = (bbox[1] + bbox[3]) / 2
        image_center_x = image_shape[1] / 2
        image_center_y = image_shape[0] / 2
        
        center_distance = np.sqrt(
            (face_center_x - image_center_x)**2 + 
            (face_center_y - image_center_y)**2
        )
        max_distance = np.sqrt(image_center_x**2 + image_center_y**2)
        center_score = 1.0 - (center_distance / max_distance)
        
        return face_area * (1 + center_score * 0.3)

    def _calculate_blur_score(self, image, bbox):
        """blur detection"""
        try:
            x1, y1, x2, y2 = map(int, bbox)
            face_roi = image[y1:y2, x1:x2]
            gray_face = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
            
            laplacian_var = cv2.Laplacian(gray_face, cv2.CV_64F).var()
            
            sobelx = cv2.Sobel(gray_face, cv2.CV_64F, 1, 0, ksize=3)
            sobely = cv2.Sobel(gray_face, cv2.CV_64F, 0, 1, ksize=3)
            sobel_magnitude = np.mean(np.sqrt(sobelx**2 + sobely**2))
            
            blur_score = min(1.0, (laplacian_var / 600.0 + sobel_magnitude / 150.0) / 2)
            return blur_score
        except:
            return 0.5
        
    def _calculate_lightning_score(self, image, bbox):
        """lighting quality assessment - more lenient"""
        try:
            x1, y1, x2, y2 = map(int, bbox)
            face_roi = image[y1:y2, x1:x2]
            gray_face = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
            
            mean_brightness = np.mean(gray_face)
            std_brightness = np.std(gray_face)
            
            if 60 <= mean_brightness <= 200:  
                brightness_score = 1.0
            else:
                brightness_score = max(0.3, 1.0 - abs(mean_brightness - 130) / 150) 
            
            contrast_score = min(1.0, std_brightness / 40.0)  
            
            lighting_score = (brightness_score * 0.6 + contrast_score * 0.4) 
            return max(0.4, lighting_score)  
            
        except:
            return 0.6 
        
    def _calculate_face_angle_score(self, face):
        """face angle assessment"""
        try:
            if hasattr(face, 'kps') and face.kps is not None:
                landmarks = face.kps
                left_eye = landmarks[0]
                right_eye = landmarks[1]
                nose = landmarks[2]
                left_mouth = landmarks[3]
                right_mouth = landmarks[4]
                
                eye_angle = abs(np.arctan2(right_eye[1] - left_eye[1], right_eye[0] - left_eye[0]))
                
                mouth_angle = abs(np.arctan2(right_mouth[1] - left_mouth[1], right_mouth[0] - left_mouth[0]))
                
                avg_angle = (eye_angle + mouth_angle) / 2
                angle_score = max(0.3, 1.0 - (avg_angle / 0.4))
                
                return min(1.0, angle_score)
            return 0.7
        except:
            return 0.7

    def _calculate_face_symmetry_score(self, face):
        """Calculate facial symmetry score"""
        try:
            if hasattr(face, 'kps') and face.kps is not None:
                landmarks = face.kps
                left_eye = landmarks[0]
                right_eye = landmarks[1]
                nose = landmarks[2]
                left_mouth = landmarks[3]
                right_mouth = landmarks[4]
                
                face_center_x = (left_eye[0] + right_eye[0]) / 2
                
                nose_center_dist = abs(nose[0] - face_center_x)
                
                left_eye_dist = abs(left_eye[0] - face_center_x)
                right_eye_dist = abs(right_eye[0] - face_center_x)
                eye_symmetry = 1.0 - abs(left_eye_dist - right_eye_dist) / max(left_eye_dist, right_eye_dist)
                
                symmetry_score = (eye_symmetry + (1.0 - nose_center_dist / 50.0)) / 2
                return max(0.3, min(1.0, symmetry_score))
            return 0.7
        except:
            return 0.7

    def _calculate_eye_openness_score(self, face):
        """Calculate eye openness score"""
        try:
            if hasattr(face, 'kps') and face.kps is not None:
                return 0.8  
            return 0.7
        except:
            return 0.7

    def fallback_face_detection(self, image):
        """fallback detection"""
        try:
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            
            if len(faces) == 0:
                return None, 0.0, None
            
            image_center = (image.shape[1]//2, image.shape[0]//2)
            best_face = None
            best_score = 0
            
            for (x, y, w, h) in faces:
                face_area = w * h
                face_center = (x + w//2, y + h//2)
                center_dist = np.sqrt((face_center[0] - image_center[0])**2 + 
                                    (face_center[1] - image_center[1])**2)
                max_dist = np.sqrt(image_center[0]**2 + image_center[1]**2)
                center_score = 1.0 - (center_dist / max_dist)
                
                total_score = face_area * (1 + center_score * 0.5)
                if total_score > best_score:
                    best_score = total_score
                    best_face = (x, y, w, h)
            
            x, y, w, h = best_face
            face_area = w * h
            image_area = image.shape[0] * image.shape[1]
            size_ratio = face_area / image_area
            quality_score = min(1.0, size_ratio * 6)
            
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

    def recognize_face_with_averaging(self, image):
        """Enhanced recognition with better matching"""
        start_time = time.time()
        
        try:
            encoding, quality, face_info = self.extract_face_encoding(image)
            
            if encoding is None:
                return {
                    'recognized': False,
                    'name': None,
                    'confidence': 0.0,
                    'message': "No face detected",
                    'processing_time': float(time.time() - start_time)
                }
            
            best_match = None
            best_confidence = 0.0
            
            for name, stored_data in self.face_encodings.items():
                confidences = []
                
                for data in stored_data:
                    stored_encoding = data['encoding']
                    
                    cosine_sim = np.dot(encoding, stored_encoding) / (
                        np.linalg.norm(encoding) * np.linalg.norm(stored_encoding)
                    )
                    
                    euclidean_dist = np.linalg.norm(encoding - stored_encoding)
                    euclidean_sim = 1.0 / (1.0 + euclidean_dist * 0.3)  # Reduced penalty
                    
                    dot_sim = np.dot(encoding, stored_encoding)
                    
                    combined_similarity = (
                        cosine_sim * 0.5 + 
                        euclidean_sim * 0.35 +  
                        dot_sim * 0.15
                    )
                    
                    quality_factor = min(1.3, (quality * 1.2 + data['quality'] * 0.8) / 1.5)  # More generous
                    final_confidence = combined_similarity * quality_factor
                    
                    confidences.append(final_confidence)
                
                if confidences:
                    top_scores = sorted(confidences, reverse=True)[:min(3, len(confidences))]
                    avg_confidence = sum(top_scores) / len(top_scores)
                    
                    good_matches = [c for c in confidences if c > 0.10]  
                    if len(good_matches) >= 2:
                        avg_confidence *= 1.15  
                    elif len(good_matches) >= 3:
                        avg_confidence *= 1.25
                    
                    if avg_confidence > best_confidence:
                        best_confidence = avg_confidence
                        best_match = name
            
            processing_time = time.time() - start_time
            
            if best_confidence > 0.12: 
                self.log_recognition(best_match, best_confidence, quality, processing_time, 'enhanced_matching')
                
                return {
                    'recognized': True,
                    'name': best_match,
                    'confidence': float(best_confidence),
                    'message': f"Recognized {best_match}",
                    'quality_score': float(quality),
                    'processing_time': float(processing_time),
                    'method_used': 'enhanced_matching'
                }
            else:
                return {
                    'recognized': False,
                    'name': None,
                    'confidence': float(best_confidence),
                    'message': "Unknown person",
                    'quality_score': float(quality),
                    'processing_time': float(processing_time),
                    'method_used': 'enhanced_matching'
                }
                
        except Exception as e:
            logging.error(f"Recognition error: {e}")
            return {
                'recognized': False,
                'name': None,
                'confidence': 0.0,
                'message': f"Error: {str(e)}",
                'processing_time': float(time.time() - start_time),
                'method_used': 'error'
            }

        
    def frame_to_base64_quality(self, frame, quality=85):
        """Convert frame to base64 string with adjustable quality"""
        try:
            if frame is None:
                return None
        
            quality = max(90, min(100, quality))
        
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
            if not ret:
                logging.error("Failed to encode frame to JPEG")
                return None
        
            jpg_as_text = base64.b64encode(buffer).decode('utf-8')
            return jpg_as_text
    
        except Exception as e:
            logging.error(f"Error converting frame to base64: {e}")
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

    def _match_with_averaging(self, encoding, quality):
        """matching with multiple averaging methods"""
        if not self.model_loaded or not self.face_encodings:
            return None, 0.0, "no_model_or_data"
        
        try:
            from sklearn.metrics.pairwise import cosine_similarity
            
            best_match = None
            best_confidence = 0.0
            method_used = "standard"
            
            for name, stored_data in self.face_encodings.items():
                confidences = []
                weights = []
                qualities = []
                
                for data in stored_data:
                    stored_encoding = data['encoding']
                    stored_quality = data['quality']
                    
                    cosine_sim = cosine_similarity([encoding], [stored_encoding])[0][0]
                    
                    euclidean_dist = np.linalg.norm(encoding - stored_encoding)
                    euclidean_sim = 1.0 / (1.0 + euclidean_dist * 0.5)  # Less penalty
                
                    dot_product = np.dot(encoding, stored_encoding)

                    combined_similarity = (
                    cosine_sim * 0.5 + 
                    euclidean_sim * 0.3 + 
                    dot_product * 0.2
                    )
                    
                    quality_factor = min(1.2, (quality + stored_quality) / 1.5)
                    final_similarity = combined_similarity * quality_factor
                    confidences.append(final_similarity)
                    weights.append(stored_quality + 0.1) 
                
                if not confidences:
                    
                    top_scores = sorted(confidences, reverse=True)[:min(3, len(confidences))]
                    final_confidence = sum(top_scores) / len(top_scores)
                
                    if len([c for c in confidences if c > 0.15]) >= 2:
                        final_confidence *= 1.1
                        method_used = "multi_match_boost"
                    
                    if final_confidence > best_confidence:
                        best_confidence = final_confidence
                        best_match = name
        
            return best_match, best_confidence, method_used
                
            
        except ImportError:
            return self._basic_matching_fallback(encoding, quality)

    def _get_confidence_level(self, confidence):
        """Get confidence level description"""
        if confidence >= self.confidence_levels['very_high']:
            return 'very_high'
        elif confidence >= self.confidence_levels['high']:
            return 'high'
        elif confidence >= self.confidence_levels['medium']:
            return 'medium'
        elif confidence >= self.confidence_levels['low']:
            return 'low'
        else:
            return 'very_low'

    def _update_daily_stats(self, name, confidence, quality, processing_time):
        """Update daily statistics"""
        today = datetime.now().date()
        stats = self.daily_stats[today]
        
        stats['recognitions'] += 1
        if name:
            stats['unique_people'].add(name)
        
        current_avg = stats['avg_confidence']
        count = stats['recognitions']
        stats['avg_confidence'] = ((current_avg * (count - 1)) + confidence) / count
        
        stats['quality_scores'].append(quality)

    def check_cache(self, image_hash):
        """cache with better expiry"""
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

    def log_recognition(self, person_name, confidence, quality_score, processing_time, method_used):
        """ recognition logging"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO recognition_logs 
                (person_name, confidence, quality_score, processing_time, method_used)
                VALUES (?, ?, ?, ?, ?)
            ''', (person_name, confidence, quality_score, processing_time, method_used))
            conn.commit()
            conn.close()
        except Exception as e:
            logging.error(f"Error logging recognition: {e}")

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

                        logging.info("usb camera started successfully as fallback")
                        return True
                
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
    
    def stop_camera(self):
        """Stop camera and cleanup"""
        try:
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

    def add_person_enhanced(self, name, images_base64):
        """Fixed registration - keep high quality images and lower requirements"""
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
                cursor.execute("INSERT INTO people (name, registration_method) VALUES (?, ?)", (name, 'enhanced'))
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

                    encoding, quality, face_info = self.extract_face_encoding(image)
                    
                    if encoding is not None and quality > 0.20: 
                        successful_encodings.append({
                            'encoding': encoding,
                            'quality': quality,
                            'weight': quality * 1.2 
                        })
                        quality_scores.append(quality)
                        logging.info(f"Kept image {i+1} for {name}, quality: {quality:.3f}")
                        
                except Exception as e:
                    logging.error(f"Error processing image {i+1}: {e}")
                    continue
            
            if len(successful_encodings) < 2:  
                conn.rollback()
                return {
                    'success': False,
                    'message': f'Need at least 2 good images. Got {len(successful_encodings)}',
                    'photos_processed': len(successful_encodings)
                }
            
            if len(successful_encodings) > 8:
                successful_encodings.sort(key=lambda x: x['quality'], reverse=True)
                successful_encodings = successful_encodings[:8]
                logging.info(f"Kept top 8 images for {name}")
            
            for enc_data in successful_encodings:
                encoding_blob = enc_data['encoding'].tobytes()
                cursor.execute('''
                    INSERT INTO face_encodings (person_id, encoding, image_quality, weight)
                    VALUES (?, ?, ?, ?)
                ''', (person_id, encoding_blob, enc_data['quality'], enc_data['weight']))
            
            avg_quality = sum([e['quality'] for e in successful_encodings]) / len(successful_encodings)
            best_quality = max([e['quality'] for e in successful_encodings])
            
            cursor.execute('''
                UPDATE people SET photo_count = ?, avg_quality = ?, best_quality = ? WHERE id = ?
            ''', (len(successful_encodings), avg_quality, best_quality, person_id))

            self.face_encodings[name] = successful_encodings
            
            conn.commit()
            conn.close()
            
            self.recognition_cache.clear()
            
            return {
                'success': True,
                'message': f'Successfully registered {name} with {len(successful_encodings)} images',
                'photos_processed': len(successful_encodings),
                'avg_quality': round(avg_quality * 100, 1),
                'best_quality': round(best_quality * 100, 1)
            }
                    
        except Exception as e:
            if 'conn' in locals():
                conn.rollback()
                conn.close()
            logging.error(f"Registration error: {e}")
            return {
                'success': False,
                'message': f'Registration error: {str(e)}',
                'photos_processed': 0
            }

    def _analyze_quality_distribution(self, quality_scores):
        """Analyze quality score distribution"""
        if not quality_scores:
            return {}
        
        return {
            'min': float(min(quality_scores)),
            'max': float(max(quality_scores)),
            'mean': float(statistics.mean(quality_scores)),
            'median': float(statistics.median(quality_scores)),
            'std_dev': float(statistics.stdev(quality_scores)) if len(quality_scores) > 1 else 0.0,
            'high_quality_count': sum(1 for q in quality_scores if q > 0.7),
            'medium_quality_count': sum(1 for q in quality_scores if 0.4 <= q <= 0.7),
            'low_quality_count': sum(1 for q in quality_scores if q < 0.4)
        }

    def _remove_encoding_outliers(self, encodings):
        """Remove outlier encodings based on similarity"""
        try:
            from sklearn.metrics.pairwise import cosine_similarity
            
            if len(encodings) <= 5:
                return encodings  
            
            encoding_vectors = [e['encoding'] for e in encodings]
            similarity_matrix = cosine_similarity(encoding_vectors)
            
            avg_similarities = []
            for i in range(len(encodings)):
                similarities = [similarity_matrix[i][j] for j in range(len(encodings)) if i != j]
                avg_similarities.append(statistics.mean(similarities))
            
            threshold = statistics.mean(avg_similarities) - statistics.stdev(avg_similarities)
            
            filtered_encodings = []
            for i, encoding in enumerate(encodings):
                if avg_similarities[i] >= threshold:
                    filtered_encodings.append(encoding)
            
            min_keep = max(3, int(len(encodings) * 0.6))
            if len(filtered_encodings) < min_keep:
                indexed_encodings = [(i, e) for i, e in enumerate(encodings)]
                indexed_encodings.sort(key=lambda x: avg_similarities[x[0]], reverse=True)
                filtered_encodings = [e for i, e in indexed_encodings[:min_keep]]
            
            return filtered_encodings
            
        except Exception as e:
            logging.error(f"Error removing outliers: {e}")
            return encodings  

    def generate_daily_report(self, date=None):
        """Generate comprehensive daily analysis report"""
        if date is None:
            date = datetime.now().date()
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT person_name, confidence, quality_score, processing_time, method_used, timestamp
                FROM recognition_logs 
                WHERE DATE(timestamp) = ?
                ORDER BY timestamp DESC
            ''', (date,))
            
            daily_recognitions = cursor.fetchall()
            
            if not daily_recognitions:
                return {
                    'date': str(date),
                    'summary': 'No recognitions recorded for this date',
                    'total_recognitions': 0
                }
            
            people_stats = defaultdict(lambda: {
                'count': 0,
                'confidences': [],
                'qualities': [],
                'processing_times': [],
                'methods': [],
                'first_seen': None,
                'last_seen': None
            })
            
            total_recognitions = 0
            all_confidences = []
            all_qualities = []
            all_processing_times = []
            method_counts = defaultdict(int)
            hourly_distribution = defaultdict(int)
            
            for name, confidence, quality, proc_time, method, timestamp in daily_recognitions:
                if name: 
                    total_recognitions += 1
                    stats = people_stats[name]
                    stats['count'] += 1
                    stats['confidences'].append(confidence)
                    stats['qualities'].append(quality)
                    stats['processing_times'].append(proc_time)
                    stats['methods'].append(method)
                    
                    if stats['first_seen'] is None:
                        stats['first_seen'] = timestamp
                    stats['last_seen'] = timestamp
                    
                    all_confidences.append(confidence)
                    all_qualities.append(quality)
                    all_processing_times.append(proc_time)
                    method_counts[method] += 1
                    
                    hour = datetime.fromisoformat(timestamp).hour
                    hourly_distribution[hour] += 1
            
            unique_people = len(people_stats)
            avg_confidence = statistics.mean(all_confidences) if all_confidences else 0
            avg_quality = statistics.mean(all_qualities) if all_qualities else 0
            avg_processing_time = statistics.mean(all_processing_times) if all_processing_times else 0
            
            top_person = max(people_stats.keys(), key=lambda x: people_stats[x]['count']) if people_stats else None
            
            people_analysis = []
            for name, stats in people_stats.items():
                people_analysis.append({
                    'name': name,
                    'recognition_count': stats['count'],
                    'avg_confidence': statistics.mean(stats['confidences']),
                    'confidence_std': statistics.stdev(stats['confidences']) if len(stats['confidences']) > 1 else 0,
                    'avg_quality': statistics.mean(stats['qualities']),
                    'avg_processing_time': statistics.mean(stats['processing_times']),
                    'most_used_method': max(set(stats['methods']), key=stats['methods'].count),
                    'first_seen': stats['first_seen'],
                    'last_seen': stats['last_seen'],
                    'confidence_level': self._get_confidence_level(statistics.mean(stats['confidences']))
                })
            
            people_analysis.sort(key=lambda x: x['recognition_count'], reverse=True)
            
            performance_insights = []
            
            if avg_confidence > 0.8:
                performance_insights.append("High confidence recognitions today")
            elif avg_confidence < 0.6:
                performance_insights.append("Lower than usual confidence levels")
                
            if avg_processing_time > 0.5:
                performance_insights.append("Slower processing times detected")
            elif avg_processing_time < 0.1:
                performance_insights.append("Fast processing performance")
                
            if 'weighted_average' in method_counts and method_counts['weighted_average'] > total_recognitions * 0.5:
                performance_insights.append(" Advanced averaging methods frequently used")
                
            report_data = {
                'people_analysis': people_analysis,
                'method_distribution': dict(method_counts),
                'hourly_distribution': dict(hourly_distribution),
                'performance_insights': performance_insights
            }
            
            cursor.execute('''
                INSERT OR REPLACE INTO daily_reports 
                (report_date, total_recognitions, unique_people_count, avg_confidence, 
                 avg_quality, avg_processing_time, top_recognized_person, report_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (date, total_recognitions, unique_people, avg_confidence, avg_quality,
                  avg_processing_time, top_person, json.dumps(report_data)))
            
            conn.commit()
            conn.close()
            
            return {
                'date': str(date),
                'summary': {
                    'total_recognitions': total_recognitions,
                    'unique_people': unique_people,
                    'avg_confidence': round(avg_confidence, 3),
                    'avg_quality': round(avg_quality, 3),
                    'avg_processing_time': round(avg_processing_time * 1000, 1), 
                    'top_recognized_person': top_person
                },
                'people_analysis': people_analysis[:10],  
                'method_distribution': dict(method_counts),
                'hourly_distribution': dict(hourly_distribution),
                'performance_insights': performance_insights,
                'confidence_distribution': {
                    'very_high': sum(1 for c in all_confidences if c >= self.confidence_levels['very_high']),
                    'high': sum(1 for c in all_confidences if self.confidence_levels['high'] <= c < self.confidence_levels['very_high']),
                    'medium': sum(1 for c in all_confidences if self.confidence_levels['medium'] <= c < self.confidence_levels['high']),
                    'low': sum(1 for c in all_confidences if self.confidence_levels['low'] <= c < self.confidence_levels['medium']),
                    'very_low': sum(1 for c in all_confidences if c < self.confidence_levels['low'])
                }
            }
            
        except Exception as e:
            logging.error(f"Error generating daily report: {e}")
            return {
                'date': str(date),
                'error': str(e),
                'summary': 'Error generating report'
            }

face_server = EnhancedFaceRecognitionServer()
connected_clients = {}

@app.route('/')
def web_interface():
    """Web interface for testing"""
    return render_template('face_server_index.html')

@app.route('/api/health', methods=['GET'])
def health_check():
    """health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'model_loaded': face_server.model_loaded,
        'people_count': len(face_server.face_encodings),
        'camera_active': face_server.camera_active,
        'camera_mode': face_server.camera_mode,
        'camera_error': face_server.camera_error,
        'rpi_camera_available': RPI_CAMERA_AVAILABLE,
        'recognition_stats': face_server.recognition_stats,
        'cache_size': len(face_server.recognition_cache),
        'averaging_methods': face_server.averaging_methods,
        'confidence_levels': face_server.confidence_levels
    })


@app.route('/api/recognize_realtime', methods=['POST'])
def recognize_realtime():
    """Real-time recognition endpoint with averaging"""
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

        result = face_server.recognize_face_with_averaging(image)
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
            'model_loaded': face_server.model_loaded,
            'method_used': 'error'
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

        result = face_server.recognize_face_with_averaging(image)
        result['timestamp'] = datetime.now().isoformat()

        return jsonify({
            'recognized': result['recognized'],
            'name': result['name'],
            'confidence': result['confidence'],
            'confidence_level': result.get('confidence_level', 'unknown'),
            'message': result['message'],
            'timestamp': result['timestamp'],
            'model_loaded': result.get('model_loaded', False),
            'method_used': result.get('method_used', 'unknown')
        })

    except Exception as e:
        logging.error(f"File recognition error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/register_enhanced', methods=['POST'])
def register_person_enhanced():
    """registration endpoint for 10-15 images"""
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
        
        if not isinstance(images, list):
            return jsonify({'error': 'Images must be a list'}), 400
            
        if len(images) < 5:
            return jsonify({'error': 'Minimum 5 images required for registration'}), 400
            
        if len(images) > 20:
            return jsonify({'error': 'Maximum 20 images allowed'}), 400
 
        result = face_server.add_person_enhanced(name, images)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logging.error(f"Enhanced registration error: {e}")
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/analyze_person/<name>')
def analyze_person(name):
    """Analyze a specific person's registration quality"""
    try:
        conn = sqlite3.connect(face_server.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT fe.image_quality, fe.weight 
            FROM people p 
            JOIN face_encodings fe ON p.id = fe.person_id 
            WHERE p.name = ?
        """, (name,))
        
        results = cursor.fetchall()
        conn.close()
        
        if not results:
            return jsonify({'error': 'Person not found'})
            
        qualities = [r[0] for r in results]
        weights = [r[1] for r in results]
        
        return jsonify({
            'name': name,
            'photo_count': len(qualities),
            'avg_quality': sum(qualities) / len(qualities),
            'min_quality': min(qualities),
            'max_quality': max(qualities),
            'qualities': qualities,
            'weights': weights,
            'recommendations': {
                'should_retake_photos': max(qualities) < 0.4,
                'needs_better_lighting': sum(q < 0.3 for q in qualities) > len(qualities) // 2,
                'has_good_photos': any(q > 0.5 for q in qualities)
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/register', methods=['POST'])
def register_person():
    """Legacy registration endpoint - redirects to enhanced registration"""
    try:
        data = request.json
        
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        if 'name' not in data or 'images' not in data:
            return jsonify({'error': 'Name and images required'}), 400
        
        return register_person_enhanced()
            
    except Exception as e:
        logging.error(f"Legacy registration error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/people', methods=['GET'])
def list_people():
    """List all registered people with details"""
    try:
        conn = sqlite3.connect(face_server.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT name, photo_count, created_at, avg_quality, best_quality, registration_method
            FROM people
            ORDER BY created_at DESC
        ''')
        
        people = []
        for row in cursor.fetchall():
            people.append({
                'name': row[0],
                'photo_count': row[1],
                'created_at': row[2],
                'avg_quality': round(row[3] or 0, 3),
                'best_quality': round(row[4] or 0, 3),
                'registration_method': row[5] or 'standard'
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

@app.route('/api/analytics_enhanced', methods=['GET'])
def get_enhanced_analytics():
    """Get comprehensive recognition analytics"""
    try:
        conn = sqlite3.connect(face_server.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT person_name, COUNT(*) as recognition_count, 
                   AVG(confidence) as avg_confidence, 
                   AVG(quality_score) as avg_quality,
                   AVG(processing_time) as avg_processing_time,
                   MAX(timestamp) as last_seen
            FROM recognition_logs 
            WHERE timestamp > datetime('now', '-24 hours')
            AND person_name IS NOT NULL
            GROUP BY person_name
            ORDER BY recognition_count DESC
        ''')
        
        recent_recognitions = []
        for row in cursor.fetchall():
            recent_recognitions.append({
                'name': row[0],
                'recognition_count': row[1],
                'avg_confidence': round(row[2], 3),
                'confidence_level': face_server._get_confidence_level(row[2]),
                'avg_quality': round(row[3], 3),
                'avg_processing_time': round(row[4] * 1000, 1),
                'last_seen': row[5]
            })
        
        cursor.execute('''
            SELECT method_used, COUNT(*) as usage_count
            FROM recognition_logs 
            WHERE timestamp > datetime('now', '-24 hours')
            GROUP BY method_used
            ORDER BY usage_count DESC
        ''')
        
        method_usage = {}
        for row in cursor.fetchall():
            method_usage[row[0]] = row[1]

        cursor.execute('''
            SELECT strftime('%H', timestamp) as hour, COUNT(*) as count
            FROM recognition_logs 
            WHERE timestamp > datetime('now', '-24 hours')
            AND person_name IS NOT NULL
            GROUP BY hour
            ORDER BY hour
        ''')
        
        hourly_distribution = {}
        for row in cursor.fetchall():
            hourly_distribution[int(row[0])] = row[1]
        
        conn.close()
        
        return jsonify({
            'recognition_stats': face_server.recognition_stats,
            'recent_recognitions': recent_recognitions,
            'method_usage': method_usage,
            'hourly_distribution': hourly_distribution,
            'cache_performance': {
                'cache_size': len(face_server.recognition_cache),
                'cache_hit_rate': (face_server.recognition_stats['cache_hits'] / 
                                 max(face_server.recognition_stats['total_requests'], 1)) * 100
            },
            'averaging_methods': face_server.averaging_methods,
            'confidence_levels': face_server.confidence_levels
        })
        
    except Exception as e:
        logging.error(f"Enhanced analytics error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/daily_report', methods=['GET'])
def get_daily_report():
    """Get daily analysis report"""
    try:
        date_str = request.args.get('date')
        if date_str:
            try:
                report_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        else:
            report_date = datetime.now().date()
        
        report = face_server.generate_daily_report(report_date)
        return jsonify(report)
        
    except Exception as e:
        logging.error(f"Daily report error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/recognition_logs', methods=['GET'])
def get_recognition_logs():
    """Get recognition logs for a specific date"""
    try:
        date_str = request.args.get('date')
        if date_str:
            try:
                report_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        else:
            report_date = datetime.now().date()
        
        conn = sqlite3.connect(face_server.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT person_name, confidence, quality_score, processing_time, method_used, timestamp
            FROM recognition_logs 
            WHERE DATE(timestamp) = ?
            ORDER BY timestamp DESC
        ''', (report_date,))
        
        logs = []
        total_confidence = 0
        total_quality = 0
        
        for row in cursor.fetchall():
            person_name, confidence, quality, proc_time, method, timestamp = row
            logs.append({
                'person_name': person_name,
                'confidence': confidence,
                'quality_score': quality,
                'processing_time': proc_time,
                'method_used': method,
                'timestamp': timestamp
            })
            total_confidence += confidence
            total_quality += quality
        
        conn.close()
        
        avg_confidence = total_confidence / len(logs) if logs else 0
        avg_quality = total_quality / len(logs) if logs else 0
        
        return jsonify({
            'logs': logs,
            'total_logs': len(logs),
            'avg_confidence': avg_confidence,
            'avg_quality': avg_quality
        })
        
    except Exception as e:
        logging.error(f"Recognition logs error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/historical_data', methods=['GET'])
def get_historical_data():
    """Get historical performance data for the last 7 days"""
    try:
        date_str = request.args.get('date')
        if date_str:
            try:
                base_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        else:
            base_date = datetime.now().date()
        
        conn = sqlite3.connect(face_server.db_path)
        cursor = conn.cursor()
        
        days = []
        total_recognitions = 0
        best_day = 0
        best_day_date = None
        
        for i in range(7):
            check_date = base_date - timedelta(days=i)
            
            cursor.execute('''
                SELECT COUNT(*) as recognition_count
                FROM recognition_logs 
                WHERE DATE(timestamp) = ?
            ''', (check_date,))
            
            count = cursor.fetchone()[0]
            days.append({
                'date': str(check_date),
                'recognitions': count
            })
            
            total_recognitions += count
            if count > best_day:
                best_day = count
                best_day_date = check_date
        
        conn.close()
        
        avg_daily = total_recognitions / 7
        trend = "Stable"
        if len(days) >= 2:
            recent_avg = sum(d['recognitions'] for d in days[:3]) / 3
            older_avg = sum(d['recognitions'] for d in days[3:]) / 4 if len(days) > 3 else 0
            if recent_avg > older_avg * 1.2:
                trend = "Increasing"
            elif recent_avg < older_avg * 0.8:
                trend = "Decreasing"
        
        return jsonify({
            'days': days,
            'total_recognitions': total_recognitions,
            'avg_daily': round(avg_daily, 1),
            'best_day': best_day_date.strftime('%b %d') if best_day_date else "None",
            'trend': trend,
            'total_days': len([d for d in days if d['recognitions'] > 0])
        })
        
    except Exception as e:
        logging.error(f"Historical data error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate_test_data', methods=['POST'])
def generate_test_data():
    """Generate test recognition data for today"""
    try:
        conn = sqlite3.connect(face_server.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM people")
        people = [row[0] for row in cursor.fetchall()]
        
        if not people:
            return jsonify({
                'success': False,
                'error': 'No registered people found. Please register at least one person first.'
            }), 400
        
        today = datetime.now().date()
        test_data_count = 0
        
        import random
        for i in range(random.randint(10, 20)):
            person = random.choice(people)
            confidence = random.uniform(0.6, 0.95)
            quality = random.uniform(0.4, 0.8)
            processing_time = random.uniform(0.1, 0.5)
            method = random.choice(['standard', 'weighted_average', 'temporal', 'enhanced'])
            
            hour = random.randint(8, 20)
            minute = random.randint(0, 59)
            second = random.randint(0, 59)
            timestamp = datetime.combine(today, datetime.min.time().replace(hour=hour, minute=minute, second=second))
            
            cursor.execute('''
                INSERT INTO recognition_logs 
                (person_name, confidence, quality_score, processing_time, method_used, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (person, confidence, quality, processing_time, method, timestamp))
            
            test_data_count += 1
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'Generated {test_data_count} test recognition records for today',
            'records_created': test_data_count
        })
        
    except Exception as e:
        logging.error(f"Test data generation error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/test', methods=['GET'])
def test_endpoint():
    """Test endpoint to check if server is working"""
    return jsonify({
        'status': ' Server is working',
        'model_loaded': face_server.model_loaded,
        'features': {
            'enhanced_registration': True,
            'weighted_averaging': True,
            'outlier_removal': True,
            'temporal_smoothing': True,
            'quality_analysis': True,
            'daily_reports': True
        },
        'timestamp': datetime.now().isoformat()
    })

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
    
    
@app.route('/api/camera/frame', methods=['GET'])
def get_camera_frame():
    """Get current camera frame with face recognition"""
    try:
        include_image = request.args.get('include_image', 'true').lower() == 'true'
        image_quality = int(request.args.get('quality', '85'))
        recognition_only = request.args.get('recognition_only', 'false').lower() == 'true'
        
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

        processed_frame = face_server.preprocess_camera_frame(frame)
        recognition_result = face_server.recognize_face_with_averaging(processed_frame)
        
        
        response_data = {
            'recognized': recognition_result.get('recognized', False),
            'message': recognition_result.get('message', 'Processing...'),
            'confidence': recognition_result.get('confidence', 0.0),
            'confidence_level': recognition_result.get('confidence_level', 'unknown'),
            'quality_score': recognition_result.get('quality_score', 0.0),
            'processing_time': recognition_result.get('processing_time', 0.0),
            'method_used': recognition_result.get('method_used', 'unknown'),
            'name': recognition_result.get('name', None),
            'timestamp': datetime.now().isoformat()
        }

        if include_image and not recognition_only:
            frame_base64 = face_server.frame_to_base64_quality(frame, image_quality)
            if frame_base64 is None:
                return jsonify({
                    'error': 'Failed to encode frame',
                    **response_data
                }), 500
            response_data['image'] = frame_base64
        elif include_image:
            response_data['image'] = ''
        else:
            pass
            
        return jsonify(response_data)
        
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

@app.route('/', methods=['POST'])
def register_face_java():
    """Face registration endpoint"""
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'message': 'No JSON data provided'}), 400
        
        name = data.get('name', '').strip()
        images = data.get('images', [])
        
        if not name:
            return jsonify({'success': False, 'message': 'Name required'}), 400
        
        if not images:
            return jsonify({'success': False, 'message': 'Images required'}), 400
        
        result = face_server.add_person_enhanced(name, images)
        
        return jsonify({
            'success': result['success'],
            'message': result['message']
        })
        
    except Exception as e:
        logging.error(f"Java registration error: {e}")
        return jsonify({
            'success': False, 
            'message': f'Registration error: {str(e)}'
        }), 500
    
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
    


if __name__ == '__main__':
    print("="*80)

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
    port = 5000
    
    print(f"\n App Configuration:")
    print(f"   Server IP: {local_ip}")
    print(f"   Server Port: {port}")
    print(f"   Full URL: http://{local_ip}:{port}")
    
    print(f"\n API Endpoints:")
    print(f"   Web Interface: GET /")
    print(f"   Test Server: GET /api/test")
    print(f"   Real-time Recognition: POST /api/recognize_realtime")
    print(f"   File Recognition: POST /api/recognize")
    print(f"   Registration: POST /api/register_enhanced")
    print(f"   Legacy Registration: POST /api/register")
    print(f"   Server Health: GET /api/health")
    print(f"   Analytics: GET /api/analytics_enhanced")
    print(f"   Daily Report: GET /api/daily_report?date=YYYY-MM-DD")
    print(f"   List People: GET /api/people")
    print(f"   Delete Person: DELETE /api/delete_person")
    print(f"   Camera Start: POST /api/camera/start")
    print(f"   Camera Stop: POST /api/camera/stop")
    print(f"   Camera Frame: GET /api/camera/frame")
    
    print(f"\n Checking dependencies...")
    try:
        import insightface
        print("  InsightFace available")
    except ImportError:
        print("  InsightFace not installed - pip install insightface")

    try:
        from sklearn.metrics.pairwise import cosine_similarity
        print("scikit-learn available")
    except ImportError:
        print("scikit-learn not installed - pip install scikit-learn")

    try:
        import cv2
        print("OpenCV available")
    except ImportError:
        print(" OpenCV not installed - pip install opencv-python")

    print("\n" + "="*80)
    print("Server starting... Press Ctrl+C to stop")
    print("="*80)

    template_path = os.path.join(TEMPLATES_DIR, 'face_server_index.html')
    if not os.path.exists(template_path):
        print(f"face_server_index.html not found at {template_path}")
    else:
        print(f"Template found at {template_path}")

    try:
        app.run(
            host='0.0.0.0',
            port=port,
            debug=False,
            threaded=True
        )
    except KeyboardInterrupt:
        print("\n\nShutting down face server...")
        cleanup_camera()
        print("Face server stopped and resources released.")