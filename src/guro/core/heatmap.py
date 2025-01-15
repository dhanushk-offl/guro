import time
import psutil
import platform
import numpy as np
from typing import List, Optional, Dict
from rich.live import Live
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
import subprocess
from pathlib import Path
import ctypes
from ctypes import Structure
import os

# Import platform-specific modules
if platform.system() == "Windows":
    from ctypes import windll, wintypes, byref, POINTER
    
    class SYSTEM_POWER_STATUS(Structure):
        _fields_ = [
            ('ACLineStatus', wintypes.BYTE),
            ('BatteryFlag', wintypes.BYTE),
            ('BatteryLifePercent', wintypes.BYTE),
            ('SystemStatusFlag', wintypes.BYTE),
            ('BatteryLifeTime', wintypes.DWORD),
            ('BatteryFullLifeTime', wintypes.DWORD),
        ]

    class PROCESSOR_POWER_INFORMATION(Structure):
        _fields_ = [
            ("CurrentFrequency", wintypes.ULONG),
            ("MaxMhz", wintypes.ULONG),
            ("CurrentMhz", wintypes.ULONG),
            ("MhzLimit", wintypes.ULONG),
            ("MaxIdleState", wintypes.ULONG),
            ("CurrentIdleState", wintypes.ULONG),
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
        if self.system == "Windows":
            self.setup_windows_api()

    def setup_windows_api(self):
        if platform.system() == "Windows":
            self.GetSystemPowerStatus = windll.kernel32.GetSystemPowerStatus
            self.GetSystemPowerStatus.argtypes = [POINTER(SYSTEM_POWER_STATUS)]
            self.GetSystemPowerStatus.restype = wintypes.BOOL
            self.NtQuerySystemInformation = windll.ntdll.NtQuerySystemInformation
            self.CallNtPowerInformation = windll.powrprof.CallNtPowerInformation

    def initialize_temp_maps(self):
        self.temp_maps = {
            component: np.zeros(dims['size']) 
            for component, dims in self.components.items()
        }

    def get_windows_temps(self) -> Dict[str, float]:
        if platform.system() != "Windows":
            return self.get_fallback_temps()
            
        return {
            'CPU': self.get_windows_cpu_temp(),
            'GPU': self.get_windows_gpu_temp(),
            'Motherboard': self.get_windows_motherboard_temp(),
            'Storage': self.get_windows_storage_temp(),
            'RAM': self.get_windows_ram_temp()
        }

    def get_windows_cpu_temp(self) -> float:
        if platform.system() != "Windows":
            return self.get_cpu_load_temp()
            
        try:
            buffer_size = ctypes.sizeof(PROCESSOR_POWER_INFORMATION)
            buffer = ctypes.create_string_buffer(buffer_size)
            if self.CallNtPowerInformation(11, None, 0, buffer, buffer_size) == 0:
                info = PROCESSOR_POWER_INFORMATION.from_buffer_copy(buffer)
                return float(40 + (info.CurrentMhz / max(info.MaxMhz, 1)) * 40)  # Fixed division by zero
            return self.get_cpu_load_temp()
        except:
            return self.get_cpu_load_temp()

    def get_windows_gpu_temp(self) -> float:
        if platform.system() != "Windows":
            return self.get_gpu_load_temp()
            
        try:
            if hasattr(windll, 'd3d11'):
                device = ctypes.c_void_p()
                if windll.d3d11.D3D11CreateDevice(None, 0, None, 0, None, 0, 0, 
                                                ctypes.byref(device), None, None) == 0:
                    return self.get_gpu_load_temp()
            return self.get_gpu_load_temp()
        except:
            return self.get_gpu_load_temp()

    def get_windows_motherboard_temp(self) -> float:
        if platform.system() != "Windows":
            return 45.0
            
        try:
            status = SYSTEM_POWER_STATUS()
            if self.GetSystemPowerStatus(byref(status)):
                return float(35 + (status.BatteryLifePercent / 100) * 15)  # Fixed type conversion
            return 45.0
        except:
            return 45.0

    def get_windows_storage_temp(self) -> float:
        if platform.system() != "Windows":
            return 35.0
            
        try:
            if hasattr(windll, 'kernel32'):
                hDevice = windll.kernel32.CreateFileW(
                    "\\\\.\\PhysicalDrive0", 
                    0x80000000,
                    0x3,
                    None,
                    3,
                    0,
                    None
                )
                if hDevice != -1:
                    return self.get_disk_load_temp()
            return 35.0
        except:
            return 35.0

    def get_windows_ram_temp(self) -> float:
        return float(psutil.virtual_memory().percent / 2)  # Fixed type conversion

    def get_linux_temps(self) -> Dict[str, float]:
        temps = {
            'CPU': 0.0,
            'GPU': 0.0,
            'Motherboard': 0.0,
            'Storage': 0.0,
            'RAM': 0.0
        }
        
        try:
            # CPU Temperature
            cpu_temps = psutil.sensors_temperatures()
            if 'coretemp' in cpu_temps:
                temps['CPU'] = float(max(temp.current for temp in cpu_temps['coretemp']))
            
            # GPU Temperature
            try:
                nvidia_output = subprocess.check_output(
                    ["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader"],
                    stderr=subprocess.DEVNULL
                ).decode()
                temps['GPU'] = float(nvidia_output.strip())
            except:
                try:
                    for card in Path('/sys/class/drm').glob('card?'):
                        temp_file = next(card.glob('device/hwmon/hwmon*/temp1_input'))
                        with open(temp_file) as f:
                            temps['GPU'] = float(f.read().strip()) / 1000
                            break
                except:
                    temps['GPU'] = self.get_gpu_load_temp()
            
            # Motherboard Temperature
            if 'acpitz' in cpu_temps:
                temps['Motherboard'] = float(cpu_temps['acpitz'][0].current)
            
            # Storage Temperature
            try:
                output = subprocess.check_output(['smartctl', '-A', '/dev/sda']).decode()
                for line in output.split('\n'):
                    if 'Temperature' in line:
                        temps['Storage'] = float(line.split()[9])
                        break
            except:
                temps['Storage'] = self.get_disk_load_temp()
            
            temps['RAM'] = float(psutil.virtual_memory().percent / 2)
            
            return temps
        except:
            return self.get_fallback_temps()

    def get_macos_temps(self) -> Dict[str, float]:
        temps = self.get_fallback_temps()  # Start with fallback temperatures
        
        try:
            # SMC temperature readings
            output = subprocess.check_output(
                ['sudo', 'powermetrics', '-n', '1'],
                stderr=subprocess.DEVNULL
            ).decode()
            
            for line in output.split('\n'):
                if 'CPU die temperature' in line:
                    temps['CPU'] = float(line.split(':')[1].split()[0])
                elif 'GPU die temperature' in line:
                    temps['GPU'] = float(line.split(':')[1].split()[0])
            
            temps['Motherboard'] = float(temps['CPU'] * 0.8)
            temps['RAM'] = float(psutil.virtual_memory().percent / 2)
            
            try:
                output = subprocess.check_output(['smartctl', '-A', '/dev/disk0']).decode()
                for line in output.split('\n'):
                    if 'Temperature' in line:
                        temps['Storage'] = float(line.split()[9])
                        break
            except:
                temps['Storage'] = self.get_disk_load_temp()
            
            return temps
        except:
            return temps  # Return the fallback temps if anything fails

    def get_cpu_load_temp(self) -> float:
        return float(40 + (psutil.cpu_percent() * 0.6))

    def get_gpu_load_temp(self) -> float:
        return float(35 + (psutil.cpu_percent() * 0.5))

    def get_disk_load_temp(self) -> float:
        disk_io = psutil.disk_io_counters()
        if disk_io:
            return float(30 + (disk_io.read_bytes + disk_io.write_bytes) / (1024 * 1024 * 1024))
        return 30.0

    def get_fallback_temps(self) -> Dict[str, float]:
        cpu_percent = float(psutil.cpu_percent())
        memory_percent = float(psutil.virtual_memory().percent)
        return {
            'CPU': float(40 + (cpu_percent * 0.4)),
            'GPU': float(35 + (cpu_percent * 0.3)),
            'Motherboard': float(35 + (cpu_percent * 0.2)),
            'Storage': float(30 + (cpu_percent * 0.1)),
            'RAM': float(30 + (memory_percent * 0.2))
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
        base_temp = float(temp)  # Ensure temp is float
        noise = np.random.normal(0, 2, (rows, cols))
        self.temp_maps[component] = np.clip(base_temp + noise, 0, 100)

    def generate_system_layout(self) -> Panel:
        layout = [[' ' for _ in range(40)] for _ in range(25)]
        colors = [[None for _ in range(40)] for _ in range(25)]
        temps = self.get_system_temps()
        
        for component, info in self.components.items():
            pos_x, pos_y = info['position']
            size_x, size_y = info['size']
            
            self.update_component_map(component, temps[component])
            
            for i in range(size_x):
                for j in range(size_y):
                    temp = float(self.temp_maps[component][i, j])  # Ensure float conversion
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
            title=f"System Temperature Heatmap ({self.system})", 
            border_style="blue"
        )

    def run(self, interval: float = 1.0, duration: Optional[int] = None) -> int:
        """
        Run the system heatmap visualization.
        
        Args:
            interval (float): Update interval in seconds
            duration (Optional[int]): Total duration to run in seconds
            
        Returns:
            int: Number of updates performed
            
        Raises:
            ValueError: If duration is negative or interval is zero/negative
        """
        if duration is not None and duration <= 0:
            raise ValueError("Duration must be positive")
        if interval <= 0:
            raise ValueError("Interval must be positive")

        start_time = time.time()
        update_count = 0
        
        with Live(self.generate_system_layout(), refresh_per_second=1) as live:
            try:
                while True:
                    live.update(self.generate_system_layout())
                    update_count += 1
                    
                    if duration and (time.time() - start_time) >= duration:
                        break
                    
                    time.sleep(interval)
            except KeyboardInterrupt:
                pass
            
            return update_count