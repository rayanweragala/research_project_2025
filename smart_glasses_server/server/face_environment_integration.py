"""
Integration layer between face recognition and environment analysis
Adds environment context to face recognition results
"""

import cv2
import numpy as np
import logging
import time
from datetime import datetime
from collections import defaultdict
import sqlite3
import json

from environment_analyzer import EnvironmentAnalyzer

logging.basicConfig(level=logging.INFO)


class EnhancedRecognitionResult:
    """
    Enhanced recognition result that includes both face and environment data
    """
    
    def __init__(self, face_server, enable_environment=True, enable_multi_person=True):
        self.face_server = face_server
        self.enable_environment = enable_environment
        self.enable_multi_person = enable_multi_person
        
        if self.enable_environment:
            self.env_analyzer = EnvironmentAnalyzer()
        else:
            self.env_analyzer = None
        
        self.init_enhanced_database()
        
        logging.info(f"Enhanced Recognition initialized - Environment: {enable_environment}, Multi-person: {enable_multi_person}")
    
    def init_enhanced_database(self):
        """Create enhanced database tables for environment and multi-person logging"""
        try:
            conn = sqlite3.connect(self.face_server.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS enhanced_recognition_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    people_detected INTEGER DEFAULT 1,
                    primary_person TEXT,
                    all_people TEXT,
                    scene_type TEXT,
                    scene_confidence REAL,
                    environment_description TEXT,
                    detected_objects TEXT,
                    object_count INTEGER,
                    confidence REAL,
                    quality_score REAL,
                    processing_time REAL
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS environment_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    scene_type TEXT,
                    scene_confidence REAL,
                    objects_detected TEXT,
                    object_count INTEGER,
                    analysis_duration REAL
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS multi_person_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    person_name TEXT,
                    position_in_frame TEXT,
                    confidence REAL,
                    face_size REAL,
                    quality_score REAL
                )
            ''')
            
            conn.commit()
            conn.close()
            logging.info("Enhanced database tables created successfully")
            
        except Exception as e:
            logging.error(f"Enhanced database initialization error: {e}")
    
    def recognize_multiple_faces(self, image):
        """
        Recognize all faces in the frame (not just the primary one)
        Returns list of recognition results
        """
        try:
            if not self.face_server.model_loaded:
                return []
            
            faces = self.face_server.model.get(image)
            
            if len(faces) == 0:
                return []
            
            results = []
            
            for idx, face in enumerate(faces):
                encoding = face.embedding
                bbox = face.bbox
                
                face_area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
                image_area = image.shape[0] * image.shape[1]
                size_ratio = face_area / image_area
                
                quality = min(1.0, size_ratio * 5)
                
                best_match = None
                best_confidence = 0.0
                
                for name, stored_data in self.face_server.face_encodings.items():
                    for data in stored_data:
                        stored_encoding = data['encoding']
                        
                        cosine_sim = np.dot(encoding, stored_encoding) / (
                            np.linalg.norm(encoding) * np.linalg.norm(stored_encoding)
                        )
                        
                        if cosine_sim > best_confidence:
                            best_confidence = cosine_sim
                            best_match = name
                
                center_x = (bbox[0] + bbox[2]) / 2
                center_y = (bbox[1] + bbox[3]) / 2
                
                if center_x < image.shape[1] / 3:
                    position = "left"
                elif center_x > 2 * image.shape[1] / 3:
                    position = "right"
                else:
                    position = "center"
                
                if center_y < image.shape[0] / 3:
                    position += "_top"
                elif center_y > 2 * image.shape[0] / 3:
                    position += "_bottom"
                else:
                    position += "_middle"
                
                results.append({
                    'name': best_match if best_confidence > 0.4 else None,
                    'confidence': float(best_confidence),
                    'recognized': best_confidence > 0.4,
                    'bbox': bbox.tolist(),
                    'position': position,
                    'quality': quality,
                    'face_index': idx
                })
            
            return results
            
        except Exception as e:
            logging.error(f"Multi-face recognition error: {e}")
            return []
    
    def recognize_with_environment(self, image, session_id=None):
        """
        Complete recognition with environment context
        Returns both face recognition and environment analysis
        """
        start_time = time.time()
        
        try:
            if session_id is None:
                session_id = f"session_{int(time.time() * 1000)}"
            
            result = {
                'session_id': session_id,
                'timestamp': datetime.now().isoformat(),
                'faces': [],
                'environment': None,
                'summary': '',
                'processing_time': 0.0
            }
            
            if self.enable_multi_person:
                face_results = self.recognize_multiple_faces(image)
            else:
                single_result = self.face_server.recognize_face_with_averaging(image)
                if single_result['recognized']:
                    face_results = [{
                        'name': single_result['name'],
                        'confidence': single_result['confidence'],
                        'recognized': True,
                        'quality': single_result.get('quality_score', 0.0),
                        'position': 'center_middle'
                    }]
                else:
                    face_results = []
            
            result['faces'] = face_results
            
            if self.enable_environment and self.env_analyzer:
                env_result = self.env_analyzer.analyze_environment(image)
                result['environment'] = env_result
            
            result['summary'] = self.generate_summary(face_results, result.get('environment'))
            
            result['processing_time'] = time.time() - start_time
            
            self.log_enhanced_recognition(result)
            
            return result
            
        except Exception as e:
            logging.error(f"Enhanced recognition error: {e}")
            return {
                'session_id': session_id,
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'faces': [],
                'environment': None,
                'summary': f"Error: {str(e)}",
                'processing_time': time.time() - start_time
            }
    
    def generate_summary(self, face_results, environment):
        """Generate human-readable summary of the detection"""
        summary_parts = []
        
        recognized_people = [f['name'] for f in face_results if f['recognized']]
        unknown_count = sum(1 for f in face_results if not f['recognized'])
        
        if recognized_people:
            if len(recognized_people) == 1:
                summary_parts.append(f"{recognized_people[0]} detected")
            else:
                summary_parts.append(f"{len(recognized_people)} people detected: {', '.join(recognized_people)}")
        
        if unknown_count > 0:
            summary_parts.append(f"{unknown_count} unknown {'person' if unknown_count == 1 else 'people'}")
        
        if environment and environment.get('scene'):
            scene_info = environment['scene']
            scene = scene_info['scene'].replace('_', ' ')
            summary_parts.append(f"in/near {scene}")
            
            if environment.get('object_summary', {}).get('primary_objects'):
                objects = environment['object_summary']['primary_objects'][:2]
                if objects:
                    summary_parts.append(f"with {', '.join(objects)} nearby")
        
        if not summary_parts:
            return "No detection"
        
        return "; ".join(summary_parts)
    
    def log_enhanced_recognition(self, result):
        """Log enhanced recognition result to database"""
        try:
            conn = sqlite3.connect(self.face_server.db_path)
            cursor = conn.cursor()
            
            people_detected = len(result['faces'])
            recognized_people = [f['name'] for f in result['faces'] if f['recognized']]
            primary_person = recognized_people[0] if recognized_people else None
            all_people_json = json.dumps([f['name'] for f in result['faces']])
            
            env = result.get('environment', {})
            scene_type = env.get('scene', {}).get('scene', 'unknown')
            scene_confidence = env.get('scene', {}).get('confidence', 0.0)
            env_description = env.get('environment_description', '')
            objects_json = json.dumps([obj['class'] for obj in env.get('objects', [])])
            object_count = len(env.get('objects', []))
            
            avg_confidence = sum(f['confidence'] for f in result['faces']) / len(result['faces']) if result['faces'] else 0.0
            avg_quality = sum(f.get('quality', 0) for f in result['faces']) / len(result['faces']) if result['faces'] else 0.0
            
            cursor.execute('''
                INSERT INTO enhanced_recognition_logs 
                (session_id, people_detected, primary_person, all_people, 
                 scene_type, scene_confidence, environment_description, 
                 detected_objects, object_count, confidence, quality_score, processing_time)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                result['session_id'], people_detected, primary_person, all_people_json,
                scene_type, scene_confidence, env_description,
                objects_json, object_count, avg_confidence, avg_quality, result['processing_time']
            ))
            
            for face in result['faces']:
                if face['recognized']:
                    cursor.execute('''
                        INSERT INTO multi_person_logs 
                        (session_id, person_name, position_in_frame, confidence, face_size, quality_score)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        result['session_id'], face['name'], face['position'],
                        face['confidence'], face.get('bbox', [0,0,100,100])[2] - face.get('bbox', [0,0,100,100])[0],
                        face.get('quality', 0.0)
                    ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logging.error(f"Enhanced logging error: {e}")
    
    def get_environment_statistics(self, days=7):
        """Get environment statistics for the last N days"""
        try:
            conn = sqlite3.connect(self.face_server.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT scene_type, COUNT(*) as count,
                       AVG(scene_confidence) as avg_confidence,
                       AVG(object_count) as avg_objects
                FROM enhanced_recognition_logs
                WHERE timestamp > datetime('now', '-' || ? || ' days')
                AND scene_type != 'unknown'
                GROUP BY scene_type
                ORDER BY count DESC
            ''', (days,))
            
            scene_stats = []
            for row in cursor.fetchall():
                scene_stats.append({
                    'scene': row[0],
                    'occurrences': row[1],
                    'avg_confidence': round(row[2], 3),
                    'avg_objects': round(row[3], 1)
                })
            
            cursor.execute('''
                SELECT detected_objects
                FROM enhanced_recognition_logs
                WHERE timestamp > datetime('now', '-' || ? || ' days')
                AND detected_objects != '[]'
            ''', (days,))
            
            all_objects = []
            for row in cursor.fetchall():
                try:
                    objects = json.loads(row[0])
                    all_objects.extend(objects)
                except:
                    pass
            
            from collections import Counter
            object_counts = Counter(all_objects)
            
            conn.close()
            
            return {
                'scenes': scene_stats,
                'most_common_objects': dict(object_counts.most_common(10)),
                'total_detections': sum(s['occurrences'] for s in scene_stats)
            }
            
        except Exception as e:
            logging.error(f"Environment statistics error: {e}")
            return {'scenes': [], 'most_common_objects': {}, 'total_detections': 0}
    
    def get_multi_person_statistics(self, days=7):
        """Get multi-person detection statistics"""
        try:
            conn = sqlite3.connect(self.face_server.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT session_id, COUNT(DISTINCT person_name) as people_count
                FROM multi_person_logs
                WHERE timestamp > datetime('now', '-' || ? || ' days')
                GROUP BY session_id
                HAVING people_count > 1
            ''', (days,))
            
            multi_person_sessions = cursor.fetchall()
            
            cursor.execute('''
                SELECT GROUP_CONCAT(person_name, ', ') as people_group, 
                       COUNT(*) as occurrences
                FROM (
                    SELECT session_id, person_name
                    FROM multi_person_logs
                    WHERE timestamp > datetime('now', '-' || ? || ' days')
                    GROUP BY session_id, person_name
                    ORDER BY session_id, person_name
                )
                GROUP BY session_id
                HAVING COUNT(*) > 1
            ''', (days,))
            
            combinations = []
            for row in cursor.fetchall():
                if row[0]:
                    combinations.append({
                        'people': row[0],
                        'occurrences': row[1]
                    })
            
            conn.close()
            
            return {
                'total_multi_person_sessions': len(multi_person_sessions),
                'common_combinations': sorted(combinations, key=lambda x: x['occurrences'], reverse=True)[:5]
            }
            
        except Exception as e:
            logging.error(f"Multi-person statistics error: {e}")
            return {'total_multi_person_sessions': 0, 'common_combinations': []}


def create_enhanced_endpoints(app, face_server, enhanced_recognition):
    """
    Add these endpoint definitions to your face_server.py
    """
    
    @app.route('/api/recognize_enhanced', methods=['POST'])
    def recognize_enhanced():
        """Enhanced recognition with environment context"""
        try:
            data = request.json
            
            if not data or 'image' not in data:
                return jsonify({'error': 'No image data provided'}), 400
            
            img_data = base64.b64decode(data['image'])
            nparr = np.frombuffer(img_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image is None:
                return jsonify({'error': 'Invalid image data'}), 400
            
            session_id = data.get('session_id', None)
            
            result = enhanced_recognition.recognize_with_environment(image, session_id)
            
            return jsonify(result)
            
        except Exception as e:
            logging.error(f"Enhanced recognition endpoint error: {e}")
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/environment/statistics', methods=['GET'])
    def get_environment_stats():
        """Get environment detection statistics"""
        try:
            days = int(request.args.get('days', 7))
            stats = enhanced_recognition.get_environment_statistics(days)
            return jsonify(stats)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/multi_person/statistics', methods=['GET'])
    def get_multi_person_stats():
        """Get multi-person detection statistics"""
        try:
            days = int(request.args.get('days', 7))
            stats = enhanced_recognition.get_multi_person_statistics(days)
            return jsonify(stats)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/enhanced_logs', methods=['GET'])
    def get_enhanced_logs():
        """Get enhanced recognition logs"""
        try:
            date_str = request.args.get('date')
            limit = int(request.args.get('limit', 50))
            
            conn = sqlite3.connect(face_server.db_path)
            cursor = conn.cursor()
            
            if date_str:
                cursor.execute('''
                    SELECT session_id, timestamp, people_detected, primary_person, 
                           all_people, scene_type, scene_confidence, 
                           environment_description, object_count, confidence, 
                           quality_score, processing_time
                    FROM enhanced_recognition_logs
                    WHERE DATE(timestamp) = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (date_str, limit))
            else:
                cursor.execute('''
                    SELECT session_id, timestamp, people_detected, primary_person, 
                           all_people, scene_type, scene_confidence, 
                           environment_description, object_count, confidence, 
                           quality_score, processing_time
                    FROM enhanced_recognition_logs
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (limit,))
            
            logs = []
            for row in cursor.fetchall():
                logs.append({
                    'session_id': row[0],
                    'timestamp': row[1],
                    'people_detected': row[2],
                    'primary_person': row[3],
                    'all_people': json.loads(row[4]) if row[4] else [],
                    'scene_type': row[5],
                    'scene_confidence': row[6],
                    'environment_description': row[7],
                    'object_count': row[8],
                    'confidence': row[9],
                    'quality_score': row[10],
                    'processing_time': row[11]
                })
            
            conn.close()
            
            return jsonify({
                'logs': logs,
                'total': len(logs)
            })
            
        except Exception as e:
            logging.error(f"Enhanced logs error: {e}")
            return jsonify({'error': str(e)}), 500


if __name__ == "__main__":
    print("Enhanced Recognition System Test")
   