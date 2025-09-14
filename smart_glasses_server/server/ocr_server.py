# -*- coding: utf-8 -*-
from flask import Flask, request, jsonify, Response, render_template
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
from datetime import datetime, timedelta
import sqlite3
import io
from PIL import Image, ImageEnhance
import pyttsx3
import tensorflow as tf
import random
from collections import defaultdict
import pytesseract as pt
import platform

from flask_cors import CORS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  
ROOT_DIR = os.path.dirname(BASE_DIR)
app = Flask(
    __name__,
    template_folder=os.path.join(ROOT_DIR, "templates"),
    static_folder=os.path.join(ROOT_DIR, "static")
)
CORS(app)

logging.basicConfig(level=logging.INFO)

class SinhalaOCRServer:
    def __init__(self):
        self.keras_model_path = 'best_document_classifier_model.keras'
        self.document_classifier = None
        self.ocr_reader = None
        self.tts_engine = None
        self.processing_stats = {
            'total_documents': 0,
            'successful_ocr': 0,
            'errors': 0,
            'avg_processing_time': 0,
            'document_types': {},
            'processing_times': [],
            'document_identification_success': 0,  # New stat for document ID success rate
            'quality_scores': [],  # Track quality scores
            'hourly_distribution': defaultdict(int),  # Track hourly activity
        }
        self.class_names = ['exam', 'form', 'newspaper', 'note', 'story', 'word']  # Update with your actual class names
        self.image_size = (224, 224)  # Update if you used a different size
        
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
        self.stop_capture = False
        self.frame_capture_thread = None
        self.camera_error = None

        self.language_configs = [
            'sin',  
            'eng',  
        ]
        self.tesseract_available = False

        self.camera_settings = {
            'width': 640,
            'height': 480,
            'fps': 25,
            'brightness': 0.0,
            'contrast': 1.0,
            'saturation': 1.0
        }

        self.setup_database()
        self.setup_tesseract()
        self.init_models()
    
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

        
    def setup_database(self):
        """Setup SQLite database for storing OCR results"""
        try:
            self.conn = sqlite3.connect('ocr_results.db', check_same_thread=False)
            self.db_lock = threading.Lock()
            
            cursor = self.conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ocr_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    document_type TEXT,
                    confidence REAL,
                    extracted_text TEXT,
                    processing_time REAL,
                    image_quality REAL,
                    file_size INTEGER,
                    classification_confidence REAL,
                    ocr_success BOOLEAN DEFAULT 1,
                    identification_success BOOLEAN DEFAULT 1
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS processing_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    action TEXT NOT NULL,
                    status TEXT NOT NULL,
                    details TEXT,
                    processing_time REAL,
                    document_type TEXT,
                    quality_score REAL,
                    success BOOLEAN DEFAULT 1
                )
            ''')
            
            # Add new columns if they don't exist
            try:
                cursor.execute('ALTER TABLE ocr_results ADD COLUMN classification_confidence REAL')
                cursor.execute('ALTER TABLE ocr_results ADD COLUMN ocr_success BOOLEAN DEFAULT 1')
                cursor.execute('ALTER TABLE ocr_results ADD COLUMN identification_success BOOLEAN DEFAULT 1')
            except sqlite3.OperationalError:
                pass  # Columns already exist
                
            try:
                cursor.execute('ALTER TABLE processing_logs ADD COLUMN document_type TEXT')
                cursor.execute('ALTER TABLE processing_logs ADD COLUMN quality_score REAL')
                cursor.execute('ALTER TABLE processing_logs ADD COLUMN success BOOLEAN DEFAULT 1')
            except sqlite3.OperationalError:
                pass  # Columns already exist
            
            self.conn.commit()
            print("Database initialized successfully")
            
        except Exception as e:
            print(f"Database setup error: {e}")
            self.conn = None

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
                        target=self._continuous_capture,
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
                            target=self._continuous_capture,
                            daemon=True
                        )

                        self.frame_capture_thread.start()
                        time.sleep(0.5)

                        logging.info("USB camera started successfully as fallback")
                        return True
            
                self.camera_error = "No working cameras found"
                logging.error(self.camera_error)
                return False
        
        except Exception as e:
            logging.error(f"Camera initialization error: {e}")
            self.camera_error = f"Camera initialization failed: {str(e)}"
            return False
        
    def _continuous_capture(self):
        """Continuously capture frames in background thread"""
        try:
            while not self.stop_capture and self.camera_active:
                frame = None
                
                if self.camera_mode == 'rpi' and self.picamera2:
                    try:
                        frame = self.picamera2.capture_array()
                        if frame is not None:
                            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                    except Exception as e:
                        logging.error(f"RPi capture error: {e}")
                        break
                        
                elif self.camera_mode == 'usb' and self.camera and self.camera.isOpened():
                    try:
                        ret, frame = self.camera.read()
                        if not ret or frame is None:
                            logging.warning("USB camera read failed")
                            break
                    except Exception as e:
                        logging.error(f"USB capture error: {e}")
                        break
                
                if frame is not None:
                    with self.camera_lock:
                        self.last_frame = frame.copy()
                
                time.sleep(0.05)  # ~20 FPS
                
        except Exception as e:
            logging.error(f"Continuous capture error: {e}")
            self.camera_error = f"Capture thread error: {str(e)}"
        finally:
            logging.info("Capture thread ended")

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


    def setup_tesseract(self):
        """Setup Tesseract OCR configuration"""
        try:
            # Auto-detect Tesseract path based on OS
            system = platform.system()
            
            if system == "Windows":
                possible_paths = [
                    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
                    r"C:\Users\%USERNAME%\AppData\Local\Tesseract-OCR\tesseract.exe"
                ]
                
                for path in possible_paths:
                    if os.path.exists(path):
                        pt.pytesseract.tesseract_cmd = path
                        break
                        
            elif system == "Linux":
                # Usually installed via package manager
                pt.pytesseract.tesseract_cmd = 'tesseract'
                
            elif system == "Darwin":  # macOS
                possible_paths = [
                    '/usr/local/bin/tesseract',
                    '/opt/homebrew/bin/tesseract'
                ]
                
                for path in possible_paths:
                    if os.path.exists(path):
                        pt.pytesseract.tesseract_cmd = path
                        break
            
            # Test Tesseract installation
            test_image = Image.new('RGB', (100, 50), color='white')
            pt.image_to_string(test_image, timeout=5)
            
            print("✅ Tesseract OCR configured successfully")
            self.tesseract_available = True
            
            # Check available languages
            try:
                langs = pt.get_languages()
                sinhala_available = 'sin' in langs
                print(f"Available Tesseract languages: {', '.join(langs[:10])}..." if len(langs) > 10 else f"Available languages: {', '.join(langs)}")
                print(f"Sinhala support: {'Available' if sinhala_available else 'Not installed'}")
                
                if not sinhala_available:
                    print("⚠️  Warning: Sinhala language pack not found. Install with:")
                    if system == "Windows":
                        print("   Download from: https://github.com/tesseract-ocr/tessdata")
                    elif system == "Linux":
                        print("   sudo apt-get install tesseract-ocr-sin")
                    elif system == "Darwin":
                        print("   brew install tesseract-lang")
                        
            except Exception as e:
                print(f"Could not check Tesseract languages: {e}")
                
        except Exception as e:
            print(f"❌ Tesseract setup error: {e}")
            print("Please ensure Tesseract is installed:")
            print("  Windows: https://github.com/UB-Mannheim/tesseract/wiki")
            print("  Linux: sudo apt-get install tesseract-ocr tesseract-ocr-sin")
            print("  macOS: brew install tesseract tesseract-lang")
            self.tesseract_available = False
    

    def extract_sinhala_text_tesseract(self, image):
        """Extract Sinhala and English text using Tesseract OCR"""
        if not self.tesseract_available:
            return "", [], 0.0
            
        try:
            # Convert OpenCV image to PIL Image
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb_image)
            
            print("Starting Tesseract OCR extraction...")
            
            best_text = ""
            best_confidence = 0.0
            best_data = None
            
            # Try different language configurations
            for lang_config in self.language_configs:
                try:
                    print(f"Trying language configuration: {lang_config}")
                    
                    # Extract text with confidence data
                    data = pt.image_to_data(
                        pil_image, 
                        lang=lang_config, 
                        timeout=15,
                        output_type=pt.Output.DICT
                    )
                    
                    # Filter out low confidence text
                    valid_confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
                    
                    if valid_confidences:
                        avg_confidence = sum(valid_confidences) / len(valid_confidences)
                        
                        # Extract text
                        text_parts = []
                        for i in range(len(data['text'])):
                            if int(data['conf'][i]) > 30:  # Only include text with >30% confidence
                                text = data['text'][i].strip()
                                if text:
                                    text_parts.append(text)
                        
                        extracted_text = ' '.join(text_parts)
                        
                        print(f"Language {lang_config}: Found {len(text_parts)} text blocks with avg confidence {avg_confidence:.2f}%")
                        
                        # Use the result with highest confidence
                        if avg_confidence > best_confidence and extracted_text:
                            best_text = extracted_text
                            best_confidence = avg_confidence
                            best_data = data
                            
                except Exception as lang_error:
                    print(f"Error with language {lang_config}: {lang_error}")
                    continue
            
            # Process the best result
            text_boxes = []
            if best_data:
                for i in range(len(best_data['text'])):
                    if int(best_data['conf'][i]) > 30:
                        text = best_data['text'][i].strip()
                        if text:
                            # Create bounding box coordinates
                            x = best_data['left'][i]
                            y = best_data['top'][i]
                            w = best_data['width'][i]
                            h = best_data['height'][i]
                            
                            bbox = [
                                [x, y],
                                [x + w, y],
                                [x + w, y + h],
                                [x, y + h]
                            ]
                            
                            text_boxes.append({
                                'text': text,
                                'bbox': bbox,
                                'confidence': int(best_data['conf'][i]) / 100.0
                            })
                            
                            print(f"Tesseract text: '{text}' (confidence: {best_data['conf'][i]}%)")
            
            print(f"Tesseract extraction complete. Total confidence: {best_confidence:.2f}%")
            return best_text, text_boxes, best_confidence / 100.0
            
        except Exception as e:
            print(f"Tesseract OCR extraction error: {e}")
            import traceback
            traceback.print_exc()
            return "", [], 0.0
    

    def init_models(self):
        """Initialize Keras model and OCR reader"""
        try:
            # Initialize Keras model
            if os.path.exists(self.keras_model_path):
                print("Loading Keras model...")
                self.document_classifier = tf.keras.models.load_model(self.keras_model_path)
                print("✅ Keras model loaded successfully!")
                
                # Display model summary
                self.document_classifier.summary()
            else:
                print(f"Warning: Keras model not found at {self.keras_model_path}")
                
            # Initialize Text-to-Speech engine
            try:
                print("Initializing Text-to-Speech engine...")
                self.tts_engine = pyttsx3.init()
                self.tts_engine.setProperty('rate', 150)  # Speed of speech
                print("✅ TTS engine initialized successfully")
            except Exception as tts_error:
                print(f"⚠️  TTS initialization failed: {tts_error}")
                print("TTS functionality will be disabled")
                self.tts_engine = None
            
        except Exception as e:
            print(f"Model initialization error: {e}")
            
        except Exception as e:
            print(f"Model initialization error: {e}")
            
    def preprocess_image(self, image_array):
        """Preprocess image for the Keras model"""
        # Resize to match model input
        image = Image.fromarray(image_array).resize(self.image_size)
        
        # Convert to numpy array
        image_array = np.array(image, dtype=np.float32)
        
        # Normalize to 0-1
        image_array = image_array / 255.0
        
        # Add batch dimension
        image_array = np.expand_dims(image_array, axis=0)
        
        return image_array
            
    def classify_document(self, image):
        """Classify document type using Keras model"""
        if not self.document_classifier:
            return "Unknown", 0.0
            
        try:
            print(f"Image input shape: {image.shape}")
            
            # Convert BGR to RGB (OpenCV loads as BGR, model expects RGB)
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Preprocess image for model
            processed_image = self.preprocess_image(rgb_image)
            print(f"After preprocessing: {processed_image.shape}")
            
            # Run inference
            prediction = self.document_classifier.predict(processed_image)
            print(f"Raw output shape: {prediction.shape}")
            print(f"Raw output: {prediction}")
            
            # Get the predicted class
            predicted_class_idx = np.argmax(prediction[0])
            confidence = float(prediction[0][predicted_class_idx])
            predicted_class = self.class_names[predicted_class_idx] if predicted_class_idx < len(self.class_names) else "Unknown"
            
            print(f"Predicted class index: {predicted_class_idx}")
            print(f"Predicted class: {predicted_class}")
            print(f"Confidence: {confidence}")
            
            return predicted_class, confidence
            
        except Exception as e:
            print(f"Document classification error: {e}")
            import traceback
            traceback.print_exc()
            return "Unknown", 0.0
    
    def extract_sinhala_text_easyocr(self, image):
        """Extract Sinhala and English text using EasyOCR (fallback method)"""
        if not self.ocr_reader:
            return "", [], 0.0
            
        try:
            # Convert BGR to RGB for EasyOCR
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            print("Starting EasyOCR extraction (fallback)...")
            # Perform OCR
            results = self.ocr_reader.readtext(rgb_image)
            print(f"EasyOCR found {len(results)} text blocks")
            
            # Process results
            extracted_text = ""
            text_boxes = []
            total_confidence = 0.0
            
            for (bbox, text, confidence) in results:
                extracted_text += text + "\n"
                text_boxes.append({
                    'text': text,
                    'bbox': bbox,
                    'confidence': confidence
                })
                total_confidence += confidence
                print(f"EasyOCR text: '{text}' (confidence: {confidence:.2f})")
                
            avg_confidence = total_confidence / len(results) if results else 0.0
            
            return extracted_text.strip(), text_boxes, avg_confidence
            
        except Exception as e:
            print(f"EasyOCR extraction error: {e}")
            import traceback
            traceback.print_exc()
            return "", [], 0.0
        
    def extract_sinhala_text(self, image):
        """Extract Sinhala and English text using best available method"""
        print("Starting text extraction...")
        
        # Try Tesseract first (better for Sinhala)
        if self.tesseract_available:
            print("Using Tesseract OCR for text extraction...")
            tesseract_text, tesseract_boxes, tesseract_conf = self.extract_sinhala_text_tesseract(image)
            
            # If Tesseract found reasonable text, use it
            if tesseract_text and len(tesseract_text.strip()) > 5 and tesseract_conf > 0.3:
                print(f"Tesseract successful: {len(tesseract_text)} characters, confidence: {tesseract_conf:.2f}")
                return tesseract_text, tesseract_boxes, tesseract_conf
            else:
                print("Tesseract results insufficient, trying EasyOCR...")
        
        # Fallback to EasyOCR
        if self.ocr_reader:
            print("Using EasyOCR for text extraction...")
            easyocr_text, easyocr_boxes, easyocr_conf = self.extract_sinhala_text_easyocr(image)
            
            if easyocr_text:
                print(f"EasyOCR successful: {len(easyocr_text)} characters, confidence: {easyocr_conf:.2f}")
                return easyocr_text, easyocr_boxes, easyocr_conf
        
        print("Both OCR methods failed or unavailable")
        return "", [], 0.0
            
    
    def text_to_speech(self, text):
        """Convert text to speech"""
        if not self.tts_engine or not text.strip():
            return False
            
        try:
            # Clean text for TTS
            clean_text = text.replace('\n', '. ')
            
            # Speak the text
            self.tts_engine.say(clean_text)
            self.tts_engine.runAndWait()
            
            return True
            
        except Exception as e:
            print(f"TTS error: {e}")
            return False
    
    def calculate_image_quality(self, image):
        """Calculate basic image quality metrics"""
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            
            # Calculate Laplacian variance (focus measure)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
            
            # Calculate brightness
            brightness = np.mean(gray)
            
            # Calculate contrast (standard deviation)
            contrast = np.std(gray)
            
            # Normalize quality score (0-1)
            quality_score = min(1.0, (laplacian_var / 1000.0 + contrast / 128.0 + (1.0 - abs(brightness - 128) / 128.0)) / 3.0)
            
            return max(0.0, quality_score)
            
        except Exception as e:
            print(f"Quality calculation error: {e}")
            return 0.5
    
    def process_document(self, image_data):
        """Process document: classify, extract text, and analyze"""
        start_time = time.time()
        
        try:
            print("Starting document processing...")
            
            # Decode base64 image
            print("Decoding base64 image...")
            image_bytes = base64.b64decode(image_data)
            image_array = np.frombuffer(image_bytes, dtype=np.uint8)
            image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
            
            if image is None:
                raise ValueError("Invalid image data - could not decode image")
            
            print(f"Image decoded successfully. Shape: {image.shape}")
            
            # Calculate image quality
            quality_score = self.calculate_image_quality(image)
            print(f"Image quality score: {quality_score}")
            
            # Classify document type
            print("Classifying document...")
            document_type, classification_confidence = self.classify_document(image)
            print(f"Classification complete: {document_type} ({classification_confidence:.2f})")
            
            # Extract text
            print("Extracting text...")
            extracted_text, text_boxes, ocr_confidence = self.extract_sinhala_text(image)
            print(f"Text extraction complete. Found {len(text_boxes)} text blocks")
            
            processing_time = time.time() - start_time
            
            # Determine success rates
            ocr_success = len(extracted_text) > 0
            identification_success = document_type != "Unknown" and classification_confidence > 0.5
            
            # Update statistics
            self.update_stats(document_type, processing_time, ocr_success, identification_success, quality_score)
            
            # Store in database
            self.store_result(document_type, classification_confidence, extracted_text, 
                            processing_time, quality_score, len(image_bytes), ocr_confidence, 
                            ocr_success, identification_success)
            
            # Log the processing
            self.log_processing('process_document', 'success' if ocr_success else 'failed', 
                              f'Processed {document_type}', processing_time, document_type, 
                              quality_score, ocr_success)
            
            result = {
                'success': True,
                'document_type': document_type,
                'classification_confidence': classification_confidence,
                'extracted_text': extracted_text,
                'text_boxes': text_boxes,
                'ocr_confidence': ocr_confidence,
                'quality_score': quality_score,
                'processing_time': processing_time,
                'text_length': len(extracted_text),
                'num_text_blocks': len(text_boxes)
            }
            
            print(f"Processing complete in {processing_time:.2f}s")
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.processing_stats['errors'] += 1
            
            # Log the error
            self.log_processing('process_document', 'error', str(e), processing_time, 
                              'Unknown', 0.0, False)
            
            print(f"Processing error: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                'success': False,
                'error': str(e),
                'processing_time': processing_time
            }
    
    def update_stats(self, document_type, processing_time, ocr_success, identification_success, quality_score):
        """Update processing statistics"""
        self.processing_stats['total_documents'] += 1
        
        if ocr_success:
            self.processing_stats['successful_ocr'] += 1
            
        if identification_success:
            self.processing_stats['document_identification_success'] += 1
            
        if document_type in self.processing_stats['document_types']:
            self.processing_stats['document_types'][document_type] += 1
        else:
            self.processing_stats['document_types'][document_type] = 1
            
        self.processing_stats['processing_times'].append(processing_time)
        self.processing_stats['quality_scores'].append(quality_score)
        
        # Track hourly distribution
        current_hour = datetime.now().hour
        self.processing_stats['hourly_distribution'][current_hour] += 1
        
        # Keep only last 100 processing times for average calculation
        if len(self.processing_stats['processing_times']) > 100:
            self.processing_stats['processing_times'] = self.processing_stats['processing_times'][-100:]
            
        if len(self.processing_stats['quality_scores']) > 100:
            self.processing_stats['quality_scores'] = self.processing_stats['quality_scores'][-100:]
            
        self.processing_stats['avg_processing_time'] = sum(self.processing_stats['processing_times']) / len(self.processing_stats['processing_times'])
    
    def store_result(self, document_type, classification_confidence, extracted_text, processing_time, 
                    quality_score, file_size, ocr_confidence=0.0, ocr_success=True, identification_success=True):
        """Store OCR result in database"""
        if not self.conn:
            return
            
        try:
            with self.db_lock:
                cursor = self.conn.cursor()
                cursor.execute('''
                    INSERT INTO ocr_results 
                    (timestamp, document_type, confidence, extracted_text, processing_time, 
                     image_quality, file_size, classification_confidence, ocr_success, identification_success)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    datetime.now().isoformat(),
                    document_type,
                    ocr_confidence,
                    extracted_text,
                    processing_time,
                    quality_score,
                    file_size,
                    classification_confidence,
                    ocr_success,
                    identification_success
                ))
                self.conn.commit()
        except Exception as e:
            print(f"Database storage error: {e}")
    
    def log_processing(self, action, status, details, processing_time, document_type='', quality_score=0.0, success=True):
        """Log processing activity"""
        if not self.conn:
            return
            
        try:
            with self.db_lock:
                cursor = self.conn.cursor()
                cursor.execute('''
                    INSERT INTO processing_logs 
                    (timestamp, action, status, details, processing_time, document_type, quality_score, success)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    datetime.now().isoformat(),
                    action,
                    status,
                    details,
                    processing_time,
                    document_type,
                    quality_score,
                    success
                ))
                self.conn.commit()
        except Exception as e:
            print(f"Logging error: {e}")
    
    def get_recent_results(self, limit=10):
        """Get recent OCR results"""
        if not self.conn:
            return []
            
        try:
            with self.db_lock:
                cursor = self.conn.cursor()
                cursor.execute('''
                    SELECT * FROM ocr_results 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                ''', (limit,))
                
                results = cursor.fetchall()
                
                return [{
                    'id': row[0],
                    'timestamp': row[1],
                    'document_type': row[2],
                    'confidence': row[3],
                    'extracted_text': row[4],
                    'processing_time': row[5],
                    'image_quality': row[6],
                    'file_size': row[7],
                    'classification_confidence': row[8] if len(row) > 8 else 0.0,
                    'ocr_success': row[9] if len(row) > 9 else True,
                    'identification_success': row[10] if len(row) > 10 else True
                } for row in results]
                
        except Exception as e:
            print(f"Database query error: {e}")
            return []
    
    def get_daily_report(self, date_str):
        """Generate daily processing report"""
        if not self.conn:
            return {'error': 'Database not available'}
            
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            next_date = target_date + timedelta(days=1)
            
            with self.db_lock:
                cursor = self.conn.cursor()
                
                # Get daily statistics
                cursor.execute('''
                    SELECT 
                        COUNT(*) as total_documents,
                        SUM(CASE WHEN ocr_success = 1 THEN 1 ELSE 0 END) as successful_ocr,
                        SUM(CASE WHEN identification_success = 1 THEN 1 ELSE 0 END) as successful_identification,
                        AVG(confidence) as avg_confidence,
                        AVG(image_quality) as avg_quality,
                        AVG(processing_time) as avg_processing_time,
                        AVG(classification_confidence) as avg_classification_confidence
                    FROM ocr_results 
                    WHERE date(timestamp) = ?
                ''', (target_date,))
                
                stats = cursor.fetchone()
                
                # Get document type distribution
                cursor.execute('''
                    SELECT document_type, COUNT(*) as count
                    FROM ocr_results 
                    WHERE date(timestamp) = ?
                    GROUP BY document_type
                    ORDER BY count DESC
                ''', (target_date,))
                
                doc_types = {row[0]: row[1] for row in cursor.fetchall()}
                
                # Get hourly distribution
                cursor.execute('''
                    SELECT 
                        strftime('%H', timestamp) as hour,
                        COUNT(*) as count
                    FROM ocr_results 
                    WHERE date(timestamp) = ?
                    GROUP BY strftime('%H', timestamp)
                ''', (target_date,))
                
                hourly_dist = {int(row[0]): row[1] for row in cursor.fetchall()}
                
                # Generate insights
                insights = self.generate_daily_insights(stats, doc_types, hourly_dist)
                
                return {
                    'date': date_str,
                    'summary': {
                        'total_documents': stats[0] or 0,
                        'successful_ocr': stats[1] or 0,
                        'successful_identification': stats[2] or 0,
                        'avg_confidence': stats[3] or 0,
                        'avg_quality': stats[4] or 0,
                        'avg_processing_time': stats[5] or 0,
                        'avg_classification_confidence': stats[6] or 0,
                        'ocr_success_rate': (stats[1] / stats[0]) if stats[0] > 0 else 0,
                        'identification_success_rate': (stats[2] / stats[0]) if stats[0] > 0 else 0
                    },
                    'document_types': doc_types,
                    'hourly_distribution': hourly_dist,
                    'insights': insights
                }
                
        except Exception as e:
            print(f"Daily report error: {e}")
            return {'error': str(e)}
    
    def generate_daily_insights(self, stats, doc_types, hourly_dist):
        """Generate insights for daily report"""
        insights = []
        
        total_docs = stats[0] or 0
        successful_ocr = stats[1] or 0
        successful_id = stats[2] or 0
        
        if total_docs > 0:
            ocr_rate = (successful_ocr / total_docs) * 100
            id_rate = (successful_id / total_docs) * 100
            
            insights.append(f"Processed {total_docs} documents with {ocr_rate:.1f}% OCR success rate")
            insights.append(f"Document identification accuracy reached {id_rate:.1f}%")
            
            if stats[4]:  # avg_quality
                insights.append(f"Average image quality was {stats[4]*100:.1f}%")
            
            if stats[5]:  # avg_processing_time
                insights.append(f"Average processing time: {stats[5]*1000:.0f}ms per document")
            
            # Most common document type
            if doc_types:
                most_common = max(doc_types, key=doc_types.get)
                insights.append(f"Most processed document type: '{most_common}' ({doc_types[most_common]} documents)")
            
            # Peak hour
            if hourly_dist:
                peak_hour = max(hourly_dist, key=hourly_dist.get)
                insights.append(f"Peak processing hour: {peak_hour}:00 with {hourly_dist[peak_hour]} documents")
        else:
            insights.append("No documents were processed on this date")
        
        return insights
    
    def get_processing_logs(self, date_str, limit=50):
        """Get processing logs for a specific date"""
        if not self.conn:
            return {'error': 'Database not available'}
            
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            
            with self.db_lock:
                cursor = self.conn.cursor()
                cursor.execute('''
                    SELECT timestamp, action, status, details, processing_time, 
                           document_type, quality_score, success
                    FROM processing_logs 
                    WHERE date(timestamp) = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (target_date, limit))
                
                logs = [{
                    'timestamp': row[0],
                    'action': row[1],
                    'status': row[2],
                    'details': row[3],
                    'processing_time': row[4],
                    'document_type': row[5] if len(row) > 5 else '',
                    'quality_score': row[6] if len(row) > 6 else 0.0,
                    'success': row[7] if len(row) > 7 else True
                } for row in cursor.fetchall()]
                
                return {
                    'date': date_str,
                    'logs': logs,
                    'total_logs': len(logs)
                }
                
        except Exception as e:
            print(f"Processing logs error: {e}")
            return {'error': str(e)}
    
    def get_historical_data(self, days=7):
        """Get historical processing data"""
        if not self.conn:
            return {'error': 'Database not available'}
            
        try:
            with self.db_lock:
                cursor = self.conn.cursor()
                cursor.execute('''
                    SELECT 
                        date(timestamp) as date,
                        COUNT(*) as total_documents,
                        SUM(CASE WHEN ocr_success = 1 THEN 1 ELSE 0 END) as successful_ocr,
                        SUM(CASE WHEN identification_success = 1 THEN 1 ELSE 0 END) as successful_identification,
                        AVG(confidence) as avg_confidence,
                        AVG(image_quality) as avg_quality,
                        AVG(processing_time) as avg_processing_time
                    FROM ocr_results 
                    WHERE date(timestamp) >= date('now', '-{} days')
                    GROUP BY date(timestamp)
                    ORDER BY date DESC
                    LIMIT ?
                '''.format(days), (days,))
                
                data = [{
                    'date': row[0],
                    'total_documents': row[1],
                    'successful_ocr': row[2],
                    'successful_identification': row[3],
                    'avg_confidence': row[4] or 0,
                    'avg_quality': row[5] or 0,
                    'avg_processing_time': row[6] or 0,
                    'ocr_success_rate': (row[2] / row[1]) if row[1] > 0 else 0,
                    'identification_success_rate': (row[3] / row[1]) if row[1] > 0 else 0
                } for row in cursor.fetchall()]
                
                return {
                    'days': data,
                    'total_days': len(data)
                }
                
        except Exception as e:
            print(f"Historical data error: {e}")
            return {'error': str(e)}
    
    def generate_test_data(self):
        """Generate sample test data for demonstration"""
        try:
            current_time = datetime.now()
            sample_types = ['exam', 'form', 'newspaper', 'note', 'story']
            sample_texts = [
                "මෙය පරීක්ෂණ ලේඛනයකි", 
                "අයදුම්පත්රය සම්පූර්ණ කරන්න",
                "අද දින පුවත්පත", 
                "සටහන් ලිපිය",
                "කතන්දර කථාව"
            ]
            
            # Generate 10 sample records for today
            for i in range(10):
                doc_type = random.choice(sample_types)
                sample_text = random.choice(sample_texts)
                processing_time = random.uniform(1.0, 3.5)
                quality_score = random.uniform(0.6, 0.95)
                classification_conf = random.uniform(0.7, 0.98)
                ocr_conf = random.uniform(0.75, 0.95)
                
                # Vary the timestamp within the day
                timestamp = current_time - timedelta(hours=random.randint(0, 23), 
                                                   minutes=random.randint(0, 59))
                
                with self.db_lock:
                    cursor = self.conn.cursor()
                    cursor.execute('''
                        INSERT INTO ocr_results 
                        (timestamp, document_type, confidence, extracted_text, processing_time, 
                         image_quality, file_size, classification_confidence, ocr_success, identification_success)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        timestamp.isoformat(),
                        doc_type,
                        ocr_conf,
                        sample_text,
                        processing_time,
                        quality_score,
                        random.randint(50000, 500000),  # file size
                        classification_conf,
                        True,
                        True
                    ))
                    
                    # Also add to processing logs
                    cursor.execute('''
                        INSERT INTO processing_logs 
                        (timestamp, action, status, details, processing_time, document_type, quality_score, success)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        timestamp.isoformat(),
                        'process_document',
                        'success',
                        f'Processed {doc_type} document',
                        processing_time,
                        doc_type,
                        quality_score,
                        True
                    ))
                    
                    self.conn.commit()
            
            return True
            
        except Exception as e:
            print(f"Test data generation error: {e}")
            return False

