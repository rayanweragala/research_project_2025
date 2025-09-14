import os
import sys
import subprocess
import time
import socket
import threading
import signal
from pathlib import Path
from flask import Flask, render_template, jsonify
import requests
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('dashboard.log')
    ]
)
logger = logging.getLogger('Dashboard')

SCRIPT_DIR = Path(__file__).parent.absolute()

def get_local_ip():
    """Get local IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except:
        return "127.0.0.1"

LOCAL_IP = get_local_ip()
logger.info(f"Local IP detected: {LOCAL_IP}")

SERVICES = {
    'face': {
        'name': 'Face Recognition Service',
        'script': 'face_server.py',
        'port': 5000,
        'url': f'http://{LOCAL_IP}:5000'
    },
    'ocr': {
        'name': 'OCR Processing Service',
        'script': 'ocr_server.py',
        'port': 5002,
        'url': f'http://{LOCAL_IP}:5002'
    },
    'ultrasonic': {
        'name': 'Distance Sensor Service',
        'script': 'ultrasonic_sensor.py',
        'port': 5001,
        'url': f'http://{LOCAL_IP}:5001'
    }
}

DASHBOARD_PORT = 3000
DASHBOARD_URL = f'http://{LOCAL_IP}:{DASHBOARD_PORT}'
BASE_DIR = '/opt/research_project'
TEMPLATES_DIR = '/opt/research_project/templates'
STATIC_DIR = '/opt/research_project/static'
service_processes = {}
app = Flask(
    __name__,
    template_folder=TEMPLATES_DIR,
    static_folder=STATIC_DIR
)

log = logging.getLogger('werkzeug')
log.setLevel(logging.WARNING)

class ServiceManager:
    def __init__(self):
        self.services = SERVICES.copy()
        self.processes = {}
        self.shutdown_requested = False

    def check_python_version(self):
        """Check if Python version is compatible"""
        if sys.version_info < (3, 7):
            logger.error("Python 3.7 or higher is required")
            sys.exit(1)
        logger.info(f"Python {sys.version_info.major}.{sys.version_info.minor} verified")

    def check_required_files(self):
        """Check if all required files exist"""
        required_files = ['face_server.py', 'ocr_server.py', 'ultrasonic_sensor.py']
        missing_files = []
        
        for file in required_files:
            file_path = SCRIPT_DIR / file
            if not file_path.exists():
                missing_files.append(file)
        
        if missing_files:
            logger.error(f"Missing required files in {SCRIPT_DIR}: {', '.join(missing_files)}")
            logger.info(f"Current working directory: {Path.cwd()}")
            logger.info(f"Script directory: {SCRIPT_DIR}")
            logger.info("Available files in script directory:")
            for f in SCRIPT_DIR.glob("*.py"):
                logger.info(f"  {f.name}")
            sys.exit(1)
        
        logger.info("All required service files found")

    def check_port_available(self, port):
        """Check if a port is available"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((LOCAL_IP, port))
                return True
        except OSError:
            return False

    def wait_for_service(self, service_name, service_key, url, timeout=30):
        """Wait for a service to become available with better error detection"""
        logger.info(f"Waiting for {service_name} to start...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if service_key in self.processes:
                process = self.processes[service_key]
                if process.poll() is not None:
                    try:
                        stdout, stderr = process.communicate(timeout=5)
                        logger.error(f"{service_name} process died!")
                        logger.error(f"Exit code: {process.returncode}")
                        if stdout:
                            logger.error(f"STDOUT: {stdout.decode()}")
                        if stderr:
                            logger.error(f"STDERR: {stderr.decode()}")
                    except subprocess.TimeoutExpired:
                        logger.error(f"{service_name} process died and communication timed out")
                    return False
            
            try:
                response = requests.get(f"{url}/api/health", timeout=3)
                if response.status_code == 200:
                    logger.info(f"{service_name} is now responding")
                    return True
            except requests.exceptions.ConnectionError:
                logger.debug(f"Connection refused for {service_name}, still waiting...")
            except Exception as e:
                logger.debug(f"Health check error for {service_name}: {e}")
            
            time.sleep(1)
        
        logger.warning(f"{service_name} did not respond within {timeout} seconds")
        return False

    def start_service(self, service_key):
        """Start a single service with enhanced error handling"""
        service = self.services[service_key]
        service_name = service['name']
        script_name = service['script']
        script_path = SCRIPT_DIR / script_name 
        port = service['port']
        
        logger.info(f"Starting {service_name} on {LOCAL_IP}:{port}")
        logger.info(f"Script path: {script_path}")
        logger.info(f"Working directory: {SCRIPT_DIR}")
        logger.info(f"Python executable: {sys.executable}")
        
        if not self.check_port_available(port):
            logger.warning(f"Port {port} is already in use for {service_name}")
            return False
        
        try:
            env = os.environ.copy()
            env['LOCAL_IP'] = LOCAL_IP
            env['PYTHONPATH'] = str(SCRIPT_DIR.parent)  
            
            if 'VIRTUAL_ENV' in os.environ:
                env['VIRTUAL_ENV'] = os.environ['VIRTUAL_ENV']
                logger.info(f"Using virtual environment: {env['VIRTUAL_ENV']}")
            
            python_executable = sys.executable
            logger.info(f"Using Python: {python_executable}")
            
            process = subprocess.Popen([
                python_executable, str(script_path)
            ], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            env=env,
            cwd=str(SCRIPT_DIR)
            )
            
            self.processes[service_key] = process
            logger.info(f"{service_name} started with PID: {process.pid}")
            
            if self.wait_for_service(service_name, service_key, service['url']):
                return True
            else:
                self.stop_service(service_key)
                return False
            
        except Exception as e:
            logger.error(f"Failed to start {service_name}: {str(e)}")
            logger.error(f"Exception type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False
        
    def start_all_services(self):
        """Start all backend services"""
        logger.info("Starting all backend services...")
        
        success_count = 0
        for service_key in self.services.keys():
            if self.start_service(service_key):
                success_count += 1
                time.sleep(2) 
        
        logger.info(f"Started {success_count}/{len(self.services)} services successfully")
        return success_count > 0

    def stop_service(self, service_key):
        """Stop a single service"""
        if service_key in self.processes:
            process = self.processes[service_key]
            service_name = self.services[service_key]['name']
            
            try:
                logger.info(f"Stopping {service_name}...")
                process.terminate()
                
                try:
                    process.wait(timeout=5)
                    logger.info(f"{service_name} stopped gracefully")
                except subprocess.TimeoutExpired:
                    logger.warning(f"Force killing {service_name}")
                    process.kill()
                    process.wait()
                
            except Exception as e:
                logger.error(f"Error stopping {service_name}: {str(e)}")
            finally:
                del self.processes[service_key]

    def stop_all_services(self):
        """Stop all running services"""
        logger.info("Stopping all services...")
        self.shutdown_requested = True
        
        for service_key in list(self.processes.keys()):
            self.stop_service(service_key)
        
        logger.info("All services stopped")

    def check_service_health(self, service_key):
        """Check if a service is healthy"""
        service = self.services[service_key]
        try:
            response = requests.get(f"{service['url']}/api/health", timeout=3)
            return response.status_code == 200
        except:
            return False
        
service_manager = ServiceManager()

@app.route('/')
def dashboard():
    """Serve the main dashboard"""
    return render_template('dashboard_index.html')

@app.route('/api/services/status')
def get_services_status():
    """API endpoint to check all services status"""
    status = {}
    for service_key, service_config in SERVICES.items():
        is_healthy = service_manager.check_service_health(service_key)
        status[service_key] = {
            'status': 'online' if is_healthy else 'offline',
            'name': service_config['name'],
            'port': service_config['port'],
            'url': service_config['url']
        }
    return jsonify(status)

@app.route('/api/system/info')
def get_system_info():
    """Get system information"""
    return jsonify({
        'local_ip': LOCAL_IP,
        'dashboard_port': DASHBOARD_PORT,
        'total_services': len(SERVICES),
        'running_processes': len(service_manager.processes)
    })

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, initiating shutdown...")
    service_manager.stop_all_services()
    sys.exit(0)

def start_dashboard_server():
    """Start the dashboard Flask server"""
    logger.info(f"Starting dashboard server on {DASHBOARD_URL}")
    try:
        app.run(
            host=LOCAL_IP, 
            port=DASHBOARD_PORT, 
            debug=False, 
            use_reloader=False,
            threaded=True
        )
    except Exception as e:
        logger.error(f"Failed to start dashboard server: {str(e)}")

def main():
    """Main startup function"""

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        logger.info("Starting system initialization...")
        service_manager.check_python_version()
        service_manager.check_required_files()
        
        logger.info(f"Current working directory: {os.getcwd()}")
        logger.info(f"Script directory: {SCRIPT_DIR}")
        logger.info(f"Python executable: {sys.executable}")
        logger.info(f"Virtual environment: {os.environ.get('VIRTUAL_ENV', 'None')}")
        logger.info(f"Python path: {sys.path[:3]}...")   
        
        if not service_manager.check_port_available(DASHBOARD_PORT):
            logger.error(f"Dashboard port {DASHBOARD_PORT} is already in use")
            sys.exit(1)
        
        if not service_manager.start_all_services():
            logger.error("Failed to start required services")
            sys.exit(1)
        
        print("\n" + "-" * 60)
        print(f"System Status:")
        print(f"Local IP: {LOCAL_IP}")
        print(f"Dashboard: {DASHBOARD_URL}")
        print("-" * 60)
        print("Service URLs:")
        for service_key, service_config in SERVICES.items():
            print(f"  {service_config['name']}: {service_config['url']}")
        print("-" * 60)
        print("Press Ctrl+C to stop all services")
        print("-" * 60)
        
        start_dashboard_server()
        
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    except Exception as e:
        logger.error(f"Critical error during startup: {str(e)}")
    finally:
        service_manager.stop_all_services()
        logger.info("System shutdown complete")

if __name__ == "__main__":
    main()