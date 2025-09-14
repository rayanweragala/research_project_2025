#!/usr/bin/env python3
"""
Improved Ultrasonic Distance Sensor Web Server for Raspberry Pi 5
Enhanced stability and noise reduction for consistent readings
"""

import lgpio
import time
import json
import threading
from datetime import datetime, timedelta
from flask import Flask, jsonify, request, render_template_string, send_from_directory
from flask_cors import CORS
import statistics
from collections import deque, defaultdict
import logging
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# GPIO pin configuration for HC-SR04 on Pi 5
TRIG_PIN = 18
ECHO_PIN = 19

# Global variables
gpio_handle = None
sensor_active = False
measurement_thread = None
current_distance = 0.0
measurement_history = deque(maxlen=1000)
stats_data = {
    'total_measurements': 0,
    'avg_distance': 0.0,
    'min_distance': float('inf'),
    'max_distance': 0.0,
    'measurement_rate': 0.0,
    'start_time': None,
    'outliers_removed': 0,
    'smoothed_readings': 0,
    'stable_readings': 0
}

# Enhanced filtering parameters
STABILITY_BUFFER = deque(maxlen=20)  # Buffer for stability checking
MOVING_AVERAGE_WINDOW = 10
OUTLIER_THRESHOLD = 3.0  # Standard deviations for outlier detection
MIN_STABLE_READINGS = 5  # Minimum readings before considering stable
STABILITY_TOLERANCE = 2.0  # cm tolerance for considering reading stable

# Distance thresholds (in cm)
DISTANCE_THRESHOLDS = {
    'very_close': 10,
    'close': 30,
    'medium': 100,
    'far': 200
}

class DistanceMeasurement:
    def __init__(self, distance, timestamp=None, quality_score=1.0, is_stable=False):
        self.distance = distance
        self.timestamp = timestamp or datetime.now()
        self.quality_score = quality_score
        self.zone = self.get_distance_zone(distance)
        self.is_stable = is_stable
       
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
            'zone': self.zone,
            'is_stable': self.is_stable
        }

def setup_gpio():
    """Initialize GPIO pins for ultrasonic sensor with enhanced stability"""
    global gpio_handle
    
    try:
        gpio_handle = lgpio.gpiochip_open(4)
        
        # Set pin modes with debounce for echo pin
        lgpio.gpio_claim_output(gpio_handle, TRIG_PIN)
        lgpio.gpio_claim_input(gpio_handle, ECHO_PIN)
        
        # Set initial state and allow longer settling time
        lgpio.gpio_write(gpio_handle, TRIG_PIN, 0)
        time.sleep(0.5)  # Increased settling time
        
        logger.info(f"GPIO initialized with enhanced stability - TRIG: {TRIG_PIN}, ECHO: {ECHO_PIN}")
        return True
    except Exception as e:
        logger.error(f"GPIO setup failed: {e}")
        if gpio_handle:
            lgpio.gpiochip_close(gpio_handle)
            gpio_handle = None
        return False

def measure_distance_raw():
    """
    Single raw distance measurement with improved timing and error handling
    """
    global gpio_handle
    
    if gpio_handle is None:
        return None
    
    max_retries = 3
    for retry in range(max_retries):
        try:
            # Ensure clean start state
            lgpio.gpio_write(gpio_handle, TRIG_PIN, 0)
            time.sleep(0.005)  # Increased settling time
            
            # Send precise 10us trigger pulse
            lgpio.gpio_write(gpio_handle, TRIG_PIN, 1)
            time.sleep(0.00001)  # 10 microseconds
            lgpio.gpio_write(gpio_handle, TRIG_PIN, 0)
            
            # Wait for echo start with precise timeout
            start_wait = time.time()
            timeout_start = 0.02  # 20ms timeout for echo start
            
            while lgpio.gpio_read(gpio_handle, ECHO_PIN) == 0:
                if time.time() - start_wait > timeout_start:
                    if retry < max_retries - 1:
                        time.sleep(0.01)
                        continue
                    return None
            
            pulse_start = time.time()
            
            # Wait for echo end with appropriate timeout
            timeout_echo = 0.025  # 25ms max echo duration
            while lgpio.gpio_read(gpio_handle, ECHO_PIN) == 1:
                if time.time() - pulse_start > timeout_echo:
                    if retry < max_retries - 1:
                        time.sleep(0.01)
                        continue
                    return None
            
            pulse_end = time.time()
            
            # Calculate distance with improved precision
            pulse_duration = pulse_end - pulse_start
            distance = (pulse_duration * 34300) / 2  # Speed of sound at 20°C
           
            # Validate measurement range
            if 2 <= distance <= 400:
                return round(distance, 2)
            elif retry < max_retries - 1:
                time.sleep(0.01)
                continue
            else:
                return None
               
        except Exception as e:
            if retry < max_retries - 1:
                time.sleep(0.01)
                continue
            logger.error(f"Distance measurement error on retry {retry}: {e}")
            return None
    
    return None

