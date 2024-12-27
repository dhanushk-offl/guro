# heatmap.py
import time
import psutil
import platform
import curses
import numpy as np
from typing import List, Tuple, Optional
from rich.live import Live
from rich.console import Console
from rich.table import Table
from rich.text import Text

class SystemHeatmap:
    def __init__(self):
        self.console = Console()
        self.history_size = 60  # 1 minute of history
        self.cpu_history = np.zeros((psutil.cpu_count(), self.history_size))
        self.gpu_history = np.zeros((self.get_gpu_count(), self.history_size))
        self.current_index = 0
        
    def get_gpu_count(self) -> int:
        """Get number of GPUs in the system."""
        try:
            if platform.system() == "Windows":
                import wmi
                w = wmi.WMI()
                return len(w.Win32_VideoController())
            elif platform.system() == "Linux":
                import subprocess
                try:
                    output = subprocess.check_output(["nvidia-smi", "-L"]).decode()
                    return len(output.strip().split('\n'))
                except:
                    return 0
            elif platform.system() == "Darwin":  # macOS
                return 1  # Assume integrated GPU
            return 0
        except:
            return 0

    def get_cpu_temps(self) -> List[float]:
        """Get CPU temperatures for all cores."""
        try:
            if platform.system() == "Linux":
                import psutil
                temps = psutil.sensors_temperatures()
                if 'coretemp' in temps:
                    return [temp.current for temp in temps['coretemp']]
                return [0.0] * psutil.cpu_count()
            elif platform.system() == "Windows":
                import wmi
                w = wmi.WMI(namespace="root\\OpenHardwareMonitor")
                temperature_infos = w.Sensor(SensorType='Temperature')
                return [float(sensor.Value) for sensor in temperature_infos if 'CPU' in sensor.Name]
            elif platform.system() == "Darwin":
                # MacOS temperature reading (requires sudo)
                import subprocess
                try:
                    output = subprocess.check_output(["sudo", "powermetrics", "-n", "1"]).decode()
                    # Parse the output to get CPU temperature
                    return [float(output.split("CPU die temperature:")[1].split()[0])]
                except:
                    return [0.0] * psutil.cpu_count()
        except:
            return [0.0] * psutil.cpu_count()

    def get_gpu_temps(self) -> List[float]:
        """Get GPU temperatures."""
        try:
            if platform.system() == "Windows":
                import wmi
                w = wmi.WMI(namespace="root\\OpenHardwareMonitor")
                temperature_infos = w.Sensor(SensorType='Temperature')
                return [float(sensor.Value) for sensor in temperature_infos if 'GPU' in sensor.Name]
            elif platform.system() == "Linux":
                import subprocess
                try:
                    output = subprocess.check_output(["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader"]).decode()
                    return [float(temp) for temp in output.strip().split('\n')]
                except:
                    return [0.0]
            elif platform.system() == "Darwin":
                # MacOS GPU temperature (if available)
                return [0.0]
        except:
            return [0.0]

    def get_temp_color(self, temp: float) -> str:
        """Convert temperature to color."""
        if temp < 50:
            return "green"
        elif temp < 70:
            return "yellow"
        else:
            return "red"

    def update_histories(self):
        """Update temperature histories."""
        cpu_temps = self.get_cpu_temps()
        gpu_temps = self.get_gpu_temps()
        
        self.cpu_history[:, self.current_index] = cpu_temps[:psutil.cpu_count()]
        self.gpu_history[:, self.current_index] = gpu_temps[:self.get_gpu_count()]
        
        self.current_index = (self.current_index + 1) % self.history_size

    def generate_heatmap_table(self, show_cpu: bool = True, show_gpu: bool = True) -> Table:
        """Generate a rich table containing the heatmap."""
        table = Table(title="System Temperature Heatmap")
        
        # Add time columns
        for i in range(self.history_size):
            table.add_column(str(i), justify="center", width=2)

        if show_cpu:
            for core in range(psutil.cpu_count()):
                row = []
                for temp in self.cpu_history[core]:
                    color = self.get_temp_color(temp)
                    cell = Text("█", style=color)
                    row.append(cell)
                table.add_row(*row, end_section=True)

        if show_gpu:
            for gpu in range(self.get_gpu_count()):
                row = []
                for temp in self.gpu_history[gpu]:
                    color = self.get_temp_color(temp)
                    cell = Text("█", style=color)
                    row.append(cell)
                table.add_row(*row)

        return table

    def run(self, show_cpu: bool = True, show_gpu: bool = True, interval: float = 1.0, duration: Optional[int] = None):
        """Run the heatmap visualization."""
        start_time = time.time()
        
        with Live(self.generate_heatmap_table(show_cpu, show_gpu), refresh_per_second=1) as live:
            try:
                while True:
                    self.update_histories()
                    live.update(self.generate_heatmap_table(show_cpu, show_gpu))
                    
                    if duration and (time.time() - start_time) >= duration:
                        break
                        
                    time.sleep(interval)
            except KeyboardInterrupt:
                pass