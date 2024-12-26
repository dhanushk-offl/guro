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

#     def display_system_info(self):
#         if not self.collector_thread.is_alive():
#             self.collector_thread.start()

#         while True:
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

#                 # Sleep for update interval
#                 time.sleep(2)
                
#             except KeyboardInterrupt:
#                 self.running = False
#                 break

# if __name__ == "__main__":
#     monitor = SystemMonitor()
#     monitor.display_system_info()
import psutil
import platform
import subprocess
import os
import shutil
from typing import Dict, List, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import time

class BarGraph:
    @staticmethod
    def create_horizontal_bar(percentage: float, width: int = 40) -> str:
        """Create a horizontal bar graph using ASCII/Unicode characters."""
        filled_length = int(width * percentage / 100)
        bar = '█' * filled_length + '░' * (width - filled_length)
        return f"[{bar}] {percentage:5.1f}%"

    @staticmethod
    def create_vertical_bars(data: List[float], height: int = 10, width: int = 50) -> List[str]:
        """Create a vertical bar graph using ASCII/Unicode characters."""
        if not data:
            return []

        # Unicode characters for different levels
        bars = ' ▁▂▃▄▅▆▇█'
        max_val = max(data)
        normalized = [min(int((val / max_val) * (len(bars) - 1)), len(bars) - 1) if max_val > 0 else 0 for val in data]
        
        graph = []
        graph.append('┌' + '─' * width + '┐')
        for i in range(height):
            line = '│'
            for val in normalized[-width:]:
                if height - i <= val:
                    line += '█'
                else:
                    line += ' '
            line += '│'
            graph.append(line)
        graph.append('└' + '─' * width + '┘')
        
        return graph

    @staticmethod
    def create_history_graph(data: List[float], width: int = 50, height: int = 10, title: str = "") -> str:
        """Create a historical line graph using ASCII/Unicode characters."""
        if not data:
            return ""

        graph = []
        if title:
            graph.append(title.center(width + 2))

        # Normalize data
        max_val = max(data)
        min_val = min(data)
        range_val = max_val - min_val or 1

        # Create graph points
        points = []
        for val in data[-width:]:
            normalized = (val - min_val) / range_val
            point_height = int(normalized * (height - 1))
            points.append(point_height)

        # Build graph
        for h in range(height - 1, -1, -1):
            line = ['│']
            for p in points:
                if p >= h:
                    line.append('█')
                else:
                    line.append(' ')
            line.append('│')
            graph.append(''.join(line))

        # Add bottom border
        graph.append('└' + '─' * width + '┘')

        # Add scale
        if max_val != min_val:
            graph.append(f"{min_val:^6.1f}{' ' * (width - 11)}{max_val:^6.1f}")

        return '\n'.join(graph)