# Initialize OCR server
ocr_server = SinhalaOCRServer()

@app.route('/')
def index():
    """Serve the main OCR interface"""
    return render_template('ocr_server_index.html')

@app.route('/api/ocr/health', methods=['GET'])
def ocr_health():
    """Check OCR server health"""
    return jsonify({
        'status': 'healthy',
        'model_loaded': ocr_server.document_classifier is not None,
        'easyocr_ready': ocr_server.ocr_reader is not None,
        'tesseract_ready': ocr_server.tesseract_available,
        'tts_ready': ocr_server.tts_engine is not None,
        'database_ready': ocr_server.conn is not None,
        'stats': ocr_server.processing_stats
    })

@app.route('/api/camera/start', methods=['POST'])
def start_camera():
    """Start camera endpoint"""
    try:
        success = ocr_server.start_camera()
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
        success = ocr_server.stop_camera()
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
        
        if not ocr_server.camera_active:
            logging.warning("Camera not active")
            return jsonify({
                'error': 'Camera not active',
                'image': '',
                'recognized': False,
                'message': 'Camera not available',
                'confidence': 0.0,
                'timestamp': datetime.now().isoformat()
            }), 500
        
        if ocr_server.camera_error:
            logging.error(f"Camera error: {ocr_server.camera_error}")
            return jsonify({
                'error': ocr_server.camera_error,
                'image': '',
                'recognized': False,
                'message': 'Camera error',
                'confidence': 0.0,
                'timestamp': datetime.now().isoformat()
            }), 500
        
        frame = ocr_server.capture_frame()
        if frame is None:
            logging.info("Attempting to restart camera...")
            if ocr_server.start_camera():
                frame = ocr_server.capture_frame()
                
            if frame is None:
                return jsonify({
                    'error': 'Failed to capture frame',
                    'image': '',
                    'recognized': False,
                    'message': 'Frame capture failed',
                    'confidence': 0.0,
                    'timestamp': datetime.now().isoformat()
                }), 500

        processed_frame = ocr_server.preprocess_camera_frame(frame)
        recognition_result = ocr_server.recognize_face_with_averaging(processed_frame)
        
        
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
            frame_base64 = ocr_server.frame_to_base64_quality(frame, image_quality)
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