def get_stable_measurement():
    """
    Take multiple measurements and return a stable, filtered result
    """
    measurements = []
    measurement_count = 8  # Increased sample size
    
    for i in range(measurement_count):
        distance = measure_distance_raw()
        if distance is not None:
            measurements.append(distance)
        
        # Variable delay between measurements based on iteration
        if i < measurement_count - 1:
            time.sleep(0.02 if i < 4 else 0.05)
    
    if not measurements:
        return None, 0.0
    
    if len(measurements) < 3:
        return statistics.mean(measurements), 0.5
    
    # Remove obvious outliers using IQR method
    try:
        q1, median, q3 = statistics.quantiles(measurements, n=4)
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        filtered_measurements = [x for x in measurements if lower_bound <= x <= upper_bound]
        
        if filtered_measurements:
            outliers_removed = len(measurements) - len(filtered_measurements)
            stats_data['outliers_removed'] += outliers_removed
            
            # Use median for better noise resistance
            stable_distance = statistics.median(filtered_measurements)
            
            # Calculate quality based on consistency
            if len(filtered_measurements) > 1:
                std_dev = statistics.stdev(filtered_measurements)
                quality = max(0.1, 1.0 - min(std_dev / 10.0, 0.9))
            else:
                quality = 0.8
                
            return stable_distance, quality
        else:
            return statistics.median(measurements), 0.3
            
    except statistics.StatisticsError:
        return statistics.mean(measurements), 0.4

def apply_advanced_smoothing(new_distance, quality):
    """
    Apply advanced smoothing with stability detection
    """
    global STABILITY_BUFFER
    
    STABILITY_BUFFER.append(new_distance)
    
    if len(STABILITY_BUFFER) < MIN_STABLE_READINGS:
        return new_distance, quality, False
    
    # Convert to numpy array for better calculations
    recent_readings = list(STABILITY_BUFFER)
    
    # Check for stability (low variance over recent readings)
    if len(recent_readings) >= MIN_STABLE_READINGS:
        recent_std = statistics.stdev(recent_readings[-MIN_STABLE_READINGS:])
        is_stable = recent_std < STABILITY_TOLERANCE
        
        if is_stable:
            stats_data['stable_readings'] += 1
            # Use more aggressive smoothing for stable readings
            weights = np.array([0.1, 0.15, 0.2, 0.25, 0.3])  # More weight to recent readings
            if len(recent_readings) >= 5:
                smoothed = np.average(recent_readings[-5:], weights=weights)
                return round(smoothed, 2), min(quality * 1.2, 1.0), True
    
    # Adaptive moving average with outlier rejection
    window_size = min(MOVING_AVERAGE_WINDOW, len(recent_readings))
    recent_window = recent_readings[-window_size:]
    
    # Remove outliers from the window
    if len(recent_window) >= 3:
        median_val = statistics.median(recent_window)
        mad = statistics.median([abs(x - median_val) for x in recent_window])  # Median Absolute Deviation
        
        if mad > 0:
            threshold = 2 * mad  # More conservative threshold
            filtered_window = [x for x in recent_window if abs(x - median_val) <= threshold]
            
            if filtered_window:
                # Weighted average favoring recent stable readings
                if len(filtered_window) >= 3:
                    return round(statistics.median(filtered_window), 2), quality, False
    
    # Fallback to simple average
    return round(statistics.mean(recent_window), 2), quality, False

