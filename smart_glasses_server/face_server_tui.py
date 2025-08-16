#! /usr/bin/env python3
"""Face Server TUI"""

import asyncio
import json
import time
from datetime import datetime,timedelta
from typing import Optional,Dict,List

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import requests
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.live import Live
from rich.columns import Columns
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.status import Status
import threading
import queue
import argparse

class FaceServerTUI:
    def __init__(self, server_url: str = "http://localhost:5000"):
        self.server_url = server_url.rstrip('/')
        self.console = Console()
        self.running = False
        self.data_queue = queue.Queue()
        self.last_update = time.time()
        
        self.server_status = {}
        self.recognition_logs = []
        self.people_list = []
        self.analytics = {}
        self.camera_status = {}
        
        self.refresh_interval = 1.0
        self.log_limit = 20
        
    def check_server_connection(self) -> bool:
        """Test connection to the face recognition server"""
        try:
            response = requests.get(f"{self.server_url}/api/health", timeout=3)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
    
    def fetch_server_data(self):
        """Background thread to fetch data from server"""
        while self.running:
            try:
                try:
                    response = requests.get(f"{self.server_url}/api/health", timeout=2)
                    if response.status_code == 200:
                        self.server_status = response.json()
                except:
                    self.server_status = {"status": "disconnected"}
                
                try:
                    response = requests.get(f"{self.server_url}/api/people", timeout=2)
                    if response.status_code == 200:
                        self.people_list = response.json().get("people", [])
                except:
                    pass
                
                try:
                    response = requests.get(f"{self.server_url}/api/analytics_enhanced", timeout=2)
                    if response.status_code == 200:
                        self.analytics = response.json()
                except:
                    pass
                
                try:
                    today = datetime.now().strftime('%Y-%m-%d')
                    response = requests.get(f"{self.server_url}/api/recognition_logs?date={today}", timeout=2)
                    if response.status_code == 200:
                        logs = response.json().get("logs", [])
                        self.recognition_logs = logs[-self.log_limit:] if logs else []
                except:
                    pass
                
                self.last_update = time.time()
                
            except Exception as e:
                pass  
            
            time.sleep(self.refresh_interval)
    
    def create_server_status_panel(self) -> Panel:
        """Create server status panel"""
        status = self.server_status
        
        if not status or status.get("status") == "disconnected":
            content = Text("SERVER DISCONNECTED", style="bold red")
            content.append(f"\nLast attempt: {datetime.now().strftime('%H:%M:%S')}")
            return Panel(content, title="Server Status", border_style="red")
        
        lines = []
        lines.append(f"Status: {status.get('status', 'unknown').upper()}")
        lines.append(f"Model Loaded: {'YES' if status.get('model_loaded') else 'NO'}")
        lines.append(f"People Count: {len(self.people_list)}")
        lines.append(f"Camera: {'ACTIVE' if status.get('camera_active') else 'INACTIVE'}")
        lines.append(f"Camera Mode: {status.get('camera_mode', 'None')}")
        lines.append(f"Cache Size: {status.get('cache_size', 0)}")
        
        content = Text("\n".join(lines))
        
        style = "green" if status.get("status") == "healthy" else "yellow"
        return Panel(content, title="Server Status", border_style=style)
    
    def create_recognition_stats_panel(self) -> Panel:
        """Create recognition statistics panel"""
        stats = self.server_status.get("recognition_stats", {})
        
        if not stats:
            content = Text("No statistics available", style="dim")
            return Panel(content, title="Recognition Stats")
        
        lines = []
        lines.append(f"Total Requests: {stats.get('total_requests', 0)}")
        lines.append(f"Successful: {stats.get('successful_recognitions', 0)}")
        lines.append(f"Cache Hits: {stats.get('cache_hits', 0)}")
        lines.append(f"Errors: {stats.get('errors', 0)}")
        lines.append(f"Avg Processing: {stats.get('avg_processing_time', 0):.3f}s")
        
        total = stats.get('total_requests', 0)
        successful = stats.get('successful_recognitions', 0)
        if total > 0:
            success_rate = (successful / total) * 100
            lines.append(f"Success Rate: {success_rate:.1f}%")
        
        content = Text("\n".join(lines))
        return Panel(content, title="Recognition Stats")
    
    def create_people_panel(self) -> Panel:
        """Create registered people panel"""
        if not self.people_list:
            content = Text("No people registered", style="dim")
            return Panel(content, title="Registered People")
        
        table = Table(show_header=True, header_style="bold blue")
        table.add_column("Name", width=20)
        table.add_column("Photos", width=8)
        table.add_column("Avg Quality", width=12)
        table.add_column("Registered", width=12)
        
        for person in self.people_list[-10:]: 
            name = person.get("name", "Unknown")
            photo_count = str(person.get("photo_count", 0))
            avg_quality = f"{person.get('avg_quality', 0):.3f}"
            created = person.get("created_at", "")
            
            if created:
                try:
                    dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                    created = dt.strftime("%m-%d %H:%M")
                except:
                    created = created[:10]
            
            table.add_row(name, photo_count, avg_quality, created)
        
        return Panel(table, title=f"Registered People ({len(self.people_list)})")
    
    def create_recent_logs_panel(self) -> Panel:
        """Create recent recognition logs panel"""
        if not self.recognition_logs:
            content = Text("No recent recognitions", style="dim")
            return Panel(content, title="Recent Recognitions")
        
        table = Table(show_header=True, header_style="bold green")
        table.add_column("Time", width=8)
        table.add_column("Person", width=15)
        table.add_column("Confidence", width=10)
        table.add_column("Quality", width=8)
        table.add_column("Method", width=12)
        
        for log in reversed(self.recognition_logs[-10:]):
            timestamp = log.get("timestamp", "")
            person = log.get("person_name", "Unknown")
            confidence = f"{log.get('confidence', 0):.3f}"
            quality = f"{log.get('quality_score', 0):.3f}"
            method = log.get("method_used", "standard")
            
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    time_str = dt.strftime("%H:%M:%S")
                except:
                    time_str = timestamp[-8:] if len(timestamp) >= 8 else timestamp
            else:
                time_str = ""
            
            conf_float = float(confidence)
            if conf_float >= 0.8:
                conf_style = "green"
            elif conf_float >= 0.6:
                conf_style = "yellow"
            else:
                conf_style = "red"
            
            table.add_row(
                time_str,
                person[:15],
                Text(confidence, style=conf_style),
                quality,
                method[:12]
            )
        
        return Panel(table, title=f"Recent Recognitions ({len(self.recognition_logs)})")
    
    def create_camera_panel(self) -> Panel:
        """Create camera status panel"""
        status = self.server_status
        
        lines = []
        lines.append(f"Active: {'YES' if status.get('camera_active') else 'NO'}")
        lines.append(f"Mode: {status.get('camera_mode', 'None')}")
        
        if status.get('camera_error'):
            lines.append(f"Error: {status['camera_error']}")
            style = "red"
        elif status.get('camera_active'):
            style = "green"
        else:
            style = "yellow"
        
        content = Text("\n".join(lines))
        return Panel(content, title="Camera Status", border_style=style)
    
    def create_actions_panel(self) -> Panel:
        """Create available actions panel"""
        actions = [
            "q - Quit",
            "r - Refresh now",
            "c - Start camera",
            "s - Stop camera",
            "p - List people",
            "l - View logs",
            "h - Show help"
        ]
        
        content = Text("\n".join(actions))
        return Panel(content, title="Controls")
    
    def create_layout(self) -> Layout:
        """Create the main layout"""
        layout = Layout()
        
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body")
        )
        
        header_text = Text("Face Recognition Server Monitor", style="bold blue")
        last_update_str = datetime.fromtimestamp(self.last_update).strftime("%H:%M:%S")
        header_text.append(f" | Last Update: {last_update_str}", style="dim")
        layout["header"].update(Panel(header_text, border_style="blue"))
        
        layout["body"].split_row(
            Layout(name="left", ratio=2),
            Layout(name="right", ratio=1)
        )
        
        layout["left"].split_column(
            Layout(name="top"),
            Layout(name="middle"),
            Layout(name="bottom")
        )
        
        layout["top"].split_row(
            Layout(self.create_server_status_panel()),
            Layout(self.create_recognition_stats_panel())
        )
        
        layout["middle"].split_row(
            Layout(self.create_people_panel()),
            Layout(self.create_camera_panel())
        )
        
        layout["bottom"].update(self.create_recent_logs_panel())
        
        layout["right"].update(self.create_actions_panel())
        
        return layout
    
    def handle_input(self, key: str):
        """Handle keyboard input"""
        if key.lower() == 'q':
            self.running = False
            return
        
        elif key.lower() == 'r':
            pass
        
        elif key.lower() == 'c':
            try:
                requests.post(f"{self.server_url}/api/camera/start", timeout=5)
                self.console.print("Camera start command sent", style="green")
            except:
                self.console.print("Failed to start camera", style="red")
        
        elif key.lower() == 's':
            try:
                requests.post(f"{self.server_url}/api/camera/stop", timeout=5)
                self.console.print("Camera stop command sent", style="yellow")
            except:
                self.console.print("Failed to stop camera", style="red")
        
        elif key.lower() == 'p':
            self.show_people_details()
        
        elif key.lower() == 'l':
            self.show_detailed_logs()
        
        elif key.lower() == 'h':
            self.show_help()
    
    def show_people_details(self):
        """Show detailed people information"""
        self.console.clear()
        self.console.print("Registered People Details", style="bold blue")
        self.console.print("=" * 50)
        
        if not self.people_list:
            self.console.print("No people registered", style="dim")
        else:
            for person in self.people_list:
                self.console.print(f"\nName: {person.get('name', 'Unknown')}")
                self.console.print(f"  Photos: {person.get('photo_count', 0)}")
                self.console.print(f"  Average Quality: {person.get('avg_quality', 0):.3f}")
                self.console.print(f"  Best Quality: {person.get('best_quality', 0):.3f}")
                self.console.print(f"  Registered: {person.get('created_at', 'Unknown')}")
        
        self.console.print("\nPress any key to return...")
        input()
    
    def show_detailed_logs(self):
        """Show detailed recognition logs"""
        self.console.clear()
        self.console.print("Recent Recognition Logs", style="bold green")
        self.console.print("=" * 70)
        
        if not self.recognition_logs:
            self.console.print("No recent recognitions", style="dim")
        else:
            for log in reversed(self.recognition_logs[-20:]):
                timestamp = log.get("timestamp", "")
                person = log.get("person_name", "Unknown")
                confidence = log.get("confidence", 0)
                quality = log.get("quality_score", 0)
                method = log.get("method_used", "standard")
                proc_time = log.get("processing_time", 0)
                
                if timestamp:
                    try:
                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        time_str = dt.strftime("%H:%M:%S")
                    except:
                        time_str = timestamp
                else:
                    time_str = "Unknown"
                
                if confidence >= 0.8:
                    style = "green"
                elif confidence >= 0.6:
                    style = "yellow"
                else:
                    style = "red"
                
                self.console.print(f"\n[{time_str}] ", end="")
                self.console.print(f"{person}", style="bold", end="")
                self.console.print(f" | Confidence: ", end="")
                self.console.print(f"{confidence:.3f}", style=style, end="")
                self.console.print(f" | Quality: {quality:.3f} | Method: {method} | Time: {proc_time:.3f}s")
        
        self.console.print("\nPress any key to return...")
        input()
    
    def show_help(self):
        """Show help information"""
        self.console.clear()
        self.console.print("Face Recognition Server TUI - Help", style="bold blue")
        self.console.print("=" * 40)
        
        help_text = """
Controls:
  q - Quit the application
  r - Force refresh data
  c - Start camera
  s - Stop camera
  p - Show detailed people list
  l - Show detailed recognition logs
  h - Show this help

Server URL: """ + self.server_url + """

The interface automatically refreshes every second with live data from the server.

Panels:
- Server Status: Shows connection status, model state, and basic info
- Recognition Stats: Shows performance metrics and success rates
- Registered People: Shows list of people in the database
- Camera Status: Shows current camera state
- Recent Recognitions: Shows latest recognition attempts
- Controls: Available keyboard shortcuts

Colors:
- Green: Good/Active/High confidence
- Yellow: Warning/Medium confidence
- Red: Error/Low confidence
"""
        
        self.console.print(help_text)
        self.console.print("\nPress any key to return...")
        input()
    
    def run(self):
        """Run the TUI application"""
        if not self.check_server_connection():
            self.console.print(f"Cannot connect to server at {self.server_url}", style="bold red")
            self.console.print("Please check that the server is running and accessible.")
            return
        
        self.console.print(f"Connected to Face Recognition Server at {self.server_url}", style="green")
        time.sleep(1)
        
        self.running = True
        
        data_thread = threading.Thread(target=self.fetch_server_data, daemon=True)
        data_thread.start()
        
        time.sleep(0.5)
        
        try:
            with Live(self.create_layout(), refresh_per_second=1, screen=True) as live:
                while self.running:
                    live.update(self.create_layout())
                    
                    import select
                    import sys
                    
                    if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
                        key = sys.stdin.read(1)
                        if key:
                            self.handle_input(key)
                    
                    time.sleep(0.1)
                    
        except KeyboardInterrupt:
            pass
        
        self.running = False
        self.console.print("\nTUI stopped.", style="yellow")

def main():
    parser = argparse.ArgumentParser(description="Face Recognition Server TUI Monitor")
    parser.add_argument(
        "--server",
        default="http://localhost:5000",
        help="Server URL (default: http://localhost:5000)"
    )
    parser.add_argument(
        "--refresh",
        type=float,
        default=1.0,
        help="Refresh interval in seconds (default: 1.0)"
    )
    
    args = parser.parse_args()
    
    console = Console()
    console.print("Face Recognition Server TUI", style="bold blue")
    console.print(f"Server: {args.server}")
    console.print("Press 'h' for help, 'q' to quit\n")
    
    tui = FaceServerTUI(args.server)
    tui.refresh_interval = args.refresh
    tui.run()

if __name__ == "__main__":
    main()