class GPUMonitor:
    @staticmethod
    def get_nvidia_info() -> List[Dict]:
        """Get NVIDIA GPU information."""
        try:
            output = subprocess.check_output(
                ['nvidia-smi', '--query-gpu=gpu_name,memory.total,memory.used,memory.free,temperature.gpu,utilization.gpu,fan.speed,power.draw', 
                 '--format=csv,noheader,nounits'],
                universal_newlines=True
            )
            gpus = []
            for line in output.strip().split('\n'):
                name, total, used, free, temp, util, fan, power = line.split(',')
                gpus.append({
                    'name': name.strip(),
                    'memory_total': float(total),
                    'memory_used': float(used),
                    'memory_free': float(free),
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
    def get_amd_info() -> List[Dict]:
        """Get AMD GPU information."""
        try:
            output = subprocess.check_output(['rocm-smi'], universal_newlines=True)
            gpus = []
            current_gpu = {}
            
            for line in output.strip().split('\n'):
                if 'GPU' in line and 'Card' in line:
                    if current_gpu:
                        gpus.append(current_gpu)
                    current_gpu = {'type': 'AMD'}
                    
                if 'GPU Memory Use' in line:
                    try:
                        used = float(line.split(':')[1].strip().split()[0])
                        current_gpu['memory_used'] = used * 1024**2
                    except:
                        pass
                        
                if 'Total GPU Memory' in line:
                    try:
                        total = float(line.split(':')[1].strip().split()[0])
                        current_gpu['memory_total'] = total * 1024**2
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
    def get_all_gpus() -> Dict:
        """Get information for all available GPUs."""
        gpu_info = {
            'available': False,
            'gpus': []
        }
        
        nvidia_gpus = GPUMonitor.get_nvidia_info()
        amd_gpus = GPUMonitor.get_amd_info()
        
        all_gpus = nvidia_gpus + amd_gpus
        
        if all_gpus:
            gpu_info['available'] = True
            gpu_info['gpus'] = all_gpus
            
        return gpu_info

class ProcessMonitor:
    @staticmethod
    def get_top_processes(count: int = 5) -> List[Dict]:
        """Get information about top processes by CPU usage."""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                proc_info = proc.info
                proc_info['cpu_percent'] = proc.cpu_percent()
                processes.append(proc_info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return sorted(processes, key=lambda x: x['cpu_percent'], reverse=True)[:count]

class SystemMonitor:
    def __init__(self):
        self.console = Console()
        terminal_size = shutil.get_terminal_size()
        self.graph_width = min(50, terminal_size.columns - 20)
        self.graph_height = 10
        self.cpu_history = []
        self.memory_history = []
        self.max_history = 50

    def get_cpu_info(self) -> Dict:
        """Get CPU information."""
        cpu_freq = psutil.cpu_freq()
        cpu_percent = psutil.cpu_percent(interval=1, percpu=True)
        avg_percent = sum(cpu_percent) / len(cpu_percent)
        
        self.cpu_history.append(avg_percent)
        if len(self.cpu_history) > self.max_history:
            self.cpu_history.pop(0)
        
        return {
            'percent': cpu_percent,
            'average': avg_percent,
            'freq_current': cpu_freq.current if cpu_freq else 0,
            'freq_max': cpu_freq.max if cpu_freq else 0,
            'cores': psutil.cpu_count(),
            'threads': psutil.cpu_count(logical=True)
        }

    def get_memory_info(self) -> Dict:
        """Get memory information."""
        memory = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        self.memory_history.append(memory.percent)
        if len(self.memory_history) > self.max_history:
            self.memory_history.pop(0)
        
        return {
            'total': memory.total,
            'used': memory.used,
            'percent': memory.percent,
            'swap_total': swap.total,
            'swap_used': swap.used,
            'swap_percent': swap.percent
        }

    def display_resource_usage(self):
        """Display system resource usage with graphs and tables."""
        while True:
            try:
                self.console.clear()
                
                # Get system information
                cpu_info = self.get_cpu_info()
                memory_info = self.get_memory_info()
                gpu_info = GPUMonitor.get_all_gpus()
                top_processes = ProcessMonitor.get_top_processes()

                # CPU Usage Section
                cpu_table = Table(title="CPU Usage", show_header=True, header_style="bold magenta")
                cpu_table.add_column("Core", style="cyan")
                cpu_table.add_column("Usage", style="green", no_wrap=True)
                
                for i, usage in enumerate(cpu_info['percent']):
                    cpu_table.add_row(
                        f"Core {i}",
                        BarGraph.create_horizontal_bar(usage, width=40)
                    )

                # CPU History Graph
                cpu_history_graph = BarGraph.create_history_graph(
                    self.cpu_history,
                    width=self.graph_width,
                    height=self.graph_height,
                    title="CPU Usage History"
                )

                # Memory Usage Section
                memory_table = Table(title="Memory Usage", show_header=True, header_style="bold magenta")
                memory_table.add_column("Type", style="cyan")
                memory_table.add_column("Usage", style="green", no_wrap=True)
                memory_table.add_column("Details", style="yellow")

                memory_table.add_row(
                    "RAM",
                    BarGraph.create_horizontal_bar(memory_info['percent'], width=40),
                    f"{memory_info['used'] / (1024**3):,.1f}GB / {memory_info['total'] / (1024**3):,.1f}GB"
                )
                memory_table.add_row(
                    "Swap",
                    BarGraph.create_horizontal_bar(memory_info['swap_percent'], width=40),
                    f"{memory_info['swap_used'] / (1024**3):,.1f}GB / {memory_info['swap_total'] / (1024**3):,.1f}GB"
                )

                # Memory History Graph
                memory_history_graph = BarGraph.create_history_graph(
                    self.memory_history,
                    width=self.graph_width,
                    height=self.graph_height,
                    title="Memory Usage History"
                )

                # GPU Section
                if gpu_info['available']:
                    gpu_table = Table(title="GPU Usage", show_header=True, header_style="bold magenta")
                    gpu_table.add_column("GPU", style="cyan")
                    gpu_table.add_column("Usage", style="green", no_wrap=True)
                    gpu_table.add_column("Memory", style="yellow")
                    gpu_table.add_column("Temperature", style="red")

                    for i, gpu in enumerate(gpu_info['gpus']):
                        memory_used_gb = gpu['memory_used'] / 1024
                        memory_total_gb = gpu['memory_total'] / 1024
                        memory_percent = (memory_used_gb / memory_total_gb) * 100

                        gpu_table.add_row(
                            f"{gpu.get('name', f'GPU {i}')} ({gpu['type']})",
                            BarGraph.create_horizontal_bar(gpu.get('utilization', 0), width=40),
                            f"{BarGraph.create_horizontal_bar(memory_percent, width=20)} ({memory_used_gb:.1f}GB / {memory_total_gb:.1f}GB)",
                            f"{gpu.get('temperature', 'N/A')}°C"
                        )

                # Top Processes Section
                process_table = Table(title="Top Processes", show_header=True, header_style="bold magenta")
                process_table.add_column("PID", style="cyan")
                process_table.add_column("Name", style="green")
                process_table.add_column("CPU%", style="yellow")
                process_table.add_column("Memory%", style="yellow")

                for proc in top_processes:
                    process_table.add_row(
                        str(proc['pid']),
                        proc['name'],
                        f"{proc['cpu_percent']:5.1f}%",
                        f"{proc.get('memory_percent', 0):5.1f}%"
                    )

                # Display all information
                self.console.print(Panel.fit(cpu_table))
                self.console.print(cpu_history_graph)
                self.console.print(Panel.fit(memory_table))
                self.console.print(memory_history_graph)
                if gpu_info['available']:
                    self.console.print(Panel.fit(gpu_table))
                self.console.print(Panel.fit(process_table))

                # User interaction
                self.console.print("\nPress Enter to refresh, 'q' to quit", style="bold yellow")
                user_input = input()
                if user_input.lower() == 'q':
                    break

            except KeyboardInterrupt:
                break

if __name__ == "__main__":
    monitor = SystemMonitor()
    monitor.display_resource_usage()