def continuous_measurement():
    """Enhanced continuous measurement with improved stability"""
    global current_distance, sensor_active
   
    measurement_times = deque(maxlen=100)
    consecutive_stable_count = 0
    
    logger.info("Starting enhanced continuous measurement (4-second intervals)...")
   
    while sensor_active:
        try:
            start_time = time.time()
           
            # Get stable measurement
            raw_distance, base_quality = get_stable_measurement()
            
            if raw_distance is not None:
                # Apply advanced smoothing
                smoothed_distance, final_quality, is_stable = apply_advanced_smoothing(raw_distance, base_quality)
                
                # Track consecutive stable readings
                if is_stable:
                    consecutive_stable_count += 1
                else:
                    consecutive_stable_count = 0
                
                # Boost quality for consistently stable readings
                if consecutive_stable_count >= 3:
                    final_quality = min(final_quality * 1.1, 1.0)
                
                current_distance = smoothed_distance
                
                # Store measurement
                measurement = DistanceMeasurement(
                    distance=smoothed_distance,
                    quality_score=final_quality,
                    is_stable=is_stable
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
                
                stability_indicator = "STABLE" if is_stable else "VARYING"
                logger.info(f"Distance: {smoothed_distance:.2f} cm ({stability_indicator}) Quality: {final_quality:.2f}")
            else:
                logger.warning("Failed to get stable measurement")
                consecutive_stable_count = 0
           
            # Maintain 4-second intervals
            elapsed = time.time() - start_time
            sleep_time = max(0, 4.0 - elapsed)
            time.sleep(sleep_time)
           
        except Exception as e:
            logger.error(f"Measurement loop error: {e}")
            consecutive_stable_count = 0
            time.sleep(4.0)

def update_statistics(distance):
    """Update running statistics with enhanced tracking"""
    stats_data['total_measurements'] += 1
   
    # Update min/max
    if distance < stats_data['min_distance']:
        stats_data['min_distance'] = distance
    if distance > stats_data['max_distance']:
        stats_data['max_distance'] = distance
   
    # Update rolling average with more weight to recent measurements
    recent_distances = [m.distance for m in list(measurement_history)[-50:]]  # Reduced window for more responsive average
    if recent_distances:
        stats_data['avg_distance'] = statistics.mean(recent_distances)

# Keep all the existing Flask routes unchanged
@app.route('/api/health')
def health_check():
    """Enhanced health check with stability metrics"""
    stability_metrics = {
        'stable_reading_percentage': 0,
        'buffer_size': len(STABILITY_BUFFER),
        'outliers_removed': stats_data['outliers_removed']
    }
    
    if stats_data['smoothed_readings'] > 0:
        stability_metrics['stable_reading_percentage'] = round(
            (stats_data['stable_readings'] / stats_data['smoothed_readings']) * 100, 1
        )
    
    return jsonify({
        'status': 'healthy',
        'sensor_active': sensor_active,
        'gpio_initialized': gpio_handle is not None,
        'current_distance': current_distance,
        'total_measurements': stats_data['total_measurements'],
        'measurement_rate': round(stats_data['measurement_rate'], 2),
        'pi_model': 'Raspberry Pi 5',
        'gpio_library': 'lgpio (Enhanced)',
        'measurement_interval': '4 seconds',
        'stability_metrics': stability_metrics,
        'features': {
            'real_time_measurement': True,
            'advanced_noise_filtering': True,
            'outlier_removal': True,
            'stability_detection': True,
            'quality_scoring': True,
            'zone_detection': True,
            'adaptive_smoothing': True
        }
    })

@app.route('/api/sensor/start', methods=['POST'])
def start_sensor():
    """Start enhanced sensor with automatic initialization"""
    global sensor_active, measurement_thread, STABILITY_BUFFER
   
    try:
        if not sensor_active:
            # Clear previous data
            STABILITY_BUFFER.clear()
            stats_data.update({
                'total_measurements': 0,
                'outliers_removed': 0,
                'smoothed_readings': 0,
                'stable_readings': 0,
                'start_time': datetime.now()
            })
            
            if not setup_gpio():
                return jsonify({'success': False, 'message': 'GPIO setup failed'})
           
            sensor_active = True
            measurement_thread = threading.Thread(target=continuous_measurement, daemon=True)
            measurement_thread.start()
           
            logger.info("Enhanced distance sensor started successfully")
            return jsonify({'success': True, 'message': 'Enhanced sensor started with stability features'})
        else:
            return jsonify({'success': False, 'message': 'Sensor already active'})
           
    except Exception as e:
        logger.error(f"Start sensor error: {e}")
        return jsonify({'success': False, 'message': f'Failed to start sensor: {str(e)}'})

@app.route('/api/sensor/stop', methods=['POST'])
def stop_sensor():
    """Stop sensor and cleanup"""
    global sensor_active, gpio_handle, STABILITY_BUFFER
   
    try:
        sensor_active = False
        STABILITY_BUFFER.clear()
        
        if gpio_handle:
            lgpio.gpiochip_close(gpio_handle)
            gpio_handle = None
            
        logger.info("Enhanced distance sensor stopped")
        return jsonify({'success': True, 'message': 'Enhanced sensor stopped'})
       
    except Exception as e:
        logger.error(f"Stop sensor error: {e}")
        return jsonify({'success': False, 'message': f'Error stopping sensor: {str(e)}'})

# Keep all other existing routes (get_current_distance, get_analytics, etc.) unchanged
@app.route('/api/distance/current')
def get_current_distance():
    """Get current distance reading with stability info"""
    if not sensor_active:
        return jsonify({'error': 'Sensor not active'})
   
    latest_measurement = measurement_history[-1] if measurement_history else None
   
    if latest_measurement:
        return jsonify({
            'distance': latest_measurement.distance,
            'zone': latest_measurement.zone,
            'quality_score': latest_measurement.quality_score,
            'timestamp': latest_measurement.timestamp.isoformat(),
            'is_stable': latest_measurement.is_stable,
            'sensor_active': sensor_active,
            'thresholds': DISTANCE_THRESHOLDS,
            'buffer_readings': len(STABILITY_BUFFER)
        })
    else:
        return jsonify({'error': 'No measurements available'})

# Include all other existing routes here (get_analytics, get_daily_report, etc.)
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
    stable_count = 0
   
    # Analyze last 100 measurements
    recent_data = list(measurement_history)[-100:]
   
    for measurement in recent_data:
        zone_counts[measurement.zone] += 1
        quality_scores.append(measurement.quality_score)
        recent_measurements.append(measurement.to_dict())
        if getattr(measurement, 'is_stable', False):
            stable_count += 1
   
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
            'measurements_in_analysis': len(recent_data),
            'stable_measurements': stable_count,
            'stability_percentage': round((stable_count / len(recent_data)) * 100, 1) if recent_data else 0
        },
        'zone_distribution': dict(zone_counts),
        'hourly_distribution': dict(hourly_distribution),
        'recent_measurements': recent_measurements[-20:],
        'thresholds': DISTANCE_THRESHOLDS
    })

