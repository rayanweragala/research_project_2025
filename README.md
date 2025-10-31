# Blind Assistant – Mobile App and Smart Glasses Server
## Project Overview

An assistive technology system designed to help people with visual impairments through real-time face recognition, text reading, and obstacle detection using smart glasses and a mobile application.
System Architecture

The Blind Assistant system consists of two integrated components:

- Android Mobile Application - Provides voice feedback and user interaction
- Python Server - Runs on Raspberry Pi or laptop for computer vision and sensor processing

The system enables users to identify people, read text in Sinhala/English, and detect obstacles through intuitive voice feedback.
Key Features

- Face Recognition - Identify familiar people in real-time

- Text Reading (OCR) - Extract and read text from signs and documents in Sinhala and English

- Obstacle Detection - Ultrasonic distance sensing for navigation assistance

- Voice Feedback - Clear audio responses through the mobile app

- Smart Glasses Integration - Designed to work with wearable smart glasses

- Speech Recognition - Recognize speech and invoke function accodingly

**Live Demo:** [https://researchproject2025.vercel.app/]

## Technical Architecture

```bash
Android Mobile App (Java) 
        ⇅
    Wi-Fi Network
        ⇅
Python Flask Servers (Raspberry Pi)
├── Face Recognition (Port 5000)
├── OCR Service (Port 5002)  
└── Distance Sensor (Port 5001)
```

## Repository Structure

```tex
blind-assistant-platform/
├── mobile_application/             
│   ├── app/src/main/java/
│   │   └── com/company/blindassistant/
│   │       ├── EnhancedFaceRecognitionActivity.java
│   │       ├── FaceRecognitionService.java
│   │       ├── SmartGlassesForegroundService.java
│   │       ├── AddFriendActivity.java
│   │       ├── BootReceiver.java
│   │       └── DistanceSensorService.java
|   |       └── FaceQualityAnalyzer.java
|   |       └── ...
│   ├── app/src/main/res/           
│   ├── build.gradle             
│   └── proguard-rules.pro       
│
├── smart_glasses_server/           
│   ├── server/
│   │   ├── face_server.py        
│   │   ├── ocr_server.py           
│   │   ├── ultrasonic_sensor.py 
│   │  
│   ├── database/
│   │   ├── user_management.db      
│   │   ├── face_database.db         
│   │   └── analytics.db          
│   ├── docs/
│   │   ├── requirements.txt
│   │   ├── api_documentation.md
│   │   └── deployment_guide.md
│
├── web_dashboard/                  
│   ├── app/
│   │   ├── page.tsx                 
│   │   ├── layout.tsx               
│   │   ├── team/                  
│   │   ├── documentation/                
│   │   ├── about/             
│   │   └── scope/                
│   ├── components/
│   │   ├── footer.tsx     
│   │   ├── navigation.tsx         
│   │   └── video-hero.tsx        
│   ├── lib/
│   │   ├── raspberry-pi-5-single-board-computer.jpg                
│   │   ├── raspberry-pi-camera-module-2-high-resolution.jpg           
│   │   └── smart-glasses-demo.mp4             
│   └── package.json
```

## Technology Stack

### Mobile Application (Android)

- **Language**: Java (Java 11)
- **Android SDK**: minSdk 27, target/compile 35
- **Libraries**: AndroidX (AppCompat, Material, ConstraintLayout), Google ML Kit (Face Detection), Volley (HTTP networking)
- **Features**: Foreground service, Boot receiver, Bluetooth access, Camera/Microphone permissions, Notifications

### Server Side (Python)

- **Framework**: Flask with CORS enabled
- **Computer Vision**: OpenCV, InsightFace, scikit-learn, TensorFlow, EasyOCR, Tesseract (pytesseract)
- **Text-to-Speech**: pyttsx3
- **Speech to Text**: Model train from Whisper
- **Database**: SQLite for storing face data and analytics
- **Camera Support**: Picamera2 (Raspberry Pi camera) with fallback to USB cameras

## Server Components and Ports

- **Face Recognition Server** (face_server.py) - Port 5000
  - Endpoints: /api/recognize, /api/recognize_realtime, /api/register_enhanced, /api/people, /api/health
- **Ultrasonic Sensor Server** (ultrasonic_sensor.py) - Port 5001
  - Provides distance readings via HTTP
- **Speech to Text** (stt_model.py)- Port 5004
  - Recognize Sinhala Speech for Sinhala Language
- **OCR Server** (ocr_server.py) - Port 5002
  - Endpoints: /api/ocr/process, /api/ocr/results, /api/ocr/health
- **Dashboard** (start_dashboard.py) - Web-based monitoring interface

## Installation and Setup

## Server Setup

**1. Prerequisites**

- Python 3.10 or higher
- Raspberry Pi or laptop with camera support

**2. Installation Steps**

```bas
cd smart_glasses_server
pip install -r docs/requirements.txt
```

**3. Starting Services**

```bas
# Terminal 1 - Face Recognition
python server/face_server.py

# Terminal 2 - Ultrasonic Sensor
python server/ultrasonic_sensor.py

# Terminal 3 - OCR Service
python server/ocr_server.py
```

**4. Verification**

- Check console output for each service
- Verify local IP addresses and endpoint lists
- Ensure all services remain running during app usage

### Android Application Setup

1. **Development Environment**
   - Android Studio (Giraffe/Koala or newer)
   - Java 11 for Gradle toolchain
   - Real Android device recommended
2. **Configuration**
   - Open `mobile_application` in Android Studio
   - Update server IP addresses in the following files:
     - `EnhancedFaceRecognitionActivity.java`
     - `FaceRecognitionService.java`
     - `SmartGlassesForegroundService.java`
     - `AddFriendActivity.java`
     - `MockSmartGlassesConnector.java`
     - `DistanceSensorService.java`
3. **Network Configuration**
   - Ensure phone and server are on the same Wi-Fi network
   - Search for "http://" in Android code and replace IP addresses
   - Example: `http://192.168.1.100:5000`
4. **Permissions**
   - Grant camera, microphone, and Bluetooth permissions
   - Build and deploy to device

## Hardware Requirements

### Server Hardware

- **Primary**: Raspberry Pi with Pi Camera module
- **Alternative**: Laptop/desktop with USB camera
- **Sensors**: Ultrasonic sensor connected to server machine GPIO
- **Network**: Wi-Fi connectivity for mobile app communication

### Mobile Requirements

- Android device with camera, microphone, and Bluetooth
- Wi-Fi connectivity for server communication

## Data Management and Privacy

- Face data stored locally in SQLite database (`face_database.db`)
- No external data transmission unless explicitly configured
- All processing occurs on local servers
- User data remains within the system boundary

## Troubleshooting

### Common Issues

1. **Connection Problems**
   - Verify server IP addresses in Android code
   - Confirm phone and server are on same network
   - Check firewall settings on server machine
2. **Camera Issues**
   - Raspberry Pi: Ensure Picamera2 is properly installed
   - USB cameras: Verify OpenCV can access the camera
   - Check server logs for camera initialization errors
3. **Model Loading Errors**
   - Some models (TensorFlow, EasyOCR) may require additional dependencies
   - Verify all requirements from `docs/requirements.txt` are installed
   - Check available CPU/GPU resources
4. **Service Startup**
   - Monitor terminal output for each service
   - Address any missing dependency errors immediately
   - Ensure ports 5000, 5001, and 5002 are available

### Debugging Steps

1. Server-side: Check terminal logs for error messages
2. Client-side: Use Android Studio Logcat to monitor app behavior
3. Network: Verify HTTP requests reach the server endpoints
4. Hardware: Confirm camera and sensor connectivity

## Maintenance and Support

- Regular updates to dependency versions recommended
- Monitor storage usage for face database growth
- Regular testing of all service endpoints
- Backup face database before system updates

## License and Attribution

This project is designed for research and assistive technology applications. Please ensure compliance with local regulations regarding privacy and  data protection when deploying in production environments.
