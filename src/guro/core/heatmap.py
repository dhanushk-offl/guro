import time
import shutil
import psutil
import platform
import logging
import subprocess
import numpy as np
from typing import Dict, Optional

from rich.live import Live
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.layout import Layout
from rich import box

from .utils import ASCIIGraph
from .telemetry import Reading, Schedule

logger = logging.getLogger(__name__)

SUBPROCESS_TIMEOUT = 5  # seconds


class SystemHeatmap:
    def __init__(self, estimates: bool = False):
        self.estimates = estimates
        self.readings = {}
        self._gpu_reading = None
        self._gpu_checked_at = float('-inf')
        self.console = Console()
        self.history_size = 60
        self.system = platform.system()
        self.components: Dict[str, Dict] = {
            'CPU': {'position': (2, 5), 'size': (8, 15)},
            'GPU': {'position': (12, 5), 'size': (8, 15)},
            'Motherboard': {'position': (0, 0), 'size': (25, 40)},
            'RAM': {'position': (2, 25), 'size': (4, 10)},
            'Storage': {'position': (18, 25), 'size': (4, 10)}
        }
        self.initialize_temp_maps()
        self.temp_history: Dict[str, ASCIIGraph] = {
            'CPU': ASCIIGraph(width=30, height=5),
            'GPU': ASCIIGraph(width=30, height=5)
        }
        if self.system == "Windows":
            self._setup_windows_api()

    def _setup_windows_api(self):
        if platform.system() != "Windows":
            return
        self.wmi_connection = None
        try:
            import wmi  # type: ignore
            self.wmi_connection = wmi.WMI(namespace="root\\OpenHardwareMonitor")
        except Exception:
            logger.debug("OpenHardwareMonitor WMI not available, marking sensors unavailable")

    def initialize_temp_maps(self):
        self.temp_maps: Dict[str, np.ndarray] = {
            component: np.zeros(dims['size'])
            for component, dims in self.components.items()
        }

    def _empty_temps(self):
        return {component: None for component in self.components}

    @staticmethod
    def _record(temps, component, value):
        reading = Reading.temperature(value, 'sensor')
        if reading.available:
            previous = temps[component]
            temps[component] = value if previous is None else max(previous, value)

    def get_windows_temps(self):
        temps = self._empty_temps()
        if getattr(self, 'wmi_connection', None):
            try:
                for sensor in self.wmi_connection.Sensor():
                    if sensor.SensorType != 'Temperature':
                        continue
                    name = sensor.Name.lower()
                    component = next((c for c, keys in {
                        'CPU': ('cpu',), 'GPU': ('gpu',),
                        'Motherboard': ('motherboard',), 'Storage': ('drive',),
                        'RAM': ('ram', 'dimm')
                    }.items() if any(k in name for k in keys)), None)
                    if component:
                        try:
                            self._record(temps, component, float(sensor.Value))
                        except (TypeError, ValueError):
                            continue
            except Exception:
                logger.exception('Unable to read WMI temperatures')
        return temps

    def get_linux_temps(self):
        temps = self._empty_temps()
        try:
            sensors = psutil.sensors_temperatures()
        except (AttributeError, OSError):
            sensors = {}
        for device, entries in sensors.items():
            for entry in entries:
                name = (device + ' ' + (entry.label or '')).lower()
                component = next((c for c, keys in {
                    'CPU': ('coretemp', 'k10temp', 'zenpower', 'cpu', 'package', 'tdie', 'tctl'),
                    'GPU': ('amdgpu', 'nouveau', 'gpu'),
                    'Storage': ('nvme', 'drivetemp'),
                    'RAM': ('dimm', 'jc42'),
                    'Motherboard': ('systin', 'motherboard')
                }.items() if any(k in name for k in keys)), None)
                if component:
                    self._record(temps, component, entry.current)
        return temps

    @staticmethod
    def _parse_sensor_temp(value: str) -> Optional[float]:
        """Extract temperature from lm-sensors output like '+45.0°C' or 'high = +80.0°C'."""
        try:
            clean_val = value.split('°C')[0].strip()
            # Find start of number
            start_idx = 0
            for k, char in enumerate(clean_val):
                if char.isdigit() or char in '+-.':
                    start_idx = k
                    break
            numeric_str = ''.join(c for c in clean_val[start_idx:] if c.isdigit() or c == '.' or c == '-')
            if not numeric_str:
                return None
            return float(numeric_str)
        except (ValueError, IndexError):
            return None

    def get_macos_temps(self):
        # Never invoke sudo or prompt for credentials from a sampling loop.
        temps = self._empty_temps()
        try:
            output = subprocess.check_output(
                ['powermetrics', '-n', '1', '-i', '1000'],
                stderr=subprocess.DEVNULL, timeout=SUBPROCESS_TIMEOUT,
            ).decode()
            for line in output.splitlines():
                for component in ('CPU', 'GPU'):
                    if component + ' die temperature' in line:
                        try:
                            self._record(temps, component, float(line.split(':')[1].split()[0]))
                        except (ValueError, IndexError):
                            continue
        except (OSError, subprocess.SubprocessError):
            logger.debug('macOS temperature sensors unavailable with current permissions')
        return temps

    def get_ram_temp(self) -> float:
        """Estimate RAM temperature based on memory usage."""
        memory = psutil.virtual_memory()
        # Higher memory usage generally correlates with higher temperature
        base_temp = 30.0
        max_temp_increase = 30.0
        return base_temp + (memory.percent / 100.0) * max_temp_increase

    def get_fallback_temps(self) -> Dict[str, float]:
        cpu_percent = float(psutil.cpu_percent())
        memory_percent = float(psutil.virtual_memory().percent)

        # Temperature estimates based on system load
        base_temps: Dict[str, float] = {
            'CPU': 35.0,
            'GPU': 35.0,
            'Motherboard': 30.0,
            'Storage': 25.0,
            'RAM': 30.0
        }

        return {
            'CPU': base_temps['CPU'] + (cpu_percent * 0.5),
            'GPU': base_temps['GPU'] + (cpu_percent * 0.4),
            'Motherboard': base_temps['Motherboard'] + (cpu_percent * 0.2),
            'Storage': base_temps['Storage'] + (cpu_percent * 0.15),
            'RAM': base_temps['RAM'] + (memory_percent * 0.3)
        }

    def get_readings(self):
        provider = {'Windows': self.get_windows_temps, 'Linux': self.get_linux_temps,
                    'Darwin': self.get_macos_temps}.get(self.system, self._empty_temps)
        temps = provider()
        source = {'Windows': 'OpenHardwareMonitor WMI', 'Linux': 'psutil/hwmon',
                  'Darwin': 'powermetrics'}.get(self.system, 'unavailable')
        self.readings = {c: Reading.temperature(v, source) for c, v in temps.items()}
        if temps['GPU'] is None and shutil.which('nvidia-smi'):
            if time.monotonic() - self._gpu_checked_at >= 2:
                from .monitor import GPUDetector
                values = [g['temperature'] for g in GPUDetector.get_nvidia_info()
                          if g.get('temperature') is not None]
                self._gpu_reading = Reading.temperature(max(values) if values else None, 'nvidia-smi')
                self._gpu_checked_at = time.monotonic()
            if self._gpu_reading is not None:
                self.readings['GPU'] = self._gpu_reading
        if self.estimates:
            estimates = self.get_fallback_temps()
            for component, reading in self.readings.items():
                if not reading.available:
                    self.readings[component] = Reading.temperature(estimates[component], 'estimate')
        return self.readings

    def get_system_temps(self):
        return {component: reading.value for component, reading in self.get_readings().items()}

    def format_temp(self, component, value):
        if value is None:
            return 'N/A'
        estimated = self.readings.get(component)
        suffix = ' (estimated)' if estimated and estimated.source == 'estimate' else ''
        return f'{value:.1f}°C{suffix}'

    def get_temp_char(self, temp: float) -> tuple:
        if temp is None or not np.isfinite(temp):
            return ('·', "dim")
        if temp < 45:
            return ('·', "green")
        elif temp < 70:
            return ('▒', "yellow")
        else:
            return ('█', "red")

    def update_component_map(self, component: str, temp: float):
        self.temp_maps[component] = np.full(self.components[component]['size'],
                                                 np.nan if temp is None else temp)

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

        schedule = Schedule(interval, duration)
        update_count = 0

        try:
            with Live(layout, refresh_per_second=2, screen=True):
                while True:
                    elapsed = schedule.elapsed
                    if schedule.finished:
                        break

                    temps = self.get_system_temps()
                    for component in ('CPU', 'GPU'):
                        if temps[component] is not None:
                            self.temp_history[component].add_point(temps[component])

                    # Update Layout
                    header = (
                        f"[bold cyan]Hardware Thermal Dashboard[/bold cyan] | "
                        f"[yellow]Elapsed: {int(elapsed)}s"
                        f"{f'/{duration}s' if duration else ''}[/yellow] | "
                        f"[green]{self.system}[/green]"
                    )
                    layout["header"].update(Panel(header, border_style="blue"))

                    layout["heatmap"].update(self.generate_system_layout(temps))

                    layout["cpu_graph"].update(Panel(
                        self.temp_history['CPU'].render(f"CPU Temp: {self.format_temp('CPU', temps['CPU'])}"),
                        title="CPU Thermal Trend", border_style="red"
                    ))
                    layout["gpu_graph"].update(Panel(
                        self.temp_history['GPU'].render(f"GPU Temp: {self.format_temp('GPU', temps['GPU'])}"),
                        title="GPU Thermal Trend", border_style="magenta"
                    ))

                    stats_table = Table(box=box.SIMPLE, expand=True)
                    stats_table.add_column("Component", style="cyan")
                    stats_table.add_column("Temp", style="yellow")
                    for comp, val in temps.items():
                        color = self.get_temp_char(val)[1]
                        stats_table.add_row(comp, f"[{color}]{self.format_temp(comp, val)}[/{color}]")

                    layout["stats"].update(Panel(stats_table, title="Current Temps", border_style="white"))

                    layout["footer"].update(Panel(
                        "[bold yellow]Press Ctrl + C to stop thermal monitoring[/bold yellow]",
                        border_style="blue",
                        title_align="center"
                    ))

                    update_count += 1
                    schedule.wait()
        except KeyboardInterrupt:
            pass

        return update_count

    def generate_system_layout(self, temps: Optional[Dict[str, Optional[float]]] = None) -> Panel:
        if temps is None:
            temps = self.get_system_temps()

        layout = [[' ' for _ in range(40)] for _ in range(25)]
        colors = [[None for _ in range(40)] for _ in range(25)]

        for component in sorted(self.components, key=lambda c: c != 'Motherboard'):
            info = self.components[component]
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
            label = f"{component[:3]} {self.format_temp(component, temps[component])}"
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
            title="Internal Thermal Map (component schematic)",
            border_style="blue"
        )
