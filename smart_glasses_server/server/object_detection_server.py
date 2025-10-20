import cv2
import numpy as np
from flask import Flask, Response, request, jsonify, render_template
from flask_cors import CORS
import base64
import json
import os
import time
import logging
import threading
import atexit
import socket
from collections import defaultdict, deque
from datetime import datetime

try:
    from picamera2 import Picamera2
    from libcamera import controls
    RPI_CAMERA_AVAILABLE = True
    print("Picamera2 available - Raspberry Pi camera support enabled")
except ImportError:
    RPI_CAMERA_AVAILABLE = False
    print("Picamera2 not available - falling back to OpenCV")

try:
    import tensorflow as tf
    TFLITE_AVAILABLE = True
    print("TensorFlow Lite available")
except ImportError:
    TFLITE_AVAILABLE = False
    print("TensorFlow Lite not available - please install: pip install tensorflow")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

BASE_DIR = '/opt/research_project'
TEMPLATES_DIR = '/opt/research_project/templates'
STATIC_DIR = '/opt/research_project/static'
MODELS_DIR = '/opt/research_project/models'

app = Flask(
    __name__,
    template_folder=TEMPLATES_DIR,
    static_folder=STATIC_DIR
)
CORS(app)

# Sinhala translations for COCO dataset objects (80 classes)
SINHALA_TRANSLATIONS = {
    'person': 'පුද්ගලයා',
    'bicycle': 'බයිසිකලය',
    'car': 'මෝටර් රථය',
    'motorcycle': 'යතුරුපැදිය',
    'airplane': 'ගුවන් යානය',
    'bus': 'බස් රථය',
    'train': 'දුම්රිය',
    'truck': 'ට්‍රක් රථය',
    'boat': 'බෝට්ටුව',
    'traffic light': 'රථවාහන ආලෝකය',
    'fire hydrant': 'ගිනි නිවන යන්ත්‍රය',
    'stop sign': 'නවතින්න සලකුණ',
    'parking meter': 'වාහන නැවැත්වීමේ මීටරය',
    'bench': 'ආසනය',
    'bird': 'කුරුල්ලා',
    'cat': 'බළලා',
    'dog': 'බල්ලා',
    'horse': 'අශ්වයා',
    'sheep': 'බැටළුවා',
    'cow': 'ගවයා',
    'elephant': 'ඇත්තා',
    'bear': 'වලසා',
    'zebra': 'සීබ්‍රා',
    'giraffe': 'ජිරාෆ්',
    'backpack': 'බෑග් පැක්',
    'umbrella': 'කුඩය',
    'handbag': 'අත් බෑගය',
    'tie': 'ටයිය',
    'suitcase': 'සූට්කේස්',
    'frisbee': 'ෆ්‍රිස්බී',
    'skis': 'ස්කීස්',
    'snowboard': 'හිම පුවරුව',
    'sports ball': 'ක්‍රීඩා බෝලය',
    'kite': 'සරුංගලය',
    'baseball bat': 'බේස්බෝල් පිත්ත',
    'baseball glove': 'බේස්බෝල් අත්වැසුම',
    'skateboard': 'ස්කේට්බෝඩ්',
    'surfboard': 'සර්ෆ් පුවරුව',
    'tennis racket': 'ටෙනිස් ක්‍රීඩා පිත්ත',
    'bottle': 'බෝතලය',
    'wine glass': 'වයින් වීදුරුව',
    'cup': 'කෝප්පය',
    'fork': 'ගෑරුප්පුව',
    'knife': 'පිහිය',
    'spoon': 'හැන්දක',
    'bowl': 'බඳුන',
    'banana': 'කෙසෙල්',
    'apple': 'ඇපල්',
    'sandwich': 'සෑන්ඩ්විච්',
    'orange': 'දොඩම්',
    'broccoli': 'බ්‍රොකොලි',
    'carrot': 'කැරට්',
    'hot dog': 'හොට් ඩෝග්',
    'pizza': 'පීසා',
    'donut': 'ඩෝනට්',
    'cake': 'කේක්',
    'chair': 'පුටුව',
    'couch': 'යහන',
    'potted plant': 'පැල භාජනය',
    'bed': 'ඇඳ',
    'dining table': 'කෑම මේසය',
    'toilet': 'වැසිකිලිය',
    'tv': 'රූපවාහිනිය',
    'laptop': 'ලැප්ටොප්',
    'mouse': 'මූසිකය',
    'remote': 'රිමෝට්',
    'keyboard': 'යතුරු පුවරුව',
    'cell phone': 'ජංගම දුරකථනය',
    'microwave': 'මයික්‍රෝවේව්',
    'oven': 'උලුව',
    'toaster': 'ටෝස්ටරය',
    'sink': 'සින්ක්',
    'refrigerator': 'ශීතකරණය',
    'book': 'පොත',
    'clock': 'ඔරලෝසුව',
    'vase': 'බඳුන',
    'scissors': 'කතුර',
    'teddy bear': 'ටෙඩි බෙයාර්',
    'hair drier': 'හිසකෙස් වියළනය',
    'toothbrush': 'දත් බුරුසුව'
}


