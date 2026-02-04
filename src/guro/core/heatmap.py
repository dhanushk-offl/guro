import time
import psutil
import platform
import numpy as np
from typing import List, Optional, Dict
from rich.live import Live
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
import subprocess
from pathlib import Path
import ctypes
from ctypes import Structure
import os
from rich.layout import Layout
from .utils import ASCIIGraph
from rich import box

# Import platform-specific modules
if platform.system() == "Windows":
    from ctypes import windll, wintypes, byref, POINTER
    import wmi
    
    class SYSTEM_POWER_STATUS(Structure):
        _fields_ = [
            ('ACLineStatus', wintypes.BYTE),
            ('BatteryFlag', wintypes.BYTE),
            ('BatteryLifePercent', wintypes.BYTE),
            ('SystemStatusFlag', wintypes.BYTE),
            ('BatteryLifeTime', wintypes.DWORD),
            ('BatteryFullLifeTime', wintypes.DWORD),
        ]

class SystemHeatmap:
    def __init__(self):
        self.console = Console()
        self.history_size = 60
        self.system = platform.system()
        self.components = {
            'CPU': {'position': (2, 5), 'size': (8, 15)},
            'GPU': {'position': (12, 5), 'size': (8, 15)},
            'Motherboard': {'position': (0, 0), 'size': (25, 40)},
            'RAM': {'position': (2, 25), 'size': (4, 10)},
            'Storage': {'position': (18, 25), 'size': (4, 10)}
        }
        self.initialize_temp_maps()
        self.temp_history = {
            'CPU': ASCIIGraph(width=30, height=5),
            'GPU': ASCIIGraph(width=30, height=5)
        }
        if self.system == "Windows":
            self.setup_windows_api()

    def setup_windows_api(self):
        if platform.system() == "Windows":
            try:
                self.wmi_connection = wmi.WMI(namespace="root\\OpenHardwareMonitor")
            except:
                self.wmi_connection = None
            self.GetSystemPowerStatus = windll.kernel32.GetSystemPowerStatus
            self.GetSystemPowerStatus.argtypes = [POINTER(SYSTEM_POWER_STATUS)]
            self.GetSystemPowerStatus.restype = wintypes.BOOL

    def initialize_temp_maps(self):
        self.temp_maps = {
            component: np.zeros(dims['size']) 
            for component, dims in self.components.items()
        }

    def get_windows_temps(self) -> Dict[str, float]:
        temps = self.get_fallback_temps()
        
        if self.wmi_connection:
            try:
                sensors = self.wmi_connection.Sensor()
                gpu_temps = []
                for sensor in sensors:
                    if sensor.SensorType == 'Temperature':
                        value = float(sensor.Value)
                        if 'CPU' in sensor.Name and temps['CPU'] < value:
                            temps['CPU'] = value
                        elif 'GPU' in sensor.Name:
                            gpu_temps.append(value)
                        elif 'Motherboard' in sensor.Name and temps['Motherboard'] < value:
                            temps['Motherboard'] = value
                        elif 'Drive' in sensor.Name and temps['Storage'] < value:
                            temps['Storage'] = value
                if gpu_temps:
                    temps['GPU'] = max(gpu_temps)
            except:
                pass
        
        # Update RAM temperature based on memory usage
        temps['RAM'] = self.get_ram_temp()
        return temps

    def get_linux_temps(self) -> Dict[str, float]:
        temps = self.get_fallback_temps()
        
        try:
            # Try reading from sysfs thermal zones
            thermal_zones = Path('/sys/class/thermal').glob('thermal_zone*')
            for zone in thermal_zones:
                try:
                    with open(zone / 'type') as f:
                        zone_type = f.read().strip()
                    with open(zone / 'temp') as f:
                        temp = float(f.read().strip()) / 1000.0
                        
                    if 'cpu' in zone_type.lower():
                        temps['CPU'] = max(temps['CPU'], temp)
                    elif 'gpu' in zone_type.lower():
                        temps['GPU'] = max(temps['GPU'], temp)
                except:
                    continue

            # Try reading from lm-sensors
            try:
                sensors_output = subprocess.check_output(['sensors'], stderr=subprocess.DEVNULL).decode()
                gpu_temps = []
                current_device = ""
                for line in sensors_output.split('\n'):
                    line = line.strip()
                    if not line: continue
                    
                    if ':' not in line:
                        current_device = line.lower()
                        continue
                    
                    name, value = line.split(':', 1)
                    name = name.lower()
                    
                    # More robust regex-free temperature extraction
                    if '°C' in value:
                        try:
                            # Extract number before °C, handling prefixes like '+'
                            clean_val = value.split('°C')[0].strip()
                            # Find the start of the number (skip non-digits except dot/dash/plus)
                            start_idx = 0
                            for k, char in enumerate(clean_val):
                                if char.isdigit() or char in '+-.':
                                    start_idx = k
                                    break
                            temp = float(''.join(c for c in clean_val[start_idx:] if c.isdigit() or c == '.' or c == '-'))
                            
                            # Categorize based on name or device context
                            if any(k in name for k in ['cpu', 'package', 'core', 'tdie', 'tctl']):
                                temps['CPU'] = max(temps['CPU'], temp)
                            elif any(k in name for k in ['gpu', 'edge', 'junction', 'mem']) or 'gpu' in current_device:
                                gpu_temps.append(temp)
                            elif any(k in name for k in ['mb', 'board', 'systin', 'cputin']):
                                temps['Motherboard'] = max(temps['Motherboard'], temp)
                        except:
                            continue
                if gpu_temps:
                    temps['GPU'] = max(gpu_temps)
            except:
                pass

            # Update storage temperature using smartctl
            try:
                smart_output = subprocess.check_output(['smartctl', '-A', '/dev/sda'], stderr=subprocess.DEVNULL).decode()
                for line in smart_output.split('\n'):
                    if 'Temperature' in line:
                        temps['Storage'] = float(line.split()[9])
                        break
            except:
                pass

        except Exception:
            pass

        # Update RAM temperature based on memory usage
        temps['RAM'] = self.get_ram_temp()
        return temps

    def get_macos_temps(self) -> Dict[str, float]:
        temps = self.get_fallback_temps()
        
        try:
            # Try using SMC readings
            try:
                output = subprocess.check_output(['sudo', 'powermetrics', '-n', '1'], stderr=subprocess.DEVNULL).decode()
                gpu_temps = []
                for line in output.split('\n'):
                    if 'CPU die temperature' in line:
                        temps['CPU'] = float(line.split(':')[1].split()[0])
                    elif 'GPU die temperature' in line:
                        gpu_temps.append(float(line.split(':')[1].split()[0]))
                if gpu_temps:
                    temps['GPU'] = max(gpu_temps)
            except:
                pass

            # Try reading from IOKit
            try:
                output = subprocess.check_output(['system_profiler', 'SPHardwareDataType'], stderr=subprocess.DEVNULL).decode()
                for line in output.split('\n'):
                    if 'Processor Temperature' in line:
                        temps['CPU'] = float(line.split(':')[1].strip().replace('°C', ''))
            except:
                pass

        except Exception:
            pass

        # Update RAM temperature based on memory usage
        temps['RAM'] = self.get_ram_temp()
        return temps

    def get_ram_temp(self) -> float:
        memory = psutil.virtual_memory()
        # Estimate RAM temperature based on memory usage
        # Higher memory usage generally correlates with higher temperature
        base_temp = 30.0
        max_temp_increase = 30.0
        return base_temp + (memory.percent / 100.0) * max_temp_increase

    def get_fallback_temps(self) -> Dict[str, float]:
        cpu_percent = float(psutil.cpu_percent())
        memory_percent = float(psutil.virtual_memory().percent)
        
        # More realistic temperature ranges based on typical hardware behavior
        base_temps = {
            'CPU': 35.0,
            'GPU': 35.0,
            'Motherboard': 30.0,
            'Storage': 25.0,
            'RAM': 30.0
        }
        
        # Calculate temperatures based on system load
        return {
            'CPU': base_temps['CPU'] + (cpu_percent * 0.5),
            'GPU': base_temps['GPU'] + (cpu_percent * 0.4),
            'Motherboard': base_temps['Motherboard'] + (cpu_percent * 0.2),
            'Storage': base_temps['Storage'] + (cpu_percent * 0.15),
            'RAM': base_temps['RAM'] + (memory_percent * 0.3)
        }

    def get_system_temps(self) -> Dict[str, float]:
        if self.system == "Windows":
            return self.get_windows_temps()
        elif self.system == "Linux":
            return self.get_linux_temps()
        elif self.system == "Darwin":
            return self.get_macos_temps()
        return self.get_fallback_temps()

    def get_temp_char(self, temp: float) -> tuple:
        if temp < 45:
            return ('·', "green")
        elif temp < 70:
            return ('▒', "yellow")
        else:
            return ('█', "red")

    def update_component_map(self, component: str, temp: float):
        rows, cols = self.components[component]['size']
        base_temp = float(temp)
        noise = np.random.normal(0, 2, (rows, cols))
        self.temp_maps[component] = np.clip(base_temp + noise, 0, 100)

    def run(self, interval: float = 1.0, duration: Optional[int] = None) -> int:
        if duration is not None and duration <= 0:
            raise ValueError("Duration must be positive")
        if interval <= 0:
            raise ValueError("Interval must be positive")

        self.console.clear()
        
        # Setup Layout
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3)
        )
        layout["body"].split_row(
            Layout(name="heatmap", ratio=2),
            Layout(name="graphs", ratio=1)
        )
        layout["graphs"].split_column(
            Layout(name="cpu_graph"),
            Layout(name="gpu_graph"),
            Layout(name="stats")
        )

        start_time = time.time()
        update_count = 0
        
        try:
            with Live(layout, refresh_per_second=2, screen=True) as live:
                while True:
                    elapsed = time.time() - start_time
                    if duration and elapsed >= duration:
                        break
                    
                    temps = self.get_system_temps()
                    self.temp_history['CPU'].add_point(temps['CPU'])
                    self.temp_history['GPU'].add_point(temps['GPU'])
                    
                    # Update Layout
                    layout["header"].update(Panel(
                        f"[bold cyan]Hardware Thermal Dashboard[/bold cyan] | [yellow]Elapsed: {int(elapsed)}s{f'/{duration}s' if duration else ''}[/yellow] | [green]{self.system}[/green]",
                        border_style="blue"
                    ))
                    
                    layout["heatmap"].update(self.generate_system_layout(temps))
                    
                    layout["cpu_graph"].update(Panel(
                        self.temp_history['CPU'].render(f"CPU Temp: {temps['CPU']:.1f}°C"),
                        title="CPU Thermal Trend", border_style="red"
                    ))
                    layout["gpu_graph"].update(Panel(
                        self.temp_history['GPU'].render(f"GPU Temp: {temps['GPU']:.1f}°C"),
                        title="GPU Thermal Trend", border_style="magenta"
                    ))
                    
                    stats_table = Table(box=box.SIMPLE, expand=True)
                    stats_table.add_column("Component", style="cyan")
                    stats_table.add_column("Temp", style="yellow")
                    for comp, val in temps.items():
                        color = "green" if val < 45 else "yellow" if val < 70 else "red"
                        stats_table.add_row(comp, f"[{color}]{val:.1f}°C[/{color}]")
                    
                    layout["stats"].update(Panel(stats_table, title="Current Temps", border_style="white"))
                    
                    layout["footer"].update(Panel(
                        "[bold yellow]Press Ctrl + C to stop thermal monitoring[/bold yellow]",
                        border_style="blue",
                        title_align="center"
                    ))
                    
                    update_count += 1
                    time.sleep(interval)
        except KeyboardInterrupt:
            pass
            
        return update_count

    def generate_system_layout(self, temps: Optional[Dict[str, float]] = None) -> Panel:
        if temps is None:
            temps = self.get_system_temps()
            
        layout = [[' ' for _ in range(40)] for _ in range(25)]
        colors = [[None for _ in range(40)] for _ in range(25)]
        
        for component, info in self.components.items():
            pos_x, pos_y = info['position']
            size_x, size_y = info['size']
            
            self.update_component_map(component, temps[component])
            
            for i in range(size_x):
                for j in range(size_y):
                    temp = float(self.temp_maps[component][i, j])
                    char, color = self.get_temp_char(temp)
                    layout[pos_x + i][pos_y + j] = char
                    colors[pos_x + i][pos_y + j] = color
            
            label_x = pos_x + size_x // 2
            label_y = pos_y + size_y // 2
            label = f"{component[:3]} {temps[component]:.1f}°C"
            for idx, char in enumerate(label):
                if 0 <= label_y + idx < len(layout[0]):
                    layout[label_x][label_y + idx] = char
                    colors[label_x][label_y + idx] = "white"

        text = Text()
        for row in range(len(layout)):
            for col in range(len(layout[0])):
                text.append(layout[row][col], style=colors[row][col])
            text.append("\n")

        return Panel(
            text, 
            title="Internal Thermal Map", 
            border_style="blue"
        )