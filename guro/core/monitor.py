import psutil
import platform
import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
import os
import time
from collections import deque
import threading
import subprocess
from typing import Dict, List, Optional
import shutil
from rich import box
import click
import csv

class GPUDetector:
    @staticmethod
    def get_nvidia_info():
        try:
            nvidia_smi = "nvidia-smi"
            output = subprocess.check_output([nvidia_smi, "--query-gpu=gpu_name,memory.total,memory.used,memory.free,temperature.gpu,utilization.gpu,fan.speed,power.draw", "--format=csv,noheader,nounits"], 
                                          universal_newlines=True)
            lines = output.strip().split('\n')
            gpus = []
            for line in lines:
                name, total, used, free, temp, util, fan, power = line.split(',')
                gpus.append({
                    'name': name.strip(),
                    'memory_total': float(total) * 1024**2,
                    'memory_used': float(used) * 1024**2,
                    'memory_free': float(free) * 1024**2,
                    'temperature': float(temp),
                    'utilization': float(util),
                    'fan_speed': float(fan) if fan.strip() != '[N/A]' else None,
                    'power_draw': float(power) if power.strip() != '[N/A]' else None,
                    'type': 'NVIDIA'
                })
            return gpus
        except:
            return []

    @staticmethod
    def get_amd_info():
        try:
            rocm_smi = "rocm-smi"
            output = subprocess.check_output([rocm_smi, "--showuse", "--showmeminfo", "--showtemp"], 
                                          universal_newlines=True)
            gpus = []
            lines = output.strip().split('\n')
            current_gpu = {}
            for line in lines:
                if 'GPU' in line and 'Card' in line:
                    if current_gpu:
                        gpus.append(current_gpu)
                    current_gpu = {'type': 'AMD'}
                if 'GPU Memory Use' in line:
                    try:
                        used = float(line.split(':')[1].strip().split()[0]) * 1024**2
                        current_gpu['memory_used'] = used
                    except:
                        pass
                if 'Total GPU Memory' in line:
                    try:
                        total = float(line.split(':')[1].strip().split()[0]) * 1024**2
                        current_gpu['memory_total'] = total
                        current_gpu['memory_free'] = total - current_gpu.get('memory_used', 0)
                    except:
                        pass
                if 'Temperature' in line:
                    try:
                        temp = float(line.split(':')[1].strip().split()[0])
                        current_gpu['temperature'] = temp
                    except:
                        pass
            if current_gpu:
                gpus.append(current_gpu)
            return gpus
        except:
            return []

    @staticmethod
    def get_all_gpus():
        gpu_info = {
            'available': False,
            'gpus': []
        }
        
        nvidia_gpus = GPUDetector.get_nvidia_info()
        amd_gpus = GPUDetector.get_amd_info()
        
        all_gpus = nvidia_gpus + amd_gpus
        
        if all_gpus:
            gpu_info['available'] = True
            gpu_info['gpus'] = all_gpus
            
        return gpu_info

class ASCIIGraph:
    def __init__(self, width=70, height=10):
        self.width = width
        self.height = height
        self.data = deque(maxlen=width)
        self.chars = ' ▁▂▃▄▅▆▇█'

    def add_point(self, value):
        self.data.append(value)

    def render(self, title=""):
        if not self.data:
            return ""

        # Normalize data
        max_val = max(self.data)
        if max_val == 0:
            normalized = [0] * len(self.data)
        else:
            normalized = [min(int((val / max_val) * (len(self.chars) - 1)), len(self.chars) - 1) 
                         for val in self.data]

        # Generate graph
        lines = []
        lines.append("╔" + "═" * (self.width + 2) + "╗")
        lines.append("║ " + title.center(self.width) + " ║")
        lines.append("║ " + "─" * self.width + " ║")

        graph_str = ""
        for val in normalized:
            graph_str += self.chars[val]
        lines.append("║ " + graph_str.ljust(self.width) + " ║")
        
        lines.append("╚" + "═" * (self.width + 2) + "╝")
        return "\n".join(lines)