# Add remaining routes (daily_report, measurement_logs, etc.)
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
    stable_readings = sum(1 for m in daily_measurements if getattr(m, 'is_stable', False))
   
    zone_distribution = defaultdict(int)
    for measurement in daily_measurements:
        zone_distribution[measurement.zone] += 1
   
    # Generate insights
    insights = []
    avg_distance = statistics.mean(distances)
    stability_percentage = (stable_readings / len(daily_measurements)) * 100
   
    insights.append(f"Stability rate: {stability_percentage:.1f}% of readings were stable")
   
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
            'stable_measurements': stable_readings,
            'avg_distance': round(avg_distance, 2),
            'min_distance': round(min(distances), 2),
            'max_distance': round(max(distances), 2),
            'avg_quality': round(quality_avg, 3),
            'stability_percentage': round(stability_percentage, 1)
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
    for measurement in daily_measurements[-100:]:
        logs.append({
            'timestamp': measurement.timestamp.isoformat(),
            'distance': measurement.distance,
            'zone': measurement.zone,
            'quality_score': measurement.quality_score,
            'is_stable': getattr(measurement, 'is_stable', False)
        })
   
    # Calculate averages
    if daily_measurements:
        avg_distance = statistics.mean([m.distance for m in daily_measurements])
        avg_quality = statistics.mean([m.quality_score for m in daily_measurements])
        stable_count = sum(1 for m in daily_measurements if getattr(m, 'is_stable', False))
    else:
        avg_distance = avg_quality = stable_count = 0
   
    return jsonify({
        'logs': logs,
        'total_logs': len(daily_measurements),
        'stable_logs': stable_count,
        'avg_distance': round(avg_distance, 2),
        'avg_quality': round(avg_quality, 3),
        'stability_percentage': round((stable_count / len(daily_measurements)) * 100, 1) if daily_measurements else 0
    })

