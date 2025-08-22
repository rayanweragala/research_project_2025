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
import subprocess
from datetime import datetime
import sqlite3
import io
from PIL import Image
import easyocr
import pyttsx3
import tensorflow as tf

from flask_cors import CORS

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)

class SinhalaOCRServer:
    def __init__(self):
        self.tflite_model_path = 'document_classifier_model_int8.tflite'
        self.document_classifier = None
        self.ocr_reader = None
        self.tts_engine = None
        self.processing_stats = {
            'total_documents': 0,
            'successful_ocr': 0,
            'errors': 0,
            'avg_processing_time': 0,
            'document_types': {},
            'processing_times': []
        }
        self.setup_database()
        self.init_models()
        
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
                    file_size INTEGER
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS processing_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    action TEXT NOT NULL,
                    status TEXT NOT NULL,
                    details TEXT,
                    processing_time REAL
                )
            ''')
            
            self.conn.commit()
            print("Database initialized successfully")
            
        except Exception as e:
            print(f"Database setup error: {e}")
            self.conn = None
            
    def init_models(self):
        """Initialize TensorFlow Lite model and OCR reader"""
        try:
            # Initialize TensorFlow Lite model
            if os.path.exists(self.tflite_model_path):
                self.document_classifier = tf.lite.Interpreter(model_path=self.tflite_model_path)
                self.document_classifier.allocate_tensors()
                
                # Get input and output details
                self.input_details = self.document_classifier.get_input_details()
                self.output_details = self.document_classifier.get_output_details()
                
                print(f"TFLite model loaded: {self.tflite_model_path}")
                print(f"Input shape: {self.input_details[0]['shape']}")
                print(f"Output shape: {self.output_details[0]['shape']}")
            else:
                print(f"Warning: TFLite model not found at {self.tflite_model_path}")
                
            # Initialize EasyOCR with Sinhala and English support
            print("Initializing EasyOCR for Sinhala and English...")
            self.ocr_reader = easyocr.Reader(['si', 'en'], gpu=False)  # Set gpu=True if you have CUDA
            print("OCR reader initialized successfully")
            
            # Initialize Text-to-Speech engine
            self.tts_engine = pyttsx3.init()
            self.tts_engine.setProperty('rate', 150)  # Speed of speech
            print("TTS engine initialized successfully")
            
        except Exception as e:
            print(f"Model initialization error: {e}")
            
    def classify_document(self, image):
        """Classify document type using TFLite model"""
        if not self.document_classifier:
            return "Unknown", 0.0
            
        try:
            # Preprocess image for model
            input_shape = self.input_details[0]['shape']
            height, width = input_shape[1], input_shape[2]
            
            # Resize and preprocess for TFLite INT8 model
            processed_image = cv2.resize(image, (width, height))
            processed_image = (processed_image / 255.0 * 255).astype(np.int8)
            
            # Add batch dimension
            if len(input_shape) == 4:
                processed_image = np.expand_dims(processed_image, axis=0)
                
            # Run inference
            self.document_classifier.set_tensor(self.input_details[0]['index'], processed_image)
            self.document_classifier.invoke()
            
            # Get prediction
            output_data = self.document_classifier.get_tensor(self.output_details[0]['index'])
            
            # Apply softmax to convert logits to probabilities
            probabilities = tf.nn.softmax(output_data).numpy().flatten()
            
            # Define class labels based on your training
            class_labels = ["Exam paper", "Forms", "Newspaper", "Notes", "Stories", "Words"]
            
            predicted_class_idx = np.argmax(probabilities)
            confidence = float(probabilities[predicted_class_idx])
            predicted_class = class_labels[predicted_class_idx] if predicted_class_idx < len(class_labels) else "Unknown"
            
            return predicted_class, confidence
            
        except Exception as e:
            print(f"Document classification error: {e}")
            return "Unknown", 0.0
    
    def extract_sinhala_text(self, image):
        """Extract Sinhala and English text using EasyOCR"""
        if not self.ocr_reader:
            return "", [], 0.0
            
        try:
            # Convert BGR to RGB for EasyOCR
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Perform OCR
            results = self.ocr_reader.readtext(rgb_image)
            
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
                
            avg_confidence = total_confidence / len(results) if results else 0.0
            
            return extracted_text.strip(), text_boxes, avg_confidence
            
        except Exception as e:
            print(f"OCR extraction error: {e}")
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
            # Decode base64 image
            image_bytes = base64.b64decode(image_data)
            image_array = np.frombuffer(image_bytes, dtype=np.uint8)
            image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
            
            if image is None:
                raise ValueError("Invalid image data")
            
            # Calculate image quality
            quality_score = self.calculate_image_quality(image)
            
            # Classify document type
            document_type, classification_confidence = self.classify_document(image)
            
            # Extract text
            extracted_text, text_boxes, ocr_confidence = self.extract_sinhala_text(image)
            
            processing_time = time.time() - start_time
            
            # Update statistics
            self.update_stats(document_type, processing_time, len(extracted_text) > 0)
            
            # Store in database
            self.store_result(document_type, classification_confidence, extracted_text, 
                            processing_time, quality_score, len(image_bytes))
            
            return {
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
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.processing_stats['errors'] += 1
            
            return {
                'success': False,
                'error': str(e),
                'processing_time': processing_time
            }
    
    def update_stats(self, document_type, processing_time, success):
        """Update processing statistics"""
        self.processing_stats['total_documents'] += 1
        
        if success:
            self.processing_stats['successful_ocr'] += 1
            
        if document_type in self.processing_stats['document_types']:
            self.processing_stats['document_types'][document_type] += 1
        else:
            self.processing_stats['document_types'][document_type] = 1
            
        self.processing_stats['processing_times'].append(processing_time)
        
        # Keep only last 100 processing times for average calculation
        if len(self.processing_stats['processing_times']) > 100:
            self.processing_stats['processing_times'] = self.processing_stats['processing_times'][-100:]
            
        self.processing_stats['avg_processing_time'] = sum(self.processing_stats['processing_times']) / len(self.processing_stats['processing_times'])
    
    def store_result(self, document_type, confidence, extracted_text, processing_time, quality_score, file_size):
        """Store OCR result in database"""
        if not self.conn:
            return
            
        try:
            with self.db_lock:
                cursor = self.conn.cursor()
                cursor.execute('''
                    INSERT INTO ocr_results 
                    (timestamp, document_type, confidence, extracted_text, processing_time, image_quality, file_size)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    datetime.now().isoformat(),
                    document_type,
                    confidence,
                    extracted_text,
                    processing_time,
                    quality_score,
                    file_size
                ))
                self.conn.commit()
        except Exception as e:
            print(f"Database storage error: {e}")
    
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
                    'file_size': row[7]
                } for row in results]
                
        except Exception as e:
            print(f"Database query error: {e}")
            return []

# Initialize OCR server
ocr_server = SinhalaOCRServer()

@app.route('/')
def index():
    """Serve the main OCR interface"""
    return send_from_directory('.', 'ocr_server_index.html')

@app.route('/api/ocr/health', methods=['GET'])
def ocr_health():
    """Check OCR server health"""
    return jsonify({
        'status': 'healthy',
        'model_loaded': ocr_server.document_classifier is not None,
        'ocr_ready': ocr_server.ocr_reader is not None,
        'tts_ready': ocr_server.tts_engine is not None,
        'database_ready': ocr_server.conn is not None,
        'stats': ocr_server.processing_stats
    })

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
        return jsonify({
            'success': True,
            'stats': ocr_server.processing_stats
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
    print("SINHALA OCR SERVER")
    print("="*60)
    
    # Check model availability
    model_available = os.path.exists(ocr_server.tflite_model_path)
    print(f"Document Classifier: {'Available' if model_available else 'Not Found'}")
    print(f"OCR Reader: {'Loaded' if ocr_server.ocr_reader else 'Failed'}")
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
        print("\n\nShutting down OCR server...")
        if ocr_server.conn:
            ocr_server.conn.close()
        print("OCR server stopped.")