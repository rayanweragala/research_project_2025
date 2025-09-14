#!/usr/bin/env python3
"""
Ultrasonic Distance Sensor Web Server for Raspberry Pi 5
Provides REST API for distance measurements with HC-SR04 sensor
Modified to use lgpio and 4-second measurement intervals
"""

import lgpio
import time
import json
import os
import threading
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import statistics
from collections import deque, defaultdict
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  
ROOT_DIR = os.path.dirname(BASE_DIR)  

app = Flask(
    __name__,
    template_folder=os.path.join(ROOT_DIR, "templates"),
    static_folder=os.path.join(ROOT_DIR, "static")
)
CORS(app)

# GPIO pin configuration for HC-SR04 on Pi 5
TRIG_PIN = 18  # Trigger pin (changed from 23)
ECHO_PIN = 19  # Echo pin (changed from 24)

# Global variables
gpio_handle = None
sensor_active = False
measurement_thread = None
current_distance = 0.0
measurement_history = deque(maxlen=1000)  # Store last 1000 measurements
stats_data = {
    'total_measurements': 0,
    'avg_distance': 0.0,
    'min_distance': float('inf'),
    'max_distance': 0.0,
    'measurement_rate': 0.0,
    'start_time': None,
    'outliers_removed': 0,
    'smoothed_readings': 0
}

# Distance thresholds (in cm)
DISTANCE_THRESHOLDS = {
    'very_close': 10,
    'close': 30,
    'medium': 100,
    'far': 200
}

class DistanceMeasurement:
    def __init__(self, distance, timestamp=None, quality_score=1.0):
        self.distance = distance
        self.timestamp = timestamp or datetime.now()
        self.quality_score = quality_score
        self.zone = self.get_distance_zone(distance)
       
    def get_distance_zone(self, distance):
        if distance <= DISTANCE_THRESHOLDS['very_close']:
            return 'very_close'
        elif distance <= DISTANCE_THRESHOLDS['close']:
            return 'close'
        elif distance <= DISTANCE_THRESHOLDS['medium']:
            return 'medium'
        elif distance <= DISTANCE_THRESHOLDS['far']:
            return 'far'
        else:
            return 'very_far'
   
    def to_dict(self):
        return {
            'distance': self.distance,
            'timestamp': self.timestamp.isoformat(),
            'quality_score': self.quality_score,
            'zone': self.zone
        }

def setup_gpio():
    """Initialize GPIO pins for ultrasonic sensor on Pi 5"""
    global gpio_handle
    
    try:
        # Open GPIO chip 4 (Pi 5)
        gpio_handle = lgpio.gpiochip_open(4)
        
        # Set pin modes
        lgpio.gpio_claim_output(gpio_handle, TRIG_PIN)
        lgpio.gpio_claim_input(gpio_handle, ECHO_PIN)
        
        # Set initial state
        lgpio.gpio_write(gpio_handle, TRIG_PIN, 0)
        time.sleep(0.1)  # Allow sensor to settle
        
        logger.info(f"GPIO initialized - TRIG: {TRIG_PIN}, ECHO: {ECHO_PIN}")
        return True
    except Exception as e:
        logger.error(f"GPIO setup failed: {e}")
        if gpio_handle:
            lgpio.gpiochip_close(gpio_handle)
            gpio_handle = None
        return False

def measure_distance():
    """
    Measure distance using HC-SR04 ultrasonic sensor with Pi 5 lgpio
    Returns distance in centimeters
    """
    global gpio_handle
    
    if gpio_handle is None:
        return None
    
    try:
        # Ensure trigger is low
        lgpio.gpio_write(gpio_handle, TRIG_PIN, 0)
        time.sleep(0.002)  # 2ms settle time
        
        # Send 10us trigger pulse
        lgpio.gpio_write(gpio_handle, TRIG_PIN, 1)
        time.sleep(0.00001)  # 10 microseconds
        lgpio.gpio_write(gpio_handle, TRIG_PIN, 0)
        
        # Wait for echo start with timeout
        start_wait = time.time()
        timeout = start_wait + 0.03  # 30ms timeout
        
        while lgpio.gpio_read(gpio_handle, ECHO_PIN) == 0:
            if time.time() > timeout:
                return None  # No echo start
        
        pulse_start = time.time()
        
        # Wait for echo end with timeout
        timeout = pulse_start + 0.025  # 25ms max (for ~400cm)
        while lgpio.gpio_read(gpio_handle, ECHO_PIN) == 1:
            if time.time() > timeout:
                return None  # Echo too long
        
        pulse_end = time.time()
        
        # Calculate distance
        pulse_duration = pulse_end - pulse_start
        distance = pulse_duration * 17150  # Sound speed = 34300 cm/s, divide by 2
       
        # Validate measurement (HC-SR04 range: 2cm to 400cm)
        if 2 <= distance <= 400:
            return round(distance, 2)
        else:
            return None
           
    except Exception as e:
        logger.error(f"Distance measurement error: {e}")
        return None