class SystemMonitor:
    def __init__(self):
        self.console = Console()
        self.cpu_graph = ASCIIGraph()
        self.memory_graph = ASCIIGraph()
        self.monitoring_data = []
        
    def _get_cpu_temperature(self):
        if platform.system() == 'Linux':
            try:
                temp_file = '/sys/class/thermal/thermal_zone0/temp'
                if os.path.exists(temp_file):
                    with open(temp_file, 'r') as f:
                        return float(f.read()) / 1000.0
            except:
                pass
        return None

    def get_system_info(self):
        cpu_freq = psutil.cpu_freq()
        memory = psutil.virtual_memory()
        
        system_info = {
            'os': f"{platform.system()} {platform.release()}",
            'cpu_model': platform.processor(),
            'cpu_cores': psutil.cpu_count(),
            'cpu_threads': psutil.cpu_count(logical=True),
            'cpu_freq': f"{cpu_freq.current:.2f}MHz" if cpu_freq else "N/A",
            'memory_total': f"{memory.total / (1024**3):.2f}GB",
            'memory_available': f"{memory.available / (1024**3):.2f}GB",
        }
        
        temp = self._get_cpu_temperature()
        if temp:
            system_info['cpu_temp'] = f"{temp:.1f}°C"
            
        return system_info

    def export_monitoring_data(self):
        if not self.monitoring_data:
            return
        
        with open('monitoring_data.csv', 'w', newline='') as csvfile:
            fieldnames = ['timestamp', 'cpu_usage', 'memory_usage']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for data in self.monitoring_data:
                writer.writerow(data)

    def run_performance_test(self, interval: float = 1.0, duration: Optional[int] = 30, export_data: bool = False):
        self.console.clear()
        self.console.print(Panel.fit(
            "[bold cyan]Welcome to System Performance Monitor[/bold cyan]\n" +
            f"[yellow]Running performance test for {duration if duration else 'unlimited'} seconds...[/yellow]",
            box=box.DOUBLE
        ))
        
        # System Information
        sys_info = self.get_system_info()
        sys_table = Table(title="System Information", box=box.HEAVY)
        sys_table.add_column("Component", style="cyan")
        sys_table.add_column("Details", style="green")
        
        for key, value in sys_info.items():
            sys_table.add_row(key.replace('_', ' ').title(), str(value))
        
        self.console.print(sys_table)
        self.console.print("")
        
        # GPU Information
        gpu_info = GPUDetector.get_all_gpus()
        if gpu_info['available']:
            gpu_table = Table(title="GPU Information", box=box.HEAVY)
            gpu_table.add_column("Metric", style="cyan")
            gpu_table.add_column("Value", style="green")
            
            for i, gpu in enumerate(gpu_info['gpus']):
                gpu_table.add_row(f"GPU {i} Type", gpu.get('type', 'Unknown'))
                gpu_table.add_row(f"GPU {i} Name", gpu.get('name', 'Unknown'))
                if gpu.get('memory_total'):
                    gpu_table.add_row(f"Memory Total", f"{gpu['memory_total'] / (1024**3):.2f} GB")
                if gpu.get('temperature'):
                    gpu_table.add_row(f"Temperature", f"{gpu['temperature']}°C")
            
            self.console.print(gpu_table)
            self.console.print("")
        
        # Performance Test
        start_time = time.time()
        try:
            while True:
                current_time = time.time()
                if duration and (current_time - start_time >= duration):
                    break
                
                cpu_percent = psutil.cpu_percent()
                memory_percent = psutil.virtual_memory().percent
                
                self.cpu_graph.add_point(cpu_percent)
                self.memory_graph.add_point(memory_percent)
                
                if export_data:
                    self.monitoring_data.append({
                        'timestamp': datetime.datetime.now().isoformat(),
                        'cpu_usage': cpu_percent,
                        'memory_usage': memory_percent
                    })
                
                self.console.clear()
                self.console.print(Panel.fit(
                    f"[bold cyan]Performance Test Progress: {int(current_time - start_time)}s{f'/{duration}s' if duration else ''}[/bold cyan]",
                    box=box.DOUBLE
                ))
                
                self.console.print(self.cpu_graph.render(f"CPU Usage: {cpu_percent:.1f}%"))
                self.console.print("")
                self.console.print(self.memory_graph.render(f"Memory Usage: {memory_percent:.1f}%"))
                
                time.sleep(interval)
        
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Monitoring stopped by user[/yellow]")
        
        # Final Summary
        self.console.clear()
        summary_table = Table(title="Performance Test Summary", box=box.HEAVY)
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Average", style="green")
        summary_table.add_column("Maximum", style="red")
        
        cpu_values = list(self.cpu_graph.data)
        mem_values = list(self.memory_graph.data)
        
        if cpu_values:
            summary_table.add_row(
                "CPU Usage",
                f"{sum(cpu_values) / len(cpu_values):.1f}%",
                f"{max(cpu_values):.1f}%"
            )
        if mem_values:
            summary_table.add_row(
                "Memory Usage",
                f"{sum(mem_values) / len(mem_values):.1f}%",
                f"{max(mem_values):.1f}%"
            )
        
        self.console.print(Panel.fit(
            "[bold green]Performance Test Completed![/bold green]",
            box=box.DOUBLE
        ))
        self.console.print(summary_table)
        
        # Final Graphs
        self.console.print(self.cpu_graph.render("CPU Usage History"))
        self.console.print("")
        self.console.print(self.memory_graph.render("Memory Usage History"))
        
        if export_data:
            self.export_monitoring_data()
            self.console.print("\n[green]Monitoring data exported to 'monitoring_data.csv'[/green]")

