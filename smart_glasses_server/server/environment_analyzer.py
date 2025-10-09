import cv2
import numpy as np
from collections import defaultdict, Counter
import json
import logging
from datetime import datetime
import time
import os

logging.basicConfig(level=logging.INFO)

class EnvironmentAnalyzer:
    """
    Enhanced environment analyzer with improved object detection
    """

    def __init__(self, confidence_threshold=0.15):  # VERY LOW threshold
        self.confidence_threshold = confidence_threshold
        self.model_loaded = False
        self.net = None
        self.classes = []

        # COCO classes that MobileNet SSD can detect
        self.coco_classes = [
            'background', 'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus',
            'train', 'truck', 'boat', 'traffic light', 'fire hydrant', 'stop sign',
            'parking meter', 'bench', 'bird', 'cat', 'dog', 'horse', 'sheep', 'cow',
            'elephant', 'bear', 'zebra', 'giraffe', 'backpack', 'umbrella', 'handbag',
            'tie', 'suitcase', 'frisbee', 'skis', 'snowboard', 'sports ball', 'kite',
            'baseball bat', 'baseball glove', 'skateboard', 'surfboard', 'tennis racket',
            'bottle', 'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl', 'banana',
            'apple', 'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog', 'pizza',
            'donut', 'cake', 'chair', 'couch', 'potted plant', 'bed', 'dining table',
            'toilet', 'tv', 'laptop', 'mouse', 'remote', 'keyboard', 'cell phone',
            'microwave', 'oven', 'toaster', 'sink', 'refrigerator', 'book', 'clock',
            'vase', 'scissors', 'teddy bear', 'hair drier', 'toothbrush'
        ]

        self.scene_rules = {
            'office': ['laptop', 'keyboard', 'mouse', 'chair', 'book', 'cell phone'],
            'study_area': ['book', 'laptop', 'chair', 'desk'],
            'living_room': ['chair', 'couch', 'tv', 'remote'],
            'kitchen': ['refrigerator', 'microwave', 'sink', 'oven', 'bottle', 'cup'],
            'bedroom': ['bed'],
            'indoor_room': ['chair', 'table'],
        }

        self.environment_cache = {
            'last_analysis': None,
            'timestamp': 0,
            'cache_duration': 1.5  # Faster cache expiry
        }

        self.analysis_stats = {
            'total_analyses': 0,
            'avg_processing_time': 0.0,
            'detected_scenes': defaultdict(int),
            'detected_objects': defaultdict(int)
        }
        
        self.init_model()

    def init_model(self):
        """Initialize MobileNet SSD model"""
        try:
            logging.info("Initializing MobileNet SSD for environment analysis...")
            
            model_paths = [
                ("/opt/research_project/models/frozen_inference_graph.pb",
                "/opt/research_project/models/ssd_mobilenet_v2_coco_2018_03_29.pbtxt"),
            ]
            
            model_loaded_successfully = False
            
            for model_file, config_file in model_paths:
                if os.path.exists(model_file) and os.path.exists(config_file):
                    try:
                        self.net = cv2.dnn.readNetFromTensorflow(model_file, config_file)
                        model_loaded_successfully = True
                        logging.info("✓ MobileNet SSD loaded successfully!")
                        break
                    except Exception as e:
                        logging.error(f"Failed to load: {e}")
                        continue
            
            if model_loaded_successfully:
                self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
                self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
                self.classes = self.coco_classes
                self.model_loaded = True
                logging.info(f"✓ Environment analyzer ready")
            else:
                logging.warning("MODEL FILES NOT FOUND - using fallback")
                self.model_loaded = False
            
        except Exception as e:
            logging.error(f"Model init error: {e}")
            self.model_loaded = False

    def detect_objects(self, frame):
        """Detect objects with VERY aggressive detection"""
        if frame is None or frame.size == 0:
            return self.fallback_object_detection(frame if frame is not None else np.zeros((480, 640, 3), dtype=np.uint8))
        
        detected_objects = []
        
        # Try model detection first
        if self.model_loaded and self.net is not None:
            try:
                start_time = time.time()
                height, width = frame.shape[:2]
                
                blob = cv2.dnn.blobFromImage(
                    cv2.resize(frame, (300, 300)),
                    0.007843,
                    (300, 300),
                    127.5
                )
                
                self.net.setInput(blob)
                detections = self.net.forward()
                
                for i in range(detections.shape[2]):
                    confidence = detections[0, 0, i, 2]
                    
                    if confidence > self.confidence_threshold: 
                        class_id = int(detections[0, 0, i, 1])
                        
                        if 0 < class_id < len(self.classes): 
                            box = detections[0, 0, i, 3:7] * np.array([width, height, width, height])
                            (x1, y1, x2, y2) = box.astype("int")
                            
                            x1 = max(0, min(x1, width))
                            y1 = max(0, min(y1, height))
                            x2 = max(0, min(x2, width))
                            y2 = max(0, min(y2, height))
                            
                            if x2 > x1 and y2 > y1:  
                                detected_objects.append({
                                    'class': self.classes[class_id],
                                    'confidence': float(confidence),
                                    'bbox': [int(x1), int(y1), int(x2), int(y2)],
                                    'class_id': class_id
                                })
                
                processing_time = time.time() - start_time
                self.update_stats(processing_time, detected_objects)
                
            except Exception as e:
                logging.error(f"Model detection error: {e}")
        
        fallback_objects = self.fallback_object_detection(frame)
        
        all_objects = detected_objects + fallback_objects
        
        unique_objects = {}
        for obj in all_objects:
            key = obj['class']
            if key not in unique_objects or obj['confidence'] > unique_objects[key]['confidence']:
                unique_objects[key] = obj
        
        final_objects = list(unique_objects.values())
        
        if len(final_objects) == 0:
            final_objects = [{
                'class': 'indoor_scene',
                'confidence': 0.4,
                'bbox': [0, 0, frame.shape[1] if frame is not None else 100, frame.shape[0] if frame is not None else 100],
                'class_id': -1
            }]
        
        return final_objects
    
    def fallback_object_detection(self, frame):
        """Enhanced fallback with color and texture analysis"""
        try:
            if frame is None or frame.size == 0:
                return []
            
            detected_objects = []
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            
            edges = cv2.Canny(gray, 20, 80)  
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            mean_brightness = np.mean(gray)
            
            for contour in contours[:30]:  
                area = cv2.contourArea(contour)
                if area < 300:  
                    continue
                
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / float(h) if h > 0 else 0
                
                roi = frame[y:y+h, x:x+w] if y+h <= frame.shape[0] and x+w <= frame.shape[1] else None
                
                if roi is not None and roi.size > 0:
                    avg_color = np.mean(roi, axis=(0, 1))
                    
                    if 0.4 < aspect_ratio < 0.7 and 1000 < area < 8000:
                        detected_objects.append({
                            'class': 'cell phone',
                            'confidence': 0.55,
                            'bbox': [x, y, x+w, y+h],
                            'class_id': 67
                        })
                    
                    elif 0.6 < aspect_ratio < 1.5 and area > 2000:
                        detected_objects.append({
                            'class': 'book',
                            'confidence': 0.5,
                            'bbox': [x, y, x+w, y+h],
                            'class_id': 73
                        })
                    
                    elif aspect_ratio > 1.3 and area > 5000:
                        detected_objects.append({
                            'class': 'laptop',
                            'confidence': 0.5,
                            'bbox': [x, y, x+w, y+h],
                            'class_id': 63
                        })
                    
                    elif 0.2 < aspect_ratio < 0.5 and 800 < area < 4000:
                        detected_objects.append({
                            'class': 'bottle',
                            'confidence': 0.45,
                            'bbox': [x, y, x+w, y+h],
                            'class_id': 39
                        })
                    
                    elif 0.7 < aspect_ratio < 1.3 and 500 < area < 3000:
                        detected_objects.append({
                            'class': 'cup',
                            'confidence': 0.45,
                            'bbox': [x, y, x+w, y+h],
                            'class_id': 41
                        })
                    
                    elif area > 1000:
                        detected_objects.append({
                            'class': 'object',
                            'confidence': 0.4,
                            'bbox': [x, y, x+w, y+h],
                            'class_id': -1
                        })
            
            if len(detected_objects) < 2:
                detected_objects.append({
                    'class': 'wall',
                    'confidence': 0.6,
                    'bbox': [0, 0, frame.shape[1]//2, frame.shape[0]//2],
                    'class_id': -1
                })
            
            return detected_objects[:15]  
            
        except Exception as e:
            logging.error(f"Fallback error: {e}")
            return []
    
    def infer_scene(self, detected_objects):
        """Infer scene from detected objects"""
        if not detected_objects:
            return {
                'scene': 'unknown',
                'confidence': 0.0,
                'reasoning': ['No objects detected'],
                'object_count': 0
            }
        
        object_names = [obj['class'] for obj in detected_objects]
        object_counter = Counter(object_names)
        
        scene_scores = {}
        
        for scene, keywords in self.scene_rules.items():
            score = 0
            matches = []
            
            for keyword in keywords:
                for obj_name in object_counter:
                    if keyword.lower() in obj_name.lower() or obj_name.lower() in keyword.lower():
                        score += object_counter[obj_name] * 15
                        matches.append(obj_name)
            
            if score > 0:
                scene_scores[scene] = {'score': score, 'matches': matches}
        
        if not scene_scores:
            return {
                'scene': 'indoor_room',
                'confidence': 0.4,
                'reasoning': object_names[:3],
                'object_count': len(detected_objects)
            }
        
        best_scene = max(scene_scores.items(), key=lambda x: x[1]['score'])
        max_possible_score = len(self.scene_rules[best_scene[0]]) * 15
        confidence = min(1.0, best_scene[1]['score'] / max_possible_score)
        
        return {
            'scene': best_scene[0],
            'confidence': float(confidence),
            'reasoning': best_scene[1]['matches'],
            'object_count': len(detected_objects)
        }
    
    def analyze_environment(self, frame, use_cache=True):
        """Complete environment analysis"""
        if frame is None or frame.size == 0:
            return {
                'timestamp': datetime.now().isoformat(),
                'scene': {'scene': 'unknown', 'confidence': 0.0, 'reasoning': [], 'object_count': 0},
                'objects': [],
                'object_summary': {'total_objects': 0, 'unique_objects': 0, 'object_counts': {}, 'primary_objects': []},
                'environment_description': 'No environment data'
            }
        
        if use_cache:
            current_time = time.time()
            if (self.environment_cache['last_analysis'] and 
                current_time - self.environment_cache['timestamp'] < self.environment_cache['cache_duration']):
                return self.environment_cache['last_analysis']
        
        detected_objects = self.detect_objects(frame)
        detected_objects = [obj for obj in detected_objects if obj['class'] != 'person']
        scene_info = self.infer_scene(detected_objects)
        
        result = {
            'timestamp': datetime.now().isoformat(),
            'scene': scene_info,
            'objects': detected_objects,
            'object_summary': self.summarize_objects(detected_objects),
            'environment_description': self.generate_description(scene_info, detected_objects)
        }
        
        if use_cache:
            self.environment_cache['last_analysis'] = result
            self.environment_cache['timestamp'] = time.time()
        
        return result
    
    def summarize_objects(self, detected_objects):
        """Create summary of detected objects"""
        object_counts = Counter([obj['class'] for obj in detected_objects])
        return {
            'total_objects': len(detected_objects),
            'unique_objects': len(object_counts),
            'object_counts': dict(object_counts),
            'primary_objects': [item[0] for item in object_counts.most_common(5)]
        }
    
    def generate_description(self, scene_info, detected_objects):
        """Generate human-readable description"""
        scene = scene_info.get('scene', 'unknown').replace('_', ' ').title()
        confidence = float(scene_info.get('confidence', 0.0))
        
        confidence_text = "likely" if confidence > 0.7 else "possibly" if confidence > 0.5 else "might be" if confidence > 0.3 else "appears to be"
        
        description = f"Environment {confidence_text} a {scene}"
        
        if detected_objects:
            object_names = [obj['class'] for obj in detected_objects[:3]]
            description += f". Detected: {', '.join(object_names)}"
            if len(detected_objects) > 3:
                description += f" and {len(detected_objects) - 3} more"
        
        return description
    
    def update_stats(self, processing_time, detected_objects):
        """Update statistics"""
        self.analysis_stats['total_analyses'] += 1
        current_avg = self.analysis_stats['avg_processing_time']
        count = self.analysis_stats['total_analyses']
        self.analysis_stats['avg_processing_time'] = ((current_avg * (count - 1) + processing_time) / count)
        
        for obj in detected_objects:
            self.analysis_stats['detected_objects'][obj['class']] += 1
    
    def get_stats(self):
        """Get statistics"""
        return {
            'total_analyses': self.analysis_stats['total_analyses'],
            'avg_processing_time': round(self.analysis_stats['avg_processing_time'], 3),
            'most_detected_objects': dict(sorted(self.analysis_stats['detected_objects'].items(), key=lambda x: x[1], reverse=True)[:10])
        }