def smooth_measurements(measurements, window_size=5):
    """Apply smoothing to reduce noise in measurements"""
    if len(measurements) < window_size:
        return measurements[-1] if measurements else 0
   
    recent = list(measurements)[-window_size:]
    # Remove outliers using IQR method
    if len(recent) >= 3:
        try:
            q1 = statistics.quantiles(recent, n=4)[0]
            q3 = statistics.quantiles(recent, n=4)[2]
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
           
            filtered = [x for x in recent if lower_bound <= x <= upper_bound]
            if filtered:
                stats_data['outliers_removed'] += len(recent) - len(filtered)
                return statistics.mean(filtered)
        except statistics.StatisticsError:
            pass
   
    return statistics.mean(recent)

def continuous_measurement():
    """Continuous measurement loop running in separate thread with 4-second intervals"""
    global current_distance, sensor_active
   
    measurement_times = deque(maxlen=100)
    raw_distances = deque(maxlen=20)
   
    logger.info("Starting continuous measurement with 4-second intervals...")
   
    while sensor_active:
        try:
            start_time = time.time()
           
            # Take multiple readings for better accuracy
            readings = []
            for _ in range(3):
                distance = measure_distance()
                if distance is not None:
                    readings.append(distance)
                time.sleep(0.01)  # Small delay between readings
           
            if readings:
                # Use median of readings to reduce noise
                raw_distance = statistics.median(readings)
                raw_distances.append(raw_distance)
               
                # Apply smoothing
                smoothed_distance = smooth_measurements(raw_distances)
                current_distance = smoothed_distance
               
                # Calculate quality score based on consistency
                quality_score = 1.0
                if len(readings) > 1:
                    try:
                        variance = statistics.variance(readings)
                        quality_score = max(0.1, 1.0 - (variance / 100))  # Lower variance = higher quality
                    except statistics.StatisticsError:
                        quality_score = 0.8
               
                # Store measurement
                measurement = DistanceMeasurement(
                    distance=smoothed_distance,
                    quality_score=quality_score
                )
                measurement_history.append(measurement)
               
                # Update statistics
                update_statistics(smoothed_distance)
               
                # Track measurement rate
                measurement_times.append(time.time())
                if len(measurement_times) >= 10:
                    time_span = measurement_times[-1] - measurement_times[0]
                    stats_data['measurement_rate'] = (len(measurement_times) - 1) / time_span
               
                stats_data['smoothed_readings'] += 1
                
                logger.info(f"Distance: {smoothed_distance:.2f} cm (Quality: {quality_score:.2f})")
           
            # 4-second interval between measurements (changed from 2.0)
            time.sleep(4.0)
           
        except Exception as e:
            logger.error(f"Measurement loop error: {e}")
            time.sleep(4.0)

def update_statistics(distance):
    """Update running statistics"""
    stats_data['total_measurements'] += 1
   
    # Update min/max
    if distance < stats_data['min_distance']:
        stats_data['min_distance'] = distance
    if distance > stats_data['max_distance']:
        stats_data['max_distance'] = distance
   
    # Update rolling average
    recent_distances = [m.distance for m in list(measurement_history)[-100:]]
    if recent_distances:
        stats_data['avg_distance'] = statistics.mean(recent_distances)

@app.route('/api/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'sensor_active': sensor_active,
        'gpio_initialized': gpio_handle is not None,
        'current_distance': current_distance,
        'total_measurements': stats_data['total_measurements'],
        'measurement_rate': round(stats_data['measurement_rate'], 2),
        'pi_model': 'Raspberry Pi 5',
        'gpio_library': 'lgpio',
        'measurement_interval': '4 seconds',
        'features': {
            'real_time_measurement': True,
            'noise_filtering': True,
            'outlier_removal': True,
            'quality_scoring': True,
            'zone_detection': True
        }
    })

