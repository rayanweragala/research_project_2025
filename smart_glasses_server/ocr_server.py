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
from PIL import Image, ImageEnhance
import easyocr
import pyttsx3
import tensorflow as tf

from flask_cors import CORS

app = Flask(__name__)
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
            'processing_times': []
        }
        self.class_names = ['exam', 'form', 'newspaper', 'note', 'story', 'word']  # Update with your actual class names
        self.image_size = (224, 224)  # Update if you used a different size
        
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
    
    def extract_sinhala_text(self, image):
        """Extract Sinhala and English text using EasyOCR"""
        if not self.ocr_reader:
            return "", [], 0.0
            
        try:
            # Convert BGR to RGB for EasyOCR
            rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            print("Starting OCR extraction...")
            # Perform OCR
            results = self.ocr_reader.readtext(rgb_image)
            print(f"OCR found {len(results)} text blocks")
            
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
                print(f"OCR text: '{text}' (confidence: {confidence:.2f})")
                
            avg_confidence = total_confidence / len(results) if results else 0.0
            
            return extracted_text.strip(), text_boxes, avg_confidence
            
        except Exception as e:
            print(f"OCR extraction error: {e}")
            import traceback
            traceback.print_exc()
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
            
            # Update statistics
            self.update_stats(document_type, processing_time, len(extracted_text) > 0)
            
            # Store in database
            self.store_result(document_type, classification_confidence, extracted_text, 
                            processing_time, quality_score, len(image_bytes))
            
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
            
            print(f"Processing error: {e}")
            import traceback
            traceback.print_exc()
            
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
    print("SINHALA OCR SERVER WITH KERAS MODEL")
    print("="*60)
    
    # Check model availability
    model_available = os.path.exists(ocr_server.keras_model_path)
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