class ObjectDetectionServer:
    def __init__(self):
        self.interpreter = None
        self.model_loaded = False
        self.labels = []
        
        self.confidence_threshold = 0.5
        self.max_detections = 10
        
        self.picamera2 = None
        self.camera = None
        self.camera_mode = None
        self.camera_active = False
        self.camera_lock = threading.Lock()
        self.last_frame = None
        self.frame_capture_thread = None
        self.stop_capture = False
        self.camera_error = None
        
        self.camera_settings = {
            'width': 640,
            'height': 480,
            'fps': 30
        }
        
        self.detection_stats = {
            'total_detections': 0,
            'objects_detected': defaultdict(int),
            'avg_processing_time': 0.0,
            'total_requests': 0
        }
        
        self.init_tflite_model()
    
    def init_tflite_model(self):
        """Initialize TensorFlow Lite model"""
        try:
            if not TFLITE_AVAILABLE:
                logging.error("TensorFlow Lite not available")
                return False
            
            model_path = os.path.join(MODELS_DIR, 'detect.tflite')
            labels_path = os.path.join(MODELS_DIR, 'labelmap.txt')
            
            if not os.path.exists(model_path):
                logging.warning(f"Model not found at {model_path}")
                return False
            
            self.interpreter = tf.lite.Interpreter(model_path=model_path)
            self.interpreter.allocate_tensors()
            
            self.input_details = self.interpreter.get_input_details()
            self.output_details = self.interpreter.get_output_details()
            
            self.input_shape = self.input_details[0]['shape']
            self.input_height = self.input_shape[1]
            self.input_width = self.input_shape[2]
            
            if os.path.exists(labels_path):
                with open(labels_path, 'r') as f:
                    self.labels = [line.strip() for line in f.readlines()]
            else:
                self.labels = list(SINHALA_TRANSLATIONS.keys())
            
            self.model_loaded = True
            logging.info(f"TFLite model loaded: {self.input_width}x{self.input_height}")
            return True
            
        except Exception as e:
            logging.error(f"Error loading TFLite model: {e}")
            self.model_loaded = False
            return False
    
    def detect_objects(self, image):
        """Detect objects in image"""
        start_time = time.time()
        
        try:
            if not self.model_loaded:
                return {
                    'success': False,
                    'message': 'Model not loaded',
                    'detections': [],
                    'processing_time': 0.0
                }
            
            input_data = self.preprocess_image(image)
            
            self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
            self.interpreter.invoke()
            
            boxes = self.interpreter.get_tensor(self.output_details[0]['index'])[0]
            classes = self.interpreter.get_tensor(self.output_details[1]['index'])[0]
            scores = self.interpreter.get_tensor(self.output_details[2]['index'])[0]
            num_detections = int(self.interpreter.get_tensor(self.output_details[3]['index'])[0])
            
            detections = []
            height, width = image.shape[:2]
            
            for i in range(min(num_detections, self.max_detections)):
                if scores[i] >= self.confidence_threshold:
                    ymin, xmin, ymax, xmax = boxes[i]
                    
                    bbox = {
                        'x1': int(xmin * width),
                        'y1': int(ymin * height),
                        'x2': int(xmax * width),
                        'y2': int(ymax * height)
                    }
                    
                    class_id = int(classes[i])
                    if class_id < len(self.labels):
                        label_en = self.labels[class_id]
                        label_si = SINHALA_TRANSLATIONS.get(label_en, label_en)
                    else:
                        label_en = f"Unknown_{class_id}"
                        label_si = f"නොදන්නා_{class_id}"
                    
                    detection = {
                        'label_english': label_en,
                        'label_sinhala': label_si,
                        'confidence': float(scores[i]),
                        'bbox': bbox
                    }
                    
                    detections.append(detection)
                    self.detection_stats['objects_detected'][label_en] += 1
            
            processing_time = time.time() - start_time
            
            self.detection_stats['total_detections'] += len(detections)
            self.detection_stats['total_requests'] += 1
            avg_time = self.detection_stats['avg_processing_time']
            count = self.detection_stats['total_requests']
            self.detection_stats['avg_processing_time'] = ((avg_time * (count - 1)) + processing_time) / count
            
            return {
                'success': True,
                'detections': detections,
                'num_detections': len(detections),
                'processing_time': float(processing_time),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logging.error(f"Detection error: {e}")
            return {
                'success': False,
                'message': str(e),
                'detections': [],
                'processing_time': float(time.time() - start_time)
            }
    
    def preprocess_image(self, image):
        """Preprocess image for model"""
        input_image = cv2.resize(image, (self.input_width, self.input_height))
        
        if len(input_image.shape) == 2:
            input_image = cv2.cvtColor(input_image, cv2.COLOR_GRAY2RGB)
        elif input_image.shape[2] == 4:
            input_image = cv2.cvtColor(input_image, cv2.COLOR_BGRA2RGB)
        else:
            input_image = cv2.cvtColor(input_image, cv2.COLOR_BGR2RGB)
        
        if self.input_details[0]['dtype'] == np.uint8:
            input_data = np.expand_dims(input_image, axis=0).astype(np.uint8)
        else:
            input_data = np.expand_dims(input_image, axis=0).astype(np.float32)
            input_data = (input_data - 127.5) / 127.5
        
        return input_data
    
    def draw_detections(self, image, detections):
        """Draw bounding boxes and labels on image"""
        annotated_image = image.copy()
        
        for det in detections:
            bbox = det['bbox']
            label_si = det['label_sinhala']
            confidence = det['confidence']
            
            cv2.rectangle(
                annotated_image,
                (bbox['x1'], bbox['y1']),
                (bbox['x2'], bbox['y2']),
                (0, 255, 0),
                2
            )
            
            label_text = f"{label_si} ({confidence:.2f})"
            
            (text_width, text_height), baseline = cv2.getTextSize(
                label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1
            )
            
            cv2.rectangle(
                annotated_image,
                (bbox['x1'], bbox['y1'] - text_height - 10),
                (bbox['x1'] + text_width, bbox['y1']),
                (0, 255, 0),
                -1
            )
            
            cv2.putText(
                annotated_image,
                label_text,
                (bbox['x1'], bbox['y1'] - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 0),
                1,
                cv2.LINE_AA
            )
        
        return annotated_image
    
    def init_rpi_camera(self):
        """Initialize Raspberry Pi camera"""
        try:
            if not RPI_CAMERA_AVAILABLE:
                return self.init_usb_camera()
            
            self.picamera2 = Picamera2()
            config = self.picamera2.create_video_configuration(
                main={"size": (640, 480)}
            )
            self.picamera2.configure(config)
            self.picamera2.start()
            time.sleep(2)
            
            self.camera_mode = 'rpi'
            logging.info("RPi camera initialized")
            return True
        except Exception as e:
            logging.error(f"RPi camera failed: {e}")
            return self.init_usb_camera()
    
    def init_usb_camera(self):
        """Initialize USB camera"""
        try:
            for camera_id in [0, 1, 2]:
                test_camera = cv2.VideoCapture(camera_id)
                if test_camera.isOpened():
                    ret, frame = test_camera.read()
                    test_camera.release()
                    if ret and frame is not None:
                        self.camera = cv2.VideoCapture(camera_id)
                        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                        self.camera_mode = 'usb'
                        logging.info(f"USB camera {camera_id} initialized")
                        return True
            return False
        except Exception as e:
            logging.error(f"USB camera error: {e}")
            return False
    
    def start_camera(self):
        """Start camera"""
        try:
            with self.camera_lock:
                if self.camera_active:
                    return True
                
                if self.init_rpi_camera() or (self.camera_mode == 'usb' and self.camera):
                    self.camera_active = True
                    self.stop_capture = False
                    self.frame_capture_thread = threading.Thread(
                        target=self._continuous_capture,
                        daemon=True
                    )
                    self.frame_capture_thread.start()
                    logging.info("Camera started")
                    return True
                
                self.camera_error = "No camera available"
                return False
        except Exception as e:
            logging.error(f"Camera start error: {e}")
            return False
    
    def _continuous_capture(self):
        """Capture frames continuously"""
        while not self.stop_capture:
            try:
                if self.camera_mode == 'rpi' and self.picamera2:
                    frame_rgb = self.picamera2.capture_array()
                    if frame_rgb is not None:
                        frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
                        with self.camera_lock:
                            self.last_frame = frame_bgr.copy()
                elif self.camera_mode == 'usb' and self.camera:
                    ret, frame = self.camera.read()
                    if ret and frame is not None:
                        with self.camera_lock:
                            self.last_frame = frame.copy()
                
                time.sleep(1.0 / 30)
            except Exception as e:
                logging.error(f"Capture error: {e}")
                time.sleep(0.5)
    
    def stop_camera(self):
        """Stop camera"""
        try:
            with self.camera_lock:
                self.stop_capture = True
                self.camera_active = False
                
                if self.picamera2:
                    self.picamera2.stop()
                    self.picamera2.close()
                    self.picamera2 = None
                
                if self.camera:
                    self.camera.release()
                    self.camera = None
                
                self.last_frame = None
            return True
        except Exception as e:
            logging.error(f"Stop camera error: {e}")
            return False
    
    def capture_frame(self):
        """Get latest frame"""
        with self.camera_lock:
            if self.last_frame is not None:
                return self.last_frame.copy()
        return None
    
    def frame_to_base64(self, frame):
        """Convert frame to base64"""
        try:
            if frame is None:
                return None
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if not ret:
                return None
            return base64.b64encode(buffer).decode('utf-8')
        except Exception as e:
            logging.error(f"Frame conversion error: {e}")
            return None


detection_server = ObjectDetectionServer()


@app.route('/')
def web_interface():
    return render_template('object_detection_index.html')


@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'model_loaded': detection_server.model_loaded,
        'camera_active': detection_server.camera_active,
        'camera_mode': detection_server.camera_mode,
        'detection_stats': dict(detection_server.detection_stats),
        'supported_objects': len(SINHALA_TRANSLATIONS)
    })