@app.route('/api/sensor/start', methods=['POST'])
def start_sensor():
    """Start continuous distance measurements"""
    global sensor_active, measurement_thread
   
    try:
        if not sensor_active:
            if not setup_gpio():
                return jsonify({'success': False, 'message': 'GPIO setup failed'})
           
            sensor_active = True
            stats_data['start_time'] = datetime.now()
            measurement_thread = threading.Thread(target=continuous_measurement, daemon=True)
            measurement_thread.start()
           
            logger.info("Distance sensor started (Pi 5 with 4-second intervals)")
            return jsonify({'success': True, 'message': 'Distance sensor started successfully'})
        else:
            return jsonify({'success': False, 'message': 'Sensor already active'})
           
    except Exception as e:
        logger.error(f"Start sensor error: {e}")
        return jsonify({'success': False, 'message': f'Failed to start sensor: {str(e)}'})

@app.route('/api/sensor/stop', methods=['POST'])
def stop_sensor():
    """Stop distance measurements"""
    global sensor_active, gpio_handle
   
    try:
        sensor_active = False
        if gpio_handle:
            lgpio.gpiochip_close(gpio_handle)
            gpio_handle = None
        logger.info("Distance sensor stopped")
        return jsonify({'success': True, 'message': 'Distance sensor stopped'})
       
    except Exception as e:
        logger.error(f"Stop sensor error: {e}")
        return jsonify({'success': False, 'message': f'Error stopping sensor: {str(e)}'})

@app.route('/api/distance/current')
def get_current_distance():
    """Get current distance reading"""
    if not sensor_active:
        return jsonify({'error': 'Sensor not active'})
   
    latest_measurement = measurement_history[-1] if measurement_history else None
   
    if latest_measurement:
        return jsonify({
            'distance': latest_measurement.distance,
            'zone': latest_measurement.zone,
            'quality_score': latest_measurement.quality_score,
            'timestamp': latest_measurement.timestamp.isoformat(),
            'sensor_active': sensor_active,
            'thresholds': DISTANCE_THRESHOLDS
        })
    else:
        return jsonify({'error': 'No measurements available'})

@app.route('/api/analytics')
def get_analytics():
    """Get measurement analytics and statistics"""
    if not measurement_history:
        return jsonify({
            'message': 'No measurement data available',
            'stats': stats_data,
            'zone_distribution': {},
            'recent_measurements': []
        })
   
    # Calculate zone distribution
    zone_counts = defaultdict(int)
    quality_scores = []
    recent_measurements = []
   
    # Analyze last 100 measurements
    recent_data = list(measurement_history)[-100:]
   
    for measurement in recent_data:
        zone_counts[measurement.zone] += 1
        quality_scores.append(measurement.quality_score)
        recent_measurements.append(measurement.to_dict())
   
    # Calculate quality statistics
    avg_quality = statistics.mean(quality_scores) if quality_scores else 0
   
    # Time-based analysis
    hourly_distribution = defaultdict(int)
    for measurement in recent_data:
        hour = measurement.timestamp.hour
        hourly_distribution[hour] += 1
   
    return jsonify({
        'stats': {
            **stats_data,
            'avg_quality': round(avg_quality, 3),
            'measurements_in_analysis': len(recent_data)
        },
        'zone_distribution': dict(zone_counts),
        'hourly_distribution': dict(hourly_distribution),
        'recent_measurements': recent_measurements[-20:],  # Last 20 measurements
        'thresholds': DISTANCE_THRESHOLDS
    })

@app.route('/api/daily_report')
def get_daily_report():
    """Generate daily measurement report"""
    date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
   
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format'})
   
    # Filter measurements for the target date
    daily_measurements = [
        m for m in measurement_history
        if m.timestamp.date() == target_date
    ]
   
    if not daily_measurements:
        return jsonify({
            'date': date_str,
            'summary': {'total_measurements': 0},
            'message': 'No measurements recorded for this date'
        })
   
    # Calculate daily statistics
    distances = [m.distance for m in daily_measurements]
    quality_scores = [m.quality_score for m in daily_measurements]
   
    zone_distribution = defaultdict(int)
    for measurement in daily_measurements:
        zone_distribution[measurement.zone] += 1
   
    # Generate insights
    insights = []
    avg_distance = statistics.mean(distances)
   
    if avg_distance < 50:
        insights.append("Objects were predominantly close to the sensor today")
    elif avg_distance > 150:
        insights.append("Most objects detected at longer distances today")
   
    closest_distance = min(distances)
    if closest_distance < 10:
        insights.append(f"Closest detection: {closest_distance:.1f}cm - very close proximity detected")
   
    quality_avg = statistics.mean(quality_scores)
    if quality_avg > 0.8:
        insights.append("High measurement quality maintained throughout the day")
    elif quality_avg < 0.6:
        insights.append("Some measurement quality issues detected - check sensor alignment")
   
    return jsonify({
        'date': date_str,
        'summary': {
            'total_measurements': len(daily_measurements),
            'avg_distance': round(avg_distance, 2),
            'min_distance': round(min(distances), 2),
            'max_distance': round(max(distances), 2),
            'avg_quality': round(quality_avg, 3)
        },
        'zone_distribution': dict(zone_distribution),
        'insights': insights,
        'hourly_activity': {
            hour: len([m for m in daily_measurements if m.timestamp.hour == hour])
            for hour in range(24)
        }
    })

