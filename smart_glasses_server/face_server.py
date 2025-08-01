from flask import Flask, request, jsonify
import cv2
import numpy as np
import base64
import json
import os
import sqlite3
from datetime import datetime
import insightface
from sklearn.metrics.pairwise import cosine_similarity
import threading
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

class FaceRecognitionServer:
    def __init__(self):
        self.model = insightface.app.FaceAnalysis(
            providers=['CPUExecutionProvider'] 
        )
        self.model.prepare(ctx_id=0, det_size=(640, 640))
 
        self.db_path = "face_database.db"
        self.init_database()
 
        self.face_encodings = {}
        self.load_face_database()
        
        self.recognition_threshold = 0.6  

    def init_database(self):
        """Initialize SQLite database for face storage"""
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
        
        conn.commit()
        conn.close()

    def load_face_database(self):
        """Load existing face encodings from database"""
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
        print(f"Loaded {len(self.face_encodings)} people from database")

    def extract_face_encoding(self, image):
        """Extract face encoding from image using InsightFace"""
        try:
            faces = self.model.get(image)
            if len(faces) == 0:
                return None, 0.0

            face = max(faces, key=lambda x: (x.bbox[2] - x.bbox[0]) * (x.bbox[3] - x.bbox[1]))
            
            face_area = (face.bbox[2] - face.bbox[0]) * (face.bbox[3] - face.bbox[1])
            image_area = image.shape[0] * image.shape[1]
            size_ratio = face_area / image_area
            
            quality_score = min(1.0, size_ratio * 10) 
            
            return face.embedding, quality_score
            
        except Exception as e:
            print(f"Error extracting face encoding: {e}")
            return None, 0.0

    def recognize_face(self, image):
        """Recognize face in image"""
        encoding, quality = self.extract_face_encoding(image)
        
        if encoding is None:
            return None, 0.0, "No face detected"
        
        if quality < 0.3:
            return None, quality, "Face quality too low"
        
        best_match = None
        best_similarity = 0.0
        
        for name, stored_encodings in self.face_encodings.items():
            for stored_encoding in stored_encodings:
                similarity = cosine_similarity([encoding], [stored_encoding])[0][0]
                
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = name
        
        if best_similarity > self.recognition_threshold:
            confidence = best_similarity
            return best_match, confidence, f"Recognized {best_match}"
        else:
            return None, best_similarity, "Unknown person"

    def add_person(self, name, images_base64):
        """Add new person with multiple images"""
        try:
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
                        continue

                    encoding, quality = self.extract_face_encoding(image)
                    
                    if encoding is not None and quality > 0.3:
                        encoding_blob = encoding.tobytes()
                        cursor.execute('''
                            INSERT INTO face_encodings (person_id, encoding, image_quality)
                            VALUES (?, ?, ?)
                        ''', (person_id, encoding_blob, quality))
                        
                        successful_encodings.append(encoding)
                        total_quality += quality
                        
                        print(f"Processed image {i+1} for {name}, quality: {quality:.2f}")
                    
                except Exception as e:
                    print(f"Error processing image {i+1} for {name}: {e}")
                    continue
            
            if successful_encodings:
                cursor.execute('''
                    UPDATE people SET photo_count = ? WHERE id = ?
                ''', (len(successful_encodings), person_id))

                self.face_encodings[name] = successful_encodings
                
                conn.commit()
                avg_quality = total_quality / len(successful_encodings)
                
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
            return {
                'success': False,
                'message': f'Database error: {str(e)}',
                'photos_processed': 0
            }
        finally:
            conn.close()

face_server = FaceRecognitionServer()

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'model_loaded': face_server.model is not None,
        'people_count': len(face_server.face_encodings)
    })

@app.route('/api/recognize', methods=['POST'])
def recognize_person():
    """Recognize person from uploaded image file"""
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

        name, confidence, message = face_server.recognize_face(image)

        return jsonify({
            'recognized': name is not None,
            'name': name,
            'confidence': float(confidence),
            'message': message,
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/register', methods=['POST'])
def register_person():
    """Register new person with multiple images"""
    try:
        data = request.json
        
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
        return jsonify({'error': str(e)}), 500

@app.route('/api/delete_person', methods=['DELETE'])
def delete_person():
    """Delete a person and their face data"""
    try:
        data = request.json
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
        
        return jsonify({
            'success': True,
            'message': f'Successfully deleted {name}'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("Starting InsightFace Recognition Server...")
    print("Install dependencies: pip install insightface flask opencv-python scikit-learn")
    print("Server will run on http://localhost:5000")
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        threaded=True
    )