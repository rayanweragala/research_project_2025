from flask import Flask, request, jsonify, render_template_string
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
        self.recognition_threshold = 0.6
        self.recognition_cache = {}
        self.cache_duration = 3.0 
        
        self.recognition_stats = {
            'total_requests': 0,
            'successful_recognitions': 0,
            'cache_hits': 0,
            'avg_processing_time': 0.0,
            'errors': 0
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
                    providers=['CPUExecutionProvider'] 
                )
                self.model.prepare(ctx_id=0, det_size=(640, 640))
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
            quality_score = min(1.0, size_ratio * 10)
            
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
                        for stored_encoding in stored_encodings:
                            similarity = cosine_similarity([encoding], [stored_encoding])[0][0]
                            
                            if similarity > best_similarity:
                                best_similarity = similarity
                                best_match = name
                                
                except ImportError:
                    logging.warning("sklearn not available, using basic similarity")
                    best_similarity = 0.0
            else:
                best_similarity = 0.0
            
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

WEB_INTERFACE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Smart Glasses Face Recognition</title>
    <style>
        body { font-family: Arial; margin: 20px; background: #f0f0f0; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; }
        .camera-section { display: flex; gap: 20px; margin-bottom: 20px; }
        .video-container { flex: 1; }
        .controls { flex: 1; }
        video { width: 100%; max-width: 640px; border: 2px solid #ddd; border-radius: 10px; }
        canvas { display: none; }
        .button { padding: 10px 20px; margin: 5px; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
        .start { background: #4CAF50; color: white; }
        .stop { background: #f44336; color: white; }
        .register { background: #2196F3; color: white; }
        .results { margin-top: 20px; padding: 15px; background: #f9f9f9; border-radius: 5px; }
        .recognition-result { margin: 10px 0; padding: 10px; border-radius: 5px; }
        .recognized { background: #d4edda; border: 1px solid #c3e6cb; }
        .unknown { background: #fff3cd; border: 1px solid #ffeaa7; }
        .error { background: #f8d7da; border: 1px solid #f5c6cb; }
        .stats { display: flex; gap: 20px; margin-top: 20px; }
        .stat-box { flex: 1; padding: 15px; background: #e9ecef; border-radius: 5px; text-align: center; }
        input[type="text"] { width: 100%; padding: 8px; margin: 5px 0; border: 1px solid #ddd; border-radius: 4px; }
        .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
        .status.error { background: #f8d7da; color: #721c24; }
        .status.warning { background: #fff3cd; color: #856404; }
        .status.success { background: #d4edda; color: #155724; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤓 Smart Glasses Face Recognition</h1>
        <p>Using laptop camera to simulate smart glasses feed</p>
        
        <div class="camera-section">
            <div class="video-container">
                <video id="video" autoplay muted></video>
                <canvas id="canvas"></canvas>
            </div>
            
            <div class="controls">
                <h3>Controls</h3>
                <button class="button start" onclick="startRecognition()">Start Recognition</button>
                <button class="button stop" onclick="stopRecognition()">Stop Recognition</button>
                
                <h3>Register New Person</h3>
                <input type="text" id="personName" placeholder="Enter person's name">
                <button class="button register" onclick="registerPerson()">Register Current Face</button>
                
                <h3>System Status</h3>
                <div id="status" class="status">Ready</div>
            </div>
        </div>
        
        <div class="stats">
            <div class="stat-box">
                <h4>Recognition Rate</h4>
                <div id="recognitionRate">0%</div>
            </div>
            <div class="stat-box">
                <h4>Avg Processing Time</h4>
                <div id="avgTime">0ms</div>
            </div>
            <div class="stat-box">
                <h4>Total Requests</h4>
                <div id="totalRequests">0</div>
            </div>
            <div class="stat-box">
                <h4>Error Rate</h4>
                <div id="errorRate">0%</div>
            </div>
        </div>
        
        <div class="results">
            <h3>Recognition Results</h3>
            <div id="results"></div>
        </div>
    </div>

    <script>
        let video = document.getElementById('video');
        let canvas = document.getElementById('canvas');
        let ctx = canvas.getContext('2d');
        let recognitionActive = false;
        let recognitionInterval;

        async function initCamera() {
            try {
                if (navigator.mediaDevices === undefined) {
                    navigator.mediaDevices = {};
                }

                if (navigator.mediaDevices.getUserMedia === undefined) {
                    navigator.mediaDevices.getUserMedia = function(constraints) {
                        const getUserMedia = navigator.webkitGetUserMedia || navigator.mozGetUserMedia;
                        if (!getUserMedia) {
                            throw new Error('getUserMedia not supported');
                        }
                        return new Promise((resolve, reject) => {
                            getUserMedia.call(navigator, constraints, resolve, reject);
                        });
                    }
                }

                const stream = await navigator.mediaDevices.getUserMedia({ video: true });
                video.srcObject = stream;
                video.onloadedmetadata = () => {
                    canvas.width = video.videoWidth;
                    canvas.height = video.videoHeight;
                };
            } catch (err) {
                console.error('Camera error:', err);
                document.getElementById('status').innerHTML = 
                    '❌ Camera error: ' + err.message + 
                    '<br>Try accessing via HTTPS://localhost:5000';
                document.getElementById('status').className = 'status error';
            }
        }

        initCamera();
        
        function startRecognition() {
            if (!recognitionActive) {
                recognitionActive = true;
                document.getElementById('status').innerHTML = '🔍 Recognition Active';
                document.getElementById('status').className = 'status success';
                recognitionInterval = setInterval(performRecognition, 2000); 
            }
        }

        function stopRecognition() {
            recognitionActive = false;
            document.getElementById('status').innerHTML = '⏸️ Recognition Stopped';
            document.getElementById('status').className = 'status warning';
            if (recognitionInterval) {
                clearInterval(recognitionInterval);
            }
        }

        function performRecognition() {
            if (!recognitionActive) return;
            
            ctx.drawImage(video, 0, 0);
            canvas.toBlob(blob => {
                let reader = new FileReader();
                reader.onload = () => {
                    let base64 = reader.result.split(',')[1];
                    
                    fetch('/api/recognize_realtime', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ image: base64 })
                    })
                    .then(response => {
                        if (!response.ok) {
                            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                        }
                        return response.json();
                    })
                    .then(data => displayResult(data))
                    .catch(err => {
                        console.error('Recognition error:', err);
                        displayResult({
                            recognized: false,
                            name: null,
                            confidence: 0,
                            message: `Error: ${err.message}`,
                            quality_score: 0,
                            processing_time: 0,
                            error: true
                        });
                    });
                };
                reader.readAsDataURL(blob);
            }, 'image/jpeg', 0.8);
        }

        function registerPerson() {
            let name = document.getElementById('personName').value.trim();
            if (!name) {
                alert('Please enter a name');
                return;
            }
            
            ctx.drawImage(video, 0, 0);
            canvas.toBlob(blob => {
                let reader = new FileReader();
                reader.onload = () => {
                    let base64 = reader.result.split(',')[1];
                    
                    fetch('/api/register', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ 
                            name: name, 
                            images: [base64] 
                        })
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            alert(`Successfully registered ${name}!`);
                            document.getElementById('personName').value = '';
                        } else {
                            alert(`Registration failed: ${data.message}`);
                        }
                    })
                    .catch(err => {
                        console.error('Registration error:', err);
                        alert(`Registration error: ${err.message}`);
                    });
                };
                reader.readAsDataURL(blob);
            }, 'image/jpeg', 0.8);
        }

        function displayResult(data) {
            let resultsDiv = document.getElementById('results');
            let resultClass = data.error ? 'error' : (data.recognized ? 'recognized' : 'unknown');
            
            let confidence = data.confidence || 0;
            let quality = data.quality_score || 0;
            let processingTime = data.processing_time || 0;
            
            let message = data.error ? 
                `❌ ${data.message}` :
                (data.recognized ? 
                    `✅ ${data.name} (${(confidence * 100).toFixed(1)}% confidence)` :
                    `❓ ${data.message} (${(confidence * 100).toFixed(1)}% similarity)`);
            
            let modelStatus = data.model_loaded ? '🟢' : '🔴';
            
            let resultHtml = `
                <div class="recognition-result ${resultClass}">
                    <strong>${new Date().toLocaleTimeString()}</strong>: ${message}
                    <br><small>Quality: ${(quality * 100).toFixed(1)}%, 
                    Processing: ${(processingTime * 1000).toFixed(0)}ms, 
                    Model: ${modelStatus}</small>
                </div>
            `;
            
            resultsDiv.innerHTML = resultHtml + resultsDiv.innerHTML;
          
            let results = resultsDiv.children;
            while (results.length > 10) {
                resultsDiv.removeChild(results[results.length - 1]);
            }
        }

        setInterval(() => {
            fetch('/api/health')
                .then(response => response.json())
                .then(data => {
                    if (data.recognition_stats) {
                        let stats = data.recognition_stats;
                        let rate = stats.total_requests > 0 ? 
                            (stats.successful_recognitions / stats.total_requests * 100).toFixed(1) : 0;
                        let errorRate = stats.total_requests > 0 ?
                            (stats.errors / stats.total_requests * 100).toFixed(1) : 0;
                        
                        document.getElementById('recognitionRate').textContent = rate + '%';
                        document.getElementById('avgTime').textContent = (stats.avg_processing_time * 1000).toFixed(0) + 'ms';
                        document.getElementById('totalRequests').textContent = stats.total_requests;
                        document.getElementById('errorRate').textContent = errorRate + '%';
                        
                        if (!recognitionActive) {
                            let statusEl = document.getElementById('status');
                            if (!data.model_loaded) {
                                statusEl.innerHTML = '⚠️ Model not loaded - basic detection only';
                                statusEl.className = 'status warning';
                            }
                        }
                    }
                })
                .catch(err => console.error('Stats error:', err));
        }, 3000);
    </script>
</body>
</html>
'''

@app.route('/')
def web_interface():
    """Web interface for testing"""
    return render_template_string(WEB_INTERFACE)

@app.route('/api/health', methods=['GET'])
def health_check():
    """Enhanced health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'model_loaded': face_server.model_loaded,
        'people_count': len(face_server.face_encodings),
        'camera_active': True,
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
    """start camera endpoint - since camera is already started in web interface, just return response"""
    try:
        return jsonify({
            'success': True,
            'message': 'Camera is already active',
            'camera_active': True,
            'timestamp': datetime.now().isoformat()
        })
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
            return jsonify({
                'error': 'Camera not active',
                'image': '',
                'recognized': False,
                'message': 'Camera not available',
                'confidence': 0.0,
                'timestamp': datetime.now().isoformat()
            }), 500
        
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
    
def cleanup_camera():
    """Cleanup camera resources"""
    if hasattr(face_server, 'camera') and face_server.camera:
        face_server.camera.release()
        logging.info("Camera resources cleaned up")

atexit.register(cleanup_camera)

if __name__ == '__main__':
    print("="*60)
    print("🧠 Enhanced Face Recognition Server - Debug Version")
    print("="*60)
    print("📊 Features:")
    print("  ✅ Enhanced error handling and logging")
    print("  ✅ Fallback face detection (OpenCV)")
    print("  ✅ Better debugging information")
    print("  ✅ Model loading status reporting")
    print("  ✅ Graceful degradation when InsightFace fails")
    print()
    print("🔗 API Endpoints:")
    print("  GET  /                       - Web interface")
    print("  GET  /api/test               - Test server status")
    print("  POST /api/recognize_realtime - For continuous recognition")
    print("  POST /api/recognize          - Original recognition")
    print("  POST /api/register           - Register new person")
    print("  GET  /api/health             - Server health + stats")
    print("  GET  /api/analytics          - Recognition analytics")
    print("  GET  /api/people             - List registered people")
    print("  DELETE /api/delete_person    - Delete person")
    print()
    print("🌐 Open http://localhost:5000 in your browser to test")
    print()
    
    print("📦 Checking dependencies...")
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
        
    print()
    print("💡 If InsightFace fails to load, the server will use OpenCV fallback")
    print("   (Face detection only - no recognition without InsightFace)")
    print("="*60)
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False,
        threaded=True
    )