@app.route('/api/detect', methods=['POST'])
def detect_objects():
    try:
        data = request.json
        if not data or 'image' not in data:
            return jsonify({'error': 'No image data'}), 400
        
        img_data = base64.b64decode(data['image'])
        nparr = np.frombuffer(img_data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            return jsonify({'error': 'Invalid image'}), 400
        
        result = detection_server.detect_objects(image)
        return jsonify(result)
    except Exception as e:
        logging.error(f"Detection error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/camera/start', methods=['POST'])
def start_camera():
    try:
        success = detection_server.start_camera()
        return jsonify({
            'success': success,
            'message': 'Camera started' if success else 'Failed to start',
            'camera_active': success
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/camera/stop', methods=['POST'])
def stop_camera():
    try:
        detection_server.stop_camera()
        return jsonify({
            'success': True,
            'message': 'Camera stopped',
            'camera_active': False
        })
    except Exception as e:
        return jsonify({'success': True, 'message': 'Stopped'}), 200


@app.route('/api/camera/detect', methods=['GET'])
def camera_detect():
    try:
        if not detection_server.camera_active:
            return jsonify({'error': 'Camera not active'}), 400
        
        frame = detection_server.capture_frame()
        if frame is None:
            return jsonify({'error': 'No frame available'}), 404
        
        result = detection_server.detect_objects(frame)
        annotated_frame = detection_server.draw_detections(frame, result['detections'])
        frame_base64 = detection_server.frame_to_base64(annotated_frame)
        result['image'] = frame_base64
        
        return jsonify(result)
    except Exception as e:
        logging.error(f"Camera detect error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/translations', methods=['GET'])
def get_translations():
    return jsonify({
        'translations': SINHALA_TRANSLATIONS,
        'total_objects': len(SINHALA_TRANSLATIONS)
    })


@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    return jsonify({
        'stats': dict(detection_server.detection_stats),
        'objects_detected': dict(detection_server.detection_stats['objects_detected'])
    })


def cleanup_camera():
    if detection_server.camera:
        detection_server.stop_camera()


atexit.register(cleanup_camera)


if __name__ == '__main__':
    print("="*60)
    print("Object Detection Server with Sinhala Translation")
    print("="*60)
    print(f"Model Status: {'Loaded' if detection_server.model_loaded else 'Not Loaded'}")
    print(f"Supported Objects: {len(SINHALA_TRANSLATIONS)}")
    print(f"Port: 5005")
    print(f"URL: http://localhost:5005")
    print("="*60)
    
    app.run(host='0.0.0.0', port=5005, debug=False, threaded=True)