@app.route('/api/generate_test_data', methods=['POST'])
def generate_test_data():
    """Generate test measurement data with stability indicators"""
    try:
        import random
       
        test_measurements = []
        base_time = datetime.now() - timedelta(hours=2)
       
        for i in range(50):
            if i % 10 == 0:
                distance = random.uniform(5, 15)
            elif i % 7 == 0:
                distance = random.uniform(15, 40)
            elif i % 5 == 0:
                distance = random.uniform(40, 120)
            else:
                distance = random.uniform(120, 300)
           
            quality = random.uniform(0.7, 1.0)
            is_stable = random.choice([True, False]) if i > 5 else False
            timestamp = base_time + timedelta(minutes=i*4)
           
            measurement = DistanceMeasurement(
                distance=round(distance, 2),
                timestamp=timestamp,
                quality_score=round(quality, 3),
                is_stable=is_stable
            )
           
            test_measurements.append(measurement)
            measurement_history.append(measurement)
       
        for measurement in test_measurements:
            update_statistics(measurement.distance)
       
        return jsonify({
            'success': True,
            'message': f'Generated {len(test_measurements)} enhanced test measurements'
        })
       
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/')
def dashboard():
    return send_from_directory('.', 'ultrasonic_sensor.html')

@app.route('/ultrasonic_sensor.html')
def dashboard_html():
    return send_from_directory('.', 'ultrasonic_sensor.html')

@app.route('/api/info')
def api_info():
    return jsonify({
        'message': 'Enhanced Pi 5 Ultrasonic Sensor API (Stable Readings)',
        'status': 'ready',
        'gpio_pins': f'Trig: {TRIG_PIN}, Echo: {ECHO_PIN}',
        'measurement_interval': '4 seconds',
        'pi_model': 'Raspberry Pi 5',
        'gpio_library': 'lgpio (Enhanced)',
        'enhancements': [
            'Advanced noise filtering',
            'Outlier detection and removal',
            'Stability detection',
            'Adaptive smoothing',
            'Multi-sample averaging',
            'Quality scoring'
        ],
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
    try:
        logger.info("Starting Enhanced Pi 5 Ultrasonic Distance Sensor Server...")
        logger.info("Enhanced features: Stability detection, Advanced filtering, Outlier removal")
        logger.info(f"GPIO pins - Trig: {TRIG_PIN}, Echo: {ECHO_PIN}")
        
        # Auto-start sensor when server starts
        if setup_gpio():
            sensor_active = True
            stats_data['start_time'] = datetime.now()
            measurement_thread = threading.Thread(target=continuous_measurement, daemon=True)
            measurement_thread.start()
            logger.info("Sensor auto-started successfully")
        
        app.run(host='0.0.0.0', port=5001, debug=False)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        if sensor_active and gpio_handle:
            sensor_active = False
            lgpio.gpiochip_close(gpio_handle)