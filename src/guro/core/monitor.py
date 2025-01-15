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
# import click
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

# @click.group()
# def cli():
#     """🖥️ System Performance Monitor CLI"""
#     pass
