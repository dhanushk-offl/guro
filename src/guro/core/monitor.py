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
from rich.live import Live
from rich import box
import csv
from .utils import ASCIIGraph

class GPUDetector:
    @staticmethod
    def get_nvidia_info():
        try:
            nvidia_smi = "nvidia-smi"
            # Use universal_newlines=False and decode manually to be safer with different OS/encodings
            output = subprocess.check_output([nvidia_smi, "--query-gpu=gpu_name,memory.total,memory.used,memory.free,temperature.gpu,utilization.gpu,fan.speed,power.draw", "--format=csv,noheader,nounits"], 
                                          universal_newlines=False).decode('utf-8')
            lines = output.strip().split('\n')
            gpus = []
            for line in lines:
                if not line.strip(): continue
                parts = [p.strip() for p in line.split(',')]
                if len(parts) < 8: continue
                name, total, used, free, temp, util, fan, power = parts
                gpus.append({
                    'name': name,
                    'memory_total': float(total) * 1024**2,
                    'memory_used': float(used) * 1024**2,
                    'memory_free': float(free) * 1024**2,
                    'temperature': float(temp),
                    'utilization': float(util),
                    'fan_speed': float(fan) if fan != '[N/A]' and fan != 'N/A' else None,
                    'power_draw': float(power) if power != '[N/A]' and power != 'N/A' else None,
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
    def get_integrated_info():
        gpus = []
        try:
            if platform.system() == "Windows":
                import wmi
                w = wmi.WMI()
                for video in w.Win32_VideoController():
                    # Avoid duplicates if nvidia/amd already detected
                    name = video.Name
                    gpus.append({
                        'name': name,
                        'type': 'Integrated',
                        'memory_total': int(video.AdapterRAM) if video.AdapterRAM else None,
                        'utilization': None,
                        'temperature': None
                    })
            elif platform.system() == "Linux":
                # Basic lspci check for VGA
                output = subprocess.check_output("lspci | grep -i vga", shell=True, universal_newlines=True)
                for line in output.strip().split('\n'):
                    gpus.append({
                        'name': line.split(':', 2)[-1].strip(),
                        'type': 'Integrated',
                        'memory_total': None,
                        'utilization': None,
                        'temperature': None
                    })
        except:
            pass
        return gpus

    @staticmethod
    def get_all_gpus():
        gpu_info = {
            'available': False,
            'gpus': []
        }
        
        nvidia_gpus = GPUDetector.get_nvidia_info()
        amd_gpus = GPUDetector.get_amd_info()
        integrated_gpus = GPUDetector.get_integrated_info()
        
        all_gpus = nvidia_gpus + amd_gpus
        
        # Add integrated GPUs only if no dedicated ones are found or if they have different names
        detected_names = [g['name'] for g in all_gpus]
        for ig in integrated_gpus:
            if ig['name'] not in detected_names:
                all_gpus.append(ig)
        
        if all_gpus:
            gpu_info['available'] = True
            gpu_info['gpus'] = all_gpus
            
        return gpu_info


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
        
        # Initialize Graphs for all potential GPUs
        gpu_info = GPUDetector.get_all_gpus()
        gpu_graphs = [ASCIIGraph(width=40, height=5) for _ in gpu_info['gpus']]
        
        # Setup Dashboard Layout
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )
        layout["main"].split_row(
            Layout(name="graphs", ratio=1),
            Layout(name="details", ratio=1)
        )
        layout["graphs"].split_column(
            Layout(name="cpu_graph"),
            Layout(name="mem_graph"),
            Layout(name="gpu_graphs")
        )
        
        start_time = time.time()
        try:
            with Live(layout, refresh_per_second=4, screen=True) as live:
                while True:
                    current_time = time.time()
                    elapsed = current_time - start_time
                    if duration and (elapsed >= duration):
                        break
                    
                    # Update System Stats
                    cpu_percent = psutil.cpu_percent()
                    memory = psutil.virtual_memory()
                    memory_percent = memory.percent
                    sys_info = self.get_system_info()
                    
                    self.cpu_graph.add_point(cpu_percent)
                    self.memory_graph.add_point(memory_percent)
                    
                    if export_data:
                        self.monitoring_data.append({
                            'timestamp': datetime.datetime.now().isoformat(),
                            'cpu_usage': cpu_percent,
                            'memory_usage': memory_percent
                        })
                    
                    # Header
                    layout["header"].update(Panel(
                        f"[bold cyan]Guro System Dashboard[/bold cyan] | [yellow]Running for: {int(elapsed)}s{f'/{duration}s' if duration else ''}[/yellow] | [green]{sys_info['os']}[/green]",
                        border_style="blue"
                    ))
                    
                    # Graphs Column
                    cpu_panel = Panel(self.cpu_graph.render(f"CPU: {cpu_percent:.1f}%"), title="CPU Usage History", border_style="green")
                    mem_panel = Panel(self.memory_graph.render(f"Memory: {memory_percent:.1f}%"), title="Memory Usage History", border_style="magenta")
                    
                    layout["cpu_graph"].update(cpu_panel)
                    layout["mem_graph"].update(mem_panel)
                    
                    # GPU Graphs and Details
                    gpu_info = GPUDetector.get_all_gpus()
                    gpu_details_table = Table(title="GPU & Device Information", box=box.SIMPLE, expand=True)
                    gpu_details_table.add_column("Device", style="cyan")
                    gpu_details_table.add_column("Stat", style="yellow")
                    gpu_details_table.add_column("Value", style="green")
                    
                    if gpu_info['available']:
                        gpu_plots = []
                        for i, (gpu, graph) in enumerate(zip(gpu_info['gpus'], gpu_graphs)):
                            util = gpu.get('utilization', 0) or 0
                            graph.add_point(util)
                            gpu_plots.append(graph.render(f"GPU {i} ({gpu['name']}): {util:.1f}%"))
                            
                            # Add to details table
                            gpu_details_table.add_row(f"GPU {i}", "Name", gpu['name'][:20])
                            gpu_details_table.add_row("", "Temp", f"{gpu.get('temperature', 'N/A')}°C")
                            if gpu.get('memory_used'):
                                gpu_details_table.add_row("", "Mem", f"{gpu['memory_used']/(1024**2):.0f}/{gpu['memory_total']/(1024**2):.0f}MB")
                        
                        layout["gpu_graphs"].update(Panel("\n".join(gpu_plots), title="GPU Usage History", border_style="cyan"))
                    else:
                        layout["gpu_graphs"].update(Panel("[yellow]No dedicated GPU stats available[/yellow]", title="GPU Usage History"))
                        gpu_details_table.add_row("GPU", "Status", "[yellow]GPU not found in your device[/yellow]")
                    
                    # Details Column
                    details_layout = Layout()
                    details_layout.split_column(
                        Layout(Panel(gpu_details_table, title="Detailed Stats", border_style="white")),
                        Layout(Panel(self._get_process_table(), title="Top Processes", border_style="white"))
                    )
                    layout["details"].update(details_layout)
                    
                    # Footer
                    progress = elapsed / duration if duration else 0
                    layout["footer"].update(Panel(
                        f"[bold yellow]Press Ctrl + C to stop monitoring[/bold yellow] | [cyan]Export: {'Enabled' if export_data else 'Disabled'}[/cyan]",
                        border_style="blue"
                    ))
                    
                    time.sleep(interval)
        
        except KeyboardInterrupt:
            pass
        
        self.console.clear()
        self.console.print("[bold green]Monitoring completed.[/bold green]")
        if export_data:
            self.export_monitoring_data()
            self.console.print("\n[green]Monitoring data exported to 'monitoring_data.csv'[/green]")

    def _get_process_table(self):
        table = Table(box=box.SIMPLE, expand=True)
        table.add_column("PID", style="dim")
        table.add_column("Name")
        table.add_column("CPU%", justify="right")
        table.add_column("Mem%", justify="right")
        
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                processes.append(proc.info)
            
            # Sort by CPU usage
            processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
            
            for proc in processes[:10]:
                table.add_row(
                    str(proc['pid']),
                    proc['name'][:15],
                    f"{proc['cpu_percent']:.1f}",
                    f"{proc['memory_percent']:.1f}"
                )
        except:
            pass
        return table

# @click.group()
# def cli():
#     """🖥️ System Performance Monitor CLI"""
#     pass
