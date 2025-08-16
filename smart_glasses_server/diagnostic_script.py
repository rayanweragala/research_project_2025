#!/usr/bin/env python3
"""
Face Recognition System Diagnostic Script
Run this to identify and fix issues with your setup
"""

import sys
import os
import cv2
import numpy as np
import sqlite3
import traceback

def check_dependencies():
    """Check if all required dependencies are installed"""
    print("=== Checking Dependencies ===")
    
    required_packages = [
        ('cv2', 'opencv-python'),
        ('numpy', 'numpy'),
        ('flask', 'flask'),
        ('flask_cors', 'flask-cors'),
        ('PIL', 'Pillow'),
        ('sqlite3', 'built-in'),
        ('sklearn', 'scikit-learn'),
        ('insightface', 'insightface'),
    ]
    
    missing_packages = []
    
    for package, install_name in required_packages:
        try:
            __import__(package)
            print(f"✓ {package} - OK")
        except ImportError:
            print(f"✗ {package} - MISSING")
            missing_packages.append(install_name)
    
    if missing_packages:
        print(f"\nMissing packages. Install with:")
        print(f"pip install {' '.join(missing_packages)}")
        return False
    
    print("All dependencies OK!")
    return True

def test_insightface():
    """Test InsightFace model loading"""
    print("\n=== Testing InsightFace ===")
    
    try:
        import insightface
        print("✓ InsightFace imported successfully")
        
        print("Initializing model (this may take time on first run)...")
        model = insightface.app.FaceAnalysis(
            providers=['CPUExecutionProvider'],
            allowed_modules=['detection', 'recognition']
        )
        model.prepare(ctx_id=0, det_size=(640, 640))
        print("✓ InsightFace model loaded successfully")
        
        test_image = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        faces = model.get(test_image)
        print(f"✓ Model test completed (detected {len(faces)} faces in random image)")
        
        return True
        
    except Exception as e:
        print(f"✗ InsightFace error: {e}")
        print("Traceback:", traceback.format_exc())
        
        print("\nTrying to download models...")
        try:
            import insightface.model_zoo as model_zoo
            print("Available models:", model_zoo.model_zoo.keys())
            return False
        except Exception as e2:
            print(f"Model download also failed: {e2}")
            return False

def test_camera():
    """Test camera functionality"""
    print("\n=== Testing Camera ===")
    
    rpi_camera_working = False
    try:
        from picamera2 import Picamera2
        print("✓ Picamera2 available")
        
        picamera2 = Picamera2()
        config = picamera2.create_preview_configuration(
            main={"format": "RGB888", "size": (640, 480)}
        )
        picamera2.configure(config)
        picamera2.start()
        
        frame = picamera2.capture_array()
        if frame is not None and frame.size > 0:
            mean_intensity = np.mean(frame)
            print(f"✓ RPi camera working - intensity: {mean_intensity:.1f}")
            
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            cv2.imwrite('rpi_camera_test.jpg', frame_bgr)
            print("✓ Test image saved as 'rpi_camera_test.jpg'")
            rpi_camera_working = True
        
        picamera2.stop()
        picamera2.close()
        
    except Exception as e:
        print(f"✗ RPi camera error: {e}")
    
    usb_camera_working = False
    for camera_id in range(3):
        try:
            cap = cv2.VideoCapture(camera_id)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    mean_intensity = np.mean(frame)
                    if mean_intensity > 15:
                        print(f"✓ USB camera {camera_id} working - intensity: {mean_intensity:.1f}")
                        cv2.imwrite(f'usb_camera_{camera_id}_test.jpg', frame)
                        print(f"✓ Test image saved as 'usb_camera_{camera_id}_test.jpg'")
                        usb_camera_working = True
                        break
            cap.release()
        except Exception as e:
            print(f"✗ USB camera {camera_id} error: {e}")
    
    if not rpi_camera_working and not usb_camera_working:
        print("✗ No working cameras found!")
        return False
    
    return True

def test_database():
    """Test database functionality"""
    print("\n=== Testing Database ===")
    
    try:
        conn = sqlite3.connect("test_face_database.db")
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS test_people (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE
            )
        ''')
        
        cursor.execute("INSERT OR IGNORE INTO test_people (name) VALUES ('test_person')")
        cursor.execute("SELECT * FROM test_people")
        results = cursor.fetchall()
        
        conn.close()
        os.remove("test_face_database.db")
        
        print(f"✓ Database working - test records: {len(results)}")
        return True
        
    except Exception as e:
        print(f"✗ Database error: {e}")
        return False

def generate_fix_commands():
    """Generate commands to fix common issues"""
    print("\n=== Fix Commands ===")
    
    print("1. Install missing dependencies:")
    print("   pip install insightface onnxruntime scikit-learn opencv-python")
    
    print("\n2. Fix camera permissions:")
    print("   sudo usermod -a -G video $USER")
    print("   (then logout and login again)")
    
    print("\n3. Download InsightFace models manually:")
    print("   python3 -c \"import insightface; app = insightface.app.FaceAnalysis(); app.prepare(ctx_id=0)\"")
    
    print("\n4. Test high-quality camera:")
    print("   rpicam-still -o test_hq.jpg --width 1920 --height 1080")
    
    print("\n5. Check Python environment:")
    print("   which python3")
    print("   python3 -c \"import sys; print(sys.path)\"")

def main():
    """Run all diagnostics"""
    print("Face Recognition System Diagnostic Tool")
    print("=" * 50)
    
    all_good = True
    
    all_good &= check_dependencies()
    all_good &= test_insightface()
    all_good &= test_camera()
    all_good &= test_database()
    
    print("\n" + "=" * 50)
    
    if all_good:
        print("✓ All systems working!")
    else:
        print("✗ Issues detected.")
        generate_fix_commands()
    
    print("\n" + "=" * 50)

if __name__ == "__main__":
    main()