@app.route('/api/measurement_logs')
def get_measurement_logs():
    """Get detailed measurement logs"""
    date_str = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
   
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format'})
   
    # Filter measurements for the target date
    daily_measurements = [
        m for m in measurement_history
        if m.timestamp.date() == target_date
    ]
   
    logs = []
    for measurement in daily_measurements[-100:]:  # Last 100 logs
        logs.append({
            'timestamp': measurement.timestamp.isoformat(),
            'distance': measurement.distance,
            'zone': measurement.zone,
            'quality_score': measurement.quality_score
        })
   
    # Calculate averages
    if daily_measurements:
        avg_distance = statistics.mean([m.distance for m in daily_measurements])
        avg_quality = statistics.mean([m.quality_score for m in daily_measurements])
    else:
        avg_distance = avg_quality = 0
   
    return jsonify({
        'logs': logs,
        'total_logs': len(daily_measurements),
        'avg_distance': round(avg_distance, 2),
        'avg_quality': round(avg_quality, 3)
    })

@app.route('/api/generate_test_data', methods=['POST'])
def generate_test_data():
    """Generate test measurement data"""
    try:
        import random
       
        # Generate 50 test measurements
        test_measurements = []
        base_time = datetime.now() - timedelta(hours=2)
       
        for i in range(50):
            # Simulate various distance scenarios
            if i % 10 == 0:
                distance = random.uniform(5, 15)  # Very close
            elif i % 7 == 0:
                distance = random.uniform(15, 40)  # Close
            elif i % 5 == 0:
                distance = random.uniform(40, 120)  # Medium
            else:
                distance = random.uniform(120, 300)  # Far
           
            quality = random.uniform(0.7, 1.0)
            timestamp = base_time + timedelta(minutes=i*4)  # Changed to 4-minute intervals
           
            measurement = DistanceMeasurement(
                distance=round(distance, 2),
                timestamp=timestamp,
                quality_score=round(quality, 3)
            )
           
            test_measurements.append(measurement)
            measurement_history.append(measurement)
       
        # Update statistics
        for measurement in test_measurements:
            update_statistics(measurement.distance)
       
        return jsonify({
            'success': True,
            'message': f'Generated {len(test_measurements)} test measurements'
        })
       
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/')
def dashboard():
    """Serve the main dashboard HTML"""
    return render_template('ultrasonic_sensor_index.html')

@app.route('/api/info')
def api_info():
    """API information endpoint"""
    return jsonify({
        'message': 'Pi 5 Ultrasonic Sensor API (4-second intervals)',
        'status': 'ready',
        'gpio_pins': f'Trig: {TRIG_PIN}, Echo: {ECHO_PIN}',
        'measurement_interval': '4 seconds',
        'pi_model': 'Raspberry Pi 5',
        'gpio_library': 'lgpio',
        'endpoints': {
            'health': '/api/health',
            'start': 'POST /api/sensor/start',
            'stop': 'POST /api/sensor/stop',
            'current': '/api/distance/current',
            'analytics': '/api/analytics',
            'daily_report': '/api/daily_report?date=YYYY-MM-DD',
            'measurement_logs': '/api/measurement_logs?date=YYYY-MM-DD',
            'generate_test_data': 'POST /api/generate_test_data'
        }
    })

if __name__ == '__main__':
    if not os.path.exists('ultrasonic_index.html'):
        print("ultrasonic_index.html not found!")

    try:
        logger.info("Starting Pi 5 Ultrasonic Distance Sensor Server...")
        logger.info("Measurement interval: 4 seconds")
        logger.info(f"GPIO pins - Trig: {TRIG_PIN}, Echo: {ECHO_PIN}")
        app.run(host='0.0.0.0', port=5001, debug=False)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        if sensor_active and gpio_handle:
            lgpio.gpiochip_close(gpio_handle)