@click.group()
def cli():
    """🖥️ System Performance Monitor CLI"""
    pass
# import psutil
# import platform
# import datetime
# from rich.console import Console
# from rich.table import Table
# from rich.panel import Panel
# from rich.layout import Layout
# import os
# import time
# from collections import deque
# import threading
# import subprocess
# from typing import Dict, List, Optional
# import shutil
# from rich import box
# import keyboard
# import sys
# import select
# import matplotlib.pyplot as plt
# import numpy as np

# class InputHandler:
#     def __init__(self):
#         self.should_exit = False
#         self._thread = None

#     def start(self):
#         if os.name == 'nt':  # Windows
#             self._thread = threading.Thread(target=self._windows_input)
#         else:  # Unix-like systems
#             self._thread = threading.Thread(target=self._unix_input)
#         self._thread.daemon = True
#         self._thread.start()

#     def _windows_input(self):
#         try:
#             while not self.should_exit:
#                 if keyboard.is_pressed('q'):
#                     self.should_exit = True
#         except:
#             pass

#     def _unix_input(self):
#         try:
#             while not self.should_exit:
#                 if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
#                     line = sys.stdin.readline()
#                     if line.strip().lower() == 'q':
#                         self.should_exit = True
#         except:
#             pass

# class GPUDetector:
#     @staticmethod
#     def get_nvidia_info():
#         try:
#             nvidia_smi = "nvidia-smi"
#             try:
#                 output = subprocess.check_output([nvidia_smi, "--query-gpu=gpu_name,memory.total,memory.used,memory.free,temperature.gpu,utilization.gpu,fan.speed,power.draw", "--format=csv,noheader,nounits"], 
#                                               universal_newlines=True)
#                 lines = output.strip().split('\n')
#                 gpus = []
#                 for line in lines:
#                     name, total, used, free, temp, util, fan, power = line.split(',')
#                     gpus.append({
#                         'name': name.strip(),
#                         'memory_total': float(total) * 1024**2,
#                         'memory_used': float(used) * 1024**2,
#                         'memory_free': float(free) * 1024**2,
#                         'temperature': float(temp),
#                         'utilization': float(util),
#                         'fan_speed': float(fan) if fan.strip() != '[N/A]' else None,
#                         'power_draw': float(power) if power.strip() != '[N/A]' else None,
#                         'type': 'NVIDIA'
#                     })
#                 return gpus
#             except subprocess.CalledProcessError:
#                 return []
#         except:
#             return []

