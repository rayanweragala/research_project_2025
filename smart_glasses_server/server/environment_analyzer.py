import cv2
import numpy as np
from collections import defaultdict, Counter
import json
import logging
from datetime import datetime
import threading
import time
import os

logging.basicConfig(level=logging.INFO)

class EnvironmentAnalyzer:
    """
    Environment analyzer using MobileNet SSD for object detection
    and simple scene classification
    """

    def __init__(self, confidence_threshold=0.4):
        self.confidence_threshold = confidence_threshold
        self.model_loaded = False
        self.net = None
        self.classes = []

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
            'indoor_room': ['wall', 'object', 'indoor_scene'],
            'office': ['desk', 'laptop', 'keyboard', 'mouse', 'chair'],
            'study_area': ['book', 'desk', 'wall'],
            'living_space': ['chair', 'wall', 'object'],
        }

        self.environment_cache = {
            'last_analysis': None,
            'timestamp': 0,
            'cache_duration': 2.0 
        }

        self.analysis_stats = {
            'total_analyses': 0,
            'avg_processing_time': 0.0,
            'detected_scenes': defaultdict(int),
            'detected_objects': defaultdict(int)
        }
        
        self.init_model()

    def init_model(self):
        """
        Initialize MobileNet SSD model from local files
        """
        try:
            logging.info("Initializing MobileNet SSD for environment analysis...")
            
            model_paths = [
                ("/opt/research_project/models/frozen_inference_graph.pb",
                "/opt/research_project/models/ssd_mobilenet_v2_coco_2018_03_29.pbtxt"),

            ]
            
            model_loaded_successfully = False
            
            for model_file, config_file in model_paths:
                if os.path.exists(model_file) and os.path.exists(config_file):
                    logging.info(f"Found model files: {model_file}")
                    logging.info(f"Model size: {os.path.getsize(model_file) / (1024*1024):.2f} MB")
                    try:
                        self.net = cv2.dnn.readNetFromTensorflow(model_file, config_file)
                        model_loaded_successfully = True
                        logging.info("✓ MobileNet SSD loaded successfully!")
                        break
                    except Exception as e:
                        logging.error(f"Failed to load from {model_file}: {e}")
                        continue
                else:
                    logging.debug(f"Model not found at: {model_file}")
            
            if model_loaded_successfully:
                self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
                self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
                self.classes = self.coco_classes
                self.model_loaded = True
                logging.info(f"✓ Environment analyzer ready with {len(self.coco_classes)} object classes")
                logging.info("✓ Will detect: person, chair, laptop, book, cup, bottle, etc.")
            else:
                logging.warning("="*60)
                logging.warning(" MODEL FILES NOT FOUND!")
                logging.warning("="*60)
                self.model_loaded = False
                self.net = None
            
        except Exception as e:
            import traceback
            logging.error(traceback.format_exc())
            self.model_loaded = False
            self.net = None

    def detect_objects(self, frame):
        """
        Detect objects in frame using MobileNet SSD
        Returns list of detected objects with confidence scores
        """
        if not self.model_loaded or self.net is None:
            return self.fallback_object_detection(frame)
        
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
            
            detected_objects = []
            
            for i in range(detections.shape[2]):
                confidence = detections[0, 0, i, 2]
                
                if confidence > self.confidence_threshold:
                    class_id = int(detections[0, 0, i, 1])
                    
                    if class_id < len(self.classes):
                        box = detections[0, 0, i, 3:7] * np.array([width, height, width, height])
                        (x1, y1, x2, y2) = box.astype("int")
                        
                        detected_objects.append({
                            'class': self.classes[class_id],
                            'confidence': float(confidence),
                            'bbox': [int(x1), int(y1), int(x2), int(y2)],
                            'class_id': class_id
                        })
            
            processing_time = time.time() - start_time
            self.update_stats(processing_time, detected_objects)
            
            return detected_objects
            
        except Exception as e:
            logging.error(f"Object detection error: {e}")
            return []
    
    def fallback_object_detection(self, frame):
        """Enhanced fallback detection"""
        try:
            detected_objects = []
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            edges = cv2.Canny(gray, 30, 100)
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            for i, contour in enumerate(contours[:15]):  
                area = cv2.contourArea(contour)
                if area > 500:  
                    x, y, w, h = cv2.boundingRect(contour)
                    aspect_ratio = w / float(h) if h > 0 else 0
                    
                    if 0.8 < aspect_ratio < 1.2 and area > 5000:
                        obj_type = 'book'
                    elif aspect_ratio > 2 and area > 3000:
                        obj_type = 'desk'
                    elif 0.3 < aspect_ratio < 0.7 and 500 < area < 2000:
                        obj_type = 'bottle'
                    elif 1.5 < aspect_ratio < 3 and 1000 < area < 5000:
                        obj_type = 'accessory'  
                    else:
                        obj_type = 'object'
                    
                    detected_objects.append({
                        'class': obj_type,
                        'confidence': 0.6,
                        'bbox': [x, y, x+w, y+h],
                        'class_id': -1
                    })
            
            if len(detected_objects) == 0:
                detected_objects.append({
                    'class': 'wall',
                    'confidence': 0.5,
                    'bbox': [0, 0, frame.shape[1], frame.shape[0]],
                    'class_id': -1
                })
            
            return detected_objects
            
        except Exception as e:
            logging.error(f"Fallback detection error: {e}")
            return [{
                'class': 'indoor_scene',
                'confidence': 0.4,
                'bbox': [0, 0, 100, 100],
                'class_id': -1
            }]
    
    def infer_scene(self, detected_objects):
        """
        Infer scene/location based on detected objects
        Returns scene type and confidence
        """
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
                        score += object_counter[obj_name] * 10
                        matches.append(obj_name)
            
            if score > 0:
                scene_scores[scene] = {
                    'score': score,
                    'matches': matches
                }
        
        if not scene_scores:
            return {
                'scene': 'generic_indoor',
                'confidence': 0.3,
                'reasoning': ['Generic indoor environment detected'],
                'object_count': len(detected_objects)
            }
        
        best_scene = max(scene_scores.items(), key=lambda x: x[1]['score'])
        
        max_possible_score = len(self.scene_rules[best_scene[0]]) * 10
        confidence = min(1.0, best_scene[1]['score'] / max_possible_score)
        
        return {
            'scene': best_scene[0],
            'confidence': float(confidence),
            'reasoning': best_scene[1]['matches'],
            'object_count': len(detected_objects)
        }
    
    def analyze_environment(self, frame, use_cache=True):
        """
        Complete environment analysis: detect objects and infer scene
        """
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
        """
        Create a summary of detected objects
        """
        object_counts = Counter([obj['class'] for obj in detected_objects])
        
        summary = {
            'total_objects': len(detected_objects),
            'unique_objects': len(object_counts),
            'object_counts': dict(object_counts),
            'primary_objects': [item[0] for item in object_counts.most_common(5)]
        }
        
        return summary
    
    def generate_description(self, scene_info, detected_objects):
        """
        Generate human-readable description of environment
        """
        scene = scene_info.get('scene', 'unknown').replace('_', ' ').title()
        confidence = float(scene_info.get('confidence', 0.0))
        
        if confidence > 0.7:
            confidence_text = "likely"
        elif confidence > 0.5:
            confidence_text = "possibly"
        elif confidence > 0.3:
            confidence_text = "might be"
        else:
            confidence_text = "appears to be"
        
        description = f"Environment {confidence_text} a {scene}"
        
        if detected_objects and len(detected_objects) > 0:
            object_names = [obj['class'] for obj in detected_objects[:3]]
            objects_text = ', '.join(object_names)
            description += f". Detected: {objects_text}"
            
            if len(detected_objects) > 3:
                description += f" and {len(detected_objects) - 3} more objects"
        else:
            description += ". No specific objects identified"
        
        return description
    
    def update_stats(self, processing_time, detected_objects):
        """Update analysis statistics"""
        self.analysis_stats['total_analyses'] += 1
        
        current_avg = self.analysis_stats['avg_processing_time']
        count = self.analysis_stats['total_analyses']
        self.analysis_stats['avg_processing_time'] = (
            (current_avg * (count - 1) + processing_time) / count
        )
        
        for obj in detected_objects:
            self.analysis_stats['detected_objects'][obj['class']] += 1
    
    def get_stats(self):
        """Get analysis statistics"""
        return {
            'total_analyses': self.analysis_stats['total_analyses'],
            'avg_processing_time': round(self.analysis_stats['avg_processing_time'], 3),
            'most_detected_objects': dict(
                sorted(
                    self.analysis_stats['detected_objects'].items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:10]
            )
        }


if __name__ == "__main__":
    analyzer = EnvironmentAnalyzer()
    
    cap = cv2.VideoCapture(0)
    
    print("Environment Analyzer Test")
    print("Press 'q' to quit")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        result = analyzer.analyze_environment(frame)
        
        print("\n" + "="*50)
        print(f"Scene: {result['scene']['scene']}")
        print(f"Confidence: {result['scene']['confidence']:.2f}")
        print(f"Description: {result['environment_description']}")
        print(f"Objects detected: {result['object_summary']['total_objects']}")
        
        for obj in result['objects']:
            x1, y1, x2, y2 = obj['bbox']
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            label = f"{obj['class']}: {obj['confidence']:.2f}"
            cv2.putText(frame, label, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        cv2.imshow('Environment Analysis', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    
    print("\nFinal Statistics:")
    print(json.dumps(analyzer.get_stats(), indent=2))