@app.route('/api/ocr/process', methods=['POST'])
def process_document():
    """Process uploaded document"""
    try:
        data = request.json
        
        if not data or 'image' not in data:
            return jsonify({
                'success': False,
                'error': 'No image data provided'
            }), 400
        
        # Process the document
        result = ocr_server.process_document(data['image'])
        
        return jsonify(result)
        
    except Exception as e:
        print(f"API process error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/ocr/speak', methods=['POST'])
def speak_text():
    """Convert text to speech"""
    try:
        data = request.json
        
        if not data or 'text' not in data:
            return jsonify({
                'success': False,
                'error': 'No text provided'
            }), 400
        
        success = ocr_server.text_to_speech(data['text'])
        
        return jsonify({
            'success': success,
            'message': 'Text spoken successfully' if success else 'Failed to speak text'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/ocr/results', methods=['GET'])
def get_results():
    """Get recent OCR results"""
    try:
        limit = int(request.args.get('limit', 10))
        results = ocr_server.get_recent_results(limit)
        
        return jsonify({
            'success': True,
            'results': results
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/ocr/stats', methods=['GET'])
def get_stats():
    """Get OCR processing statistics"""
    try:
        stats = ocr_server.processing_stats.copy()
        
        # Calculate additional metrics
        total_docs = stats['total_documents']
        if total_docs > 0:
            stats['ocr_success_rate'] = (stats['successful_ocr'] / total_docs) * 100
            stats['identification_success_rate'] = (stats['document_identification_success'] / total_docs) * 100
            stats['error_rate'] = (stats['errors'] / total_docs) * 100
            
            # Calculate average quality if available
            if stats['quality_scores']:
                stats['avg_quality'] = sum(stats['quality_scores']) / len(stats['quality_scores'])
            else:
                stats['avg_quality'] = 0.0
        else:
            stats['ocr_success_rate'] = 0
            stats['identification_success_rate'] = 0
            stats['error_rate'] = 0
            stats['avg_quality'] = 0.0
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/ocr/daily_report', methods=['GET'])
def get_daily_report():
    """Get daily processing report"""
    try:
        date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
        report = ocr_server.get_daily_report(date_str)
        
        return jsonify(report)
        
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500

@app.route('/api/ocr/processing_logs', methods=['GET'])
def get_processing_logs():
    """Get processing logs for a specific date"""
    try:
        date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
        limit = int(request.args.get('limit', 50))
        
        logs = ocr_server.get_processing_logs(date_str, limit)
        
        return jsonify(logs)
        
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500

@app.route('/api/ocr/historical_data', methods=['GET'])
def get_historical_data():
    """Get historical processing data"""
    try:
        days = int(request.args.get('days', 7))
        data = ocr_server.get_historical_data(days)
        
        return jsonify(data)
        
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500

@app.route('/api/ocr/generate_test_data', methods=['POST'])
def generate_test_data():
    """Generate sample test data for demonstration"""
    try:
        success = ocr_server.generate_test_data()
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Test data generated successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to generate test data'
            }), 500
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/ocr/enhanced_stats', methods=['GET'])
def get_enhanced_stats():
    """Get enhanced analytics with additional metrics"""
    try:
        if not ocr_server.conn:
            return jsonify({'error': 'Database not available'}), 500
            
        with ocr_server.db_lock:
            cursor = ocr_server.conn.cursor()
            
            # Get comprehensive statistics
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_documents,
                    SUM(CASE WHEN ocr_success = 1 THEN 1 ELSE 0 END) as successful_ocr,
                    SUM(CASE WHEN identification_success = 1 THEN 1 ELSE 0 END) as successful_identification,
                    AVG(confidence) as avg_ocr_confidence,
                    AVG(classification_confidence) as avg_classification_confidence,
                    AVG(image_quality) as avg_quality,
                    AVG(processing_time) as avg_processing_time,
                    MIN(processing_time) as min_processing_time,
                    MAX(processing_time) as max_processing_time
                FROM ocr_results
            ''')
            
            stats = cursor.fetchone()
            
            # Get document type distribution
            cursor.execute('''
                SELECT document_type, COUNT(*) as count
                FROM ocr_results
                GROUP BY document_type
                ORDER BY count DESC
            ''')
            
            doc_types = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Get quality distribution
            cursor.execute('''
                SELECT 
                    CASE 
                        WHEN image_quality >= 0.9 THEN 'excellent'
                        WHEN image_quality >= 0.8 THEN 'good'
                        WHEN image_quality >= 0.6 THEN 'fair'
                        ELSE 'poor'
                    END as quality_range,
                    COUNT(*) as count
                FROM ocr_results
                GROUP BY quality_range
            ''')
            
            quality_dist = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Get hourly distribution for today
            cursor.execute('''
                SELECT 
                    strftime('%H', timestamp) as hour,
                    COUNT(*) as count
                FROM ocr_results 
                WHERE date(timestamp) = date('now')
                GROUP BY strftime('%H', timestamp)
            ''')
            
            hourly_dist = {int(row[0]): row[1] for row in cursor.fetchall()}
            
            total_docs = stats[0] or 0
            result = {
                'total_documents': total_docs,
                'successful_ocr': stats[1] or 0,
                'successful_identification': stats[2] or 0,
                'avg_ocr_confidence': stats[3] or 0,
                'avg_classification_confidence': stats[4] or 0,
                'avg_quality': stats[5] or 0,
                'avg_processing_time': stats[6] or 0,
                'min_processing_time': stats[7] or 0,
                'max_processing_time': stats[8] or 0,
                'ocr_success_rate': (stats[1] / total_docs * 100) if total_docs > 0 else 0,
                'identification_success_rate': (stats[2] / total_docs * 100) if total_docs > 0 else 0,
                'document_types': doc_types,
                'quality_distribution': quality_dist,
                'hourly_distribution': hourly_dist
            }
            
            return jsonify({
                'success': True,
                'analytics': result
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
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

if __name__ == '__main__':
    print("="*60)
    print("SINHALA OCR SERVER WITH KERAS MODEL & ENHANCED REPORTING")
    print("="*60)
    
    # Check model availability
    model_available = os.path.exists(ocr_server.keras_model_path)
    print(f"Document Classifier: {'Available' if model_available else 'Not Found'}")
    print(f"EasyOCR Reader: {'Loaded' if ocr_server.ocr_reader else 'Failed'}")
    print(f"Tesseract OCR: {'Ready' if ocr_server.tesseract_available else 'Failed'}")
    print(f"TTS Engine: {'Ready' if ocr_server.tts_engine else 'Failed'}")
    print(f"Database: {'Connected' if ocr_server.conn else 'Failed'}")
    
    local_ip = get_local_ip()
    port = 5002
    
    print(f"\nServer Configuration:")
    print(f"   Server IP: {local_ip}")
    print(f"   Server Port: {port}")
    print(f"   Full URL: http://{local_ip}:{port}")
    
    print(f"\nAPI Endpoints:")
    print(f"   Web Interface: GET /")
    print(f"   Health Check: GET /api/ocr/health")
    print(f"   Process Document: POST /api/ocr/process")
    print(f"   Text to Speech: POST /api/ocr/speak")
    print(f"   Get Results: GET /api/ocr/results")
    print(f"   Get Statistics: GET /api/ocr/stats")
    print(f"   Enhanced Analytics: GET /api/ocr/enhanced_stats")
    print(f"   Daily Report: GET /api/ocr/daily_report?date=YYYY-MM-DD")
    print(f"   Processing Logs: GET /api/ocr/processing_logs?date=YYYY-MM-DD")
    print(f"   Historical Data: GET /api/ocr/historical_data?days=7")
    print(f"   Generate Test Data: POST /api/ocr/generate_test_data")
    
    print(f"\nDependencies:")
    dependencies = [
        ('TensorFlow', 'tensorflow'),
        ('EasyOCR', 'easyocr'),
        ('Text-to-Speech', 'pyttsx3'),
        ('OpenCV', 'cv2'),
        ('PIL', 'PIL')
    ]
    
    for name, module in dependencies:
        try:
            __import__(module)
            print(f"   {name}: Available")
        except ImportError:
            print(f"   {name}: Missing - install with pip install {module}")
    
    print(f"\nNew Features:")
    print(f"   ✓ Document identification success rate tracking")
    print(f"   ✓ Enhanced daily reports with insights")
    print(f"   ✓ Processing logs with detailed activity tracking")
    print(f"   ✓ Historical performance analysis")
    print(f"   ✓ Quality score analytics")
    print(f"   ✓ Hourly activity distribution")
    print(f"   ✓ Test data generation for demonstration")
    
    print("\n" + "="*60)
    print("Server starting... Press Ctrl+C to stop")
    print("="*60)

    if not os.path.exists('ocr_server_index.html'):
        print("ocr_server_index.html not found!")

    try:
        app.run(
            host='0.0.0.0',
            port=port,
            debug=False,
            threaded=True
        )
    except KeyboardInterrupt:
        print("\n\nShutting down OCR server...")
        if ocr_server.conn:
            ocr_server.conn.close()
        print("OCR server stopped.")