#     @staticmethod
#     def get_amd_info():
#         try:
#             # Try rocm-smi for AMD GPUs
#             rocm_smi = "rocm-smi"
#             try:
#                 output = subprocess.check_output([rocm_smi, "--showuse", "--showmeminfo", "--showtemp"], 
#                                               universal_newlines=True)
#                 gpus = []
#                 # Parse rocm-smi output
#                 lines = output.strip().split('\n')
#                 current_gpu = {}
#                 for line in lines:
#                     if 'GPU' in line and 'Card' in line:
#                         if current_gpu:
#                             gpus.append(current_gpu)
#                         current_gpu = {'type': 'AMD'}
#                     if 'GPU Memory Use' in line:
#                         try:
#                             used = float(line.split(':')[1].strip().split()[0]) * 1024**2
#                             current_gpu['memory_used'] = used
#                         except:
#                             pass
#                     if 'Total GPU Memory' in line:
#                         try:
#                             total = float(line.split(':')[1].strip().split()[0]) * 1024**2
#                             current_gpu['memory_total'] = total
#                             current_gpu['memory_free'] = total - current_gpu.get('memory_used', 0)
#                         except:
#                             pass
#                     if 'Temperature' in line:
#                         try:
#                             temp = float(line.split(':')[1].strip().split()[0])
#                             current_gpu['temperature'] = temp
#                         except:
#                             pass
#                 if current_gpu:
#                     gpus.append(current_gpu)
#                 return gpus
#             except subprocess.CalledProcessError:
#                 return []
#         except:
#             return []

#     @staticmethod
#     def get_intel_info():
#         try:
#             # Try intel_gpu_top for Intel GPUs
#             output = subprocess.check_output(['intel_gpu_top', '-J'], universal_newlines=True)
#             gpus = []
#             # Parse intel_gpu_top JSON output
#             import json
#             data = json.loads(output)
#             if 'engines' in data:
#                 gpu = {
#                     'name': 'Intel GPU',
#                     'type': 'Intel',
#                     'utilization': data.get('engines', {}).get('total', 0),
#                     'temperature': None,  # Intel GPU top doesn't provide temperature
#                     'memory_total': None,  # These would need to be obtained through other means
#                     'memory_used': None,
#                     'memory_free': None
#                 }
#                 gpus.append(gpu)
#             return gpus
#         except:
#             return []

#     @staticmethod
#     def get_all_gpus():
#         gpu_info = {
#             'available': False,
#             'gpus': []
#         }
        
#         # Collect info from all GPU types
#         nvidia_gpus = GPUDetector.get_nvidia_info()
#         amd_gpus = GPUDetector.get_amd_info()
#         intel_gpus = GPUDetector.get_intel_info()
        
#         all_gpus = nvidia_gpus + amd_gpus + intel_gpus
        
#         if all_gpus:
#             gpu_info['available'] = True
#             gpu_info['gpus'] = all_gpus
            
#         return gpu_info

# class CLIGraph:
#     def __init__(self, width=70, height=15):
#         self.width = width
#         self.height = height
#         self.graph_chars = ' ▁▂▃▄▅▆▇█'

#     def generate_graph(self, data: list, title: str = "") -> str:
#         if not data:
#             return ""

#         # Normalize data to fit height
#         max_val = max(data)
#         if max_val == 0:
#             normalized = [0] * len(data)
#         else:
#             normalized = [min(int((val / max_val) * (len(self.graph_chars) - 1)), len(self.graph_chars) - 1) 
#                          for val in data]

#         # Generate graph
#         graph = [title.center(self.width) if title else ""]
#         graph.append("┌" + "─" * (self.width - 2) + "┐")

#         # Add data points
#         graph_str = ""
#         for val in normalized[-self.width+2:]:  # Only show last width-2 points
#             graph_str += self.graph_chars[val]

#         graph.append("│" + graph_str.ljust(self.width - 2) + "│")
#         graph.append("└" + "─" * (self.width - 2) + "┘")

#         return "\n".join(graph)

# class PerformanceHistory:
#     def __init__(self, max_points=100):
#         self.max_points = max_points
#         self.cpu_history = deque(maxlen=max_points)
#         self.memory_history = deque(maxlen=max_points)
#         self.gpu_histories = {}  # Dictionary to store histories for multiple GPUs
#         terminal_size = shutil.get_terminal_size()
#         self.cli_graph = CLIGraph(width=min(70, terminal_size.columns - 10))

#     def update(self, cpu_percent, memory_percent, gpu_info=None):
#         self.cpu_history.append(cpu_percent)
#         self.memory_history.append(memory_percent)
        
#         if gpu_info and gpu_info['available']:
#             for i, gpu in enumerate(gpu_info['gpus']):
#                 if i not in self.gpu_histories:
#                     self.gpu_histories[i] = deque(maxlen=self.max_points)
#                 self.gpu_histories[i].append(gpu.get('utilization', 0))

#     def generate_graphs(self) -> str:
#         graphs = []
        
#         # CPU Usage Graph
#         cpu_graph = self.cli_graph.generate_graph(
#             list(self.cpu_history),
#             "CPU Usage (%)"
#         )
#         graphs.append(cpu_graph)
        
#         # Memory Usage Graph
#         memory_graph = self.cli_graph.generate_graph(
#             list(self.memory_history),
#             "Memory Usage (%)"
#         )
#         graphs.append(memory_graph)
        
#         # GPU Usage Graphs
#         for gpu_id, gpu_history in self.gpu_histories.items():
#             gpu_graph = self.cli_graph.generate_graph(
#                 list(gpu_history),
#                 f"GPU {gpu_id} Usage (%)"
#             )
#             graphs.append(gpu_graph)
        
#         return "\n".join(graphs)

# class SystemMonitor:
#     def __init__(self):
#         self.console = Console()
#         self.history = PerformanceHistory()
#         self.running = True
#         self.collector_thread = threading.Thread(target=self._collect_data)
#         self.collector_thread.daemon = True
#         self.input_handler = InputHandler()
#         self.metrics = {
#             'cpu_usage': [],
#             'memory_usage': [],
#             'timestamps': []
#         }

#     def _collect_data(self):
#         while self.running:
#             cpu_percent = psutil.cpu_percent()
#             memory_percent = psutil.virtual_memory().percent
#             gpu_info = GPUDetector.get_all_gpus()
            
#             self.history.update(cpu_percent, memory_percent, gpu_info)
#             time.sleep(1)

#     def get_cpu_info(self):
#         cpu_freq = psutil.cpu_freq()
#         cpu_info = {
#             'percent': psutil.cpu_percent(interval=1, percpu=True),
#             'freq_current': cpu_freq.current if cpu_freq else 0,
#             'freq_max': cpu_freq.max if cpu_freq else 0,
#             'cores': psutil.cpu_count(),
#             'threads': psutil.cpu_count(logical=True),
#             'temperature': self._get_cpu_temperature()
#         }
        
#         # Get thread information
#         thread_info = []
#         for proc in psutil.process_iter(['pid', 'name', 'num_threads']):
#             try:
#                 thread_info.append({
#                     'pid': proc.info['pid'],
#                     'name': proc.info['name'],
#                     'threads': proc.info['num_threads']
#                 })
#             except (psutil.NoSuchProcess, psutil.AccessDenied):
#                 pass
        
#         cpu_info['thread_info'] = sorted(thread_info, key=lambda x: x['threads'], reverse=True)[:5]
#         return cpu_info

#     def _get_cpu_temperature(self):
#         if platform.system() == 'Linux':
#             try:
#                 # For Raspberry Pi and other Linux systems
#                 temp_file = '/sys/class/thermal/thermal_zone0/temp'
#                 if os.path.exists(temp_file):
#                     with open(temp_file, 'r') as f:
#                         return float(f.read()) / 1000.0
#             except:
#                 pass
#         return None

#     def get_memory_info(self):
#         memory = psutil.virtual_memory()
#         swap = psutil.swap_memory()
#         return {
#             'total': memory.total,
#             'available': memory.available,
#             'percent': memory.percent,
#             'used': memory.used,
#             'swap_total': swap.total,
#             'swap_used': swap.used,
#             'swap_percent': swap.percent
#         }

#     def discover_devices(self):
#         system_info = {
#             'os': platform.system() + ' ' + platform.release(),
#             'cpu': platform.processor(),
#             'memory': f"{round(psutil.virtual_memory().total / (1024**3), 2)} GB",
#             'gpus': GPUDetector.get_all_gpus()['gpus'] if GPUDetector.get_all_gpus()['available'] else "No GPU detected"
#         }
#         return system_info

#     def collect_metrics(self, duration=30):
#         self.console.print(Panel.fit(
#             "[bold yellow]Running performance test for 30 seconds...[/bold yellow]",
#             box=box.ROUNDED
#         ))
        
#         start_time = time.time()
#         while time.time() - start_time < duration:
#             self.metrics['cpu_usage'].append(psutil.cpu_percent())
#             self.metrics['memory_usage'].append(psutil.virtual_memory().percent)
#             self.metrics['timestamps'].append(time.time() - start_time)
#             time.sleep(1)

#     def plot_metrics(self):
#         plt.figure(figsize=(12, 6))
        
#         plt.subplot(1, 2, 1)
#         plt.plot(self.metrics['timestamps'], self.metrics['cpu_usage'])
#         plt.title('CPU Usage Over Time')
#         plt.xlabel('Time (s)')
#         plt.ylabel('CPU Usage (%)')
        
#         plt.subplot(1, 2, 2)
#         plt.plot(self.metrics['timestamps'], self.metrics['memory_usage'])
#         plt.title('Memory Usage Over Time')
#         plt.xlabel('Time (s)')
#         plt.ylabel('Memory Usage (%)')
        
#         plt.tight_layout()
#         plt.savefig('system_metrics.png')

#     def display_system_info(self):
#         if not self.collector_thread.is_alive():
#             self.collector_thread.start()

#         # Initial instruction message
#         self.console.print(Panel.fit(
#             "[bold yellow]Press 'q' and Enter to exit (or just 'q' on Windows)[/bold yellow]",
#             box=box.ROUNDED
#         ))

#         self.input_handler.start()

#         while self.running:
#             try:
#                 self.console.clear()
                
#                 # Display performance graphs
#                 self.console.print(self.history.generate_graphs())
                
#                 # CPU Information
#                 cpu_info = self.get_cpu_info()
#                 cpu_table = Table(title="CPU Information", show_header=True, header_style="bold magenta")
#                 cpu_table.add_column("Metric", style="cyan")
#                 cpu_table.add_column("Value", style="green")
                
#                 cpu_table.add_row("Cores/Threads", f"{cpu_info['cores']}/{cpu_info['threads']}")
#                 cpu_table.add_row("Current Frequency", f"{cpu_info['freq_current']:.2f} MHz")
#                 cpu_table.add_row("Max Frequency", f"{cpu_info['freq_max']:.2f} MHz")
#                 if cpu_info['temperature']:
#                     cpu_table.add_row("Temperature", f"{cpu_info['temperature']:.1f}°C")

