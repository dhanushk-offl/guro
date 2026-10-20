"""Read-only capability diagnostics; no privilege escalation or installation."""
import platform
import shutil

from .heatmap import SystemHeatmap
from .monitor import GPUDetector
from .network import NetworkMonitor
from .telemetry import timestamp


def capabilities():
    thermal = SystemHeatmap()
    network = NetworkMonitor()
    network._connection_snapshot()
    return {
        'timestamp': timestamp(),
        'platform': platform.system(),
        'tools': {name: shutil.which(name) is not None for name in
                  ('nvidia-smi', 'rocm-smi', 'lspci', 'powermetrics')},
        'temperatures': {name: reading.to_dict() for name, reading in thermal.get_readings().items()},
        'gpus': GPUDetector.get_all_gpus(),
        'tcp_connections': network.connection_status,
        'gpu_workload': 'unsupported',
        'notes': [
            'Missing temperature sensors are reported as unavailable.',
            'Windows temperatures require OpenHardwareMonitor WMI sensors.',
            'macOS powermetrics may require permission granted outside Guro.',
        ],
    }