#                 # GPU Information
#                 gpu_info = GPUDetector.get_all_gpus()
#                 if gpu_info['available']:
#                     gpu_table = Table(title="GPU Information", show_header=True, header_style="bold magenta")
#                     gpu_table.add_column("Metric", style="cyan")
#                     gpu_table.add_column("Value", style="green")
                    
#                     for i, gpu in enumerate(gpu_info['gpus']):
#                         gpu_table.add_row(f"GPU {i} Type", gpu.get('type', 'Unknown'))
#                         gpu_table.add_row(f"GPU {i} Name", gpu.get('name', 'Unknown'))
#                         if gpu.get('memory_total'):
#                             gpu_table.add_row(f"Memory Total", f"{gpu['memory_total'] / (1024**3):.2f} GB")
#                         if gpu.get('memory_used'):
#                             gpu_table.add_row(f"Memory Used", f"{gpu['memory_used'] / (1024**3):.2f} GB")
#                         if gpu.get('temperature'):
#                             gpu_table.add_row(f"Temperature", f"{gpu['temperature']}°C")
#                         if gpu.get('power_draw'):
#                             gpu_table.add_row(f"Power Usage", f"{gpu['power_draw']:.2f} W")
#                         if gpu.get('fan_speed'):
#                             gpu_table.add_row(f"Fan Speed", f"{gpu['fan_speed']}%")
#                 else:
#                     self.console.print(Panel.fit(
#                         "[bold red]GPU not available/found in this system[/bold red]",
#                         box=box.ROUNDED
#                     ))

#                 # Thread Information
#                 thread_table = Table(title="Top Processes by Thread Count", show_header=True, header_style="bold magenta")
#                 thread_table.add_column("PID", style="cyan")
#                 thread_table.add_column("Name", style="green")
#                 thread_table.add_column("Threads", style="yellow")
                
#                 for proc in cpu_info['thread_info']:
#                     thread_table.add_row(
#                         str(proc['pid']),
#                         proc['name'],
#                         str(proc['threads'])
#                     )

#                 # Display all tables
#                 self.console.print(Panel.fit(cpu_table))
#                 if gpu_info['available']:
#                     self.console.print(Panel.fit(gpu_table))
#                 self.console.print(Panel.fit(thread_table))

#                 # Check for 'q' key press
#                 if self.input_handler.should_exit:
#                     self.running = False
#                     break

#                 # Sleep for 1 minute
#                 time.sleep(60)
                
#             except KeyboardInterrupt:
#                 self.running = False
#                 break

#         # Device Discovery
#         system_info = self.discover_devices()
        
#         # Display System Information
#         sys_table = Table(title="System Information", show_header=True, header_style="bold magenta")
#         sys_table.add_column("Component", style="cyan")
#         sys_table.add_column("Details", style="green")
        
#         for key, value in system_info.items():
#             sys_table.add_row(key.capitalize(), str(value))
        
#         self.console.print(sys_table)
        
#         # Collect metrics
#         self.collect_metrics()
        
#         # Plot metrics
#         self.plot_metrics()
        
#         # Display Summary
#         summary_table = Table(title="Performance Summary", show_header=True, header_style="bold magenta")
#         summary_table.add_column("Metric", style="cyan")
#         summary_table.add_column("Average", style="green")
#         summary_table.add_column("Max", style="red")
        
#         summary_table.add_row(
#             "CPU Usage",
#             f"{np.mean(self.metrics['cpu_usage']):.1f}%",
#             f"{max(self.metrics['cpu_usage']):.1f}%"
#         )
#         summary_table.add_row(
#             "Memory Usage",
#             f"{np.mean(self.metrics['memory_usage']):.1f}%",
#             f"{max(self.metrics['memory_usage']):.1f}%"
#         )
        
#         self.console.print(summary_table)
#         self.console.print(Panel.fit(
#             "[bold green]Test completed! Results saved in 'system_metrics.png'[/bold green]",
#             box=box.ROUNDED
#         ))

# if __name__ == "__main__":
#     monitor = SystemMonitor()
#     monitor.display_system_info()