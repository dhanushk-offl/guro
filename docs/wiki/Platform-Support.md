# Platform Support and Requirements

Guro is engineered for broad compatibility across major operating systems. Technical implementations vary by platform to leverage native diagnostic interfaces.

## Compatibility Matrix

| Operating System | Information Interface | Thermal Acquisition | GPU Support |
| :--- | :--- | :--- | :--- |
| **Windows** | Win32 API / psutil | WMI (MSAcpi) | NVIDIA (NVML), AMD, Intel |
| **Linux** | sysfs / procfs | lm-sensors / sysfs | NVIDIA, AMD (ROCm), Intel |
| **macOS** | Mach / Grand Central | SMC / powermetrics | Apple Silicon, AMD |

## Requirements

### Python Environment
- **Version**: Python 3.7+ is mandatory.
- **Virtualization**: Highly recommended to use `venv` or `pipx` to avoid dependency conflicts.

### System Permissions
- **Linux**: Reading thermal data from `sysfs` may require the user to be in the `video` or `hwmon` group, or require `sudo` for certain sensor chips.
- **Windows**: WMI queries for thermal data often require administrative privileges.
- **macOS**: `powermetrics` and SMC access require elevated standard permissions.

## Dependency Management

Guro minimizes its core footprint by separating diagnostic requirements from optional visualization libraries.
- **Core**: `click`, `rich`, `psutil`, `gputil`, `numpy`, `py-cpuinfo`.
- **NVIDIA Dedicated**: `nvidia-ml-py`.
- **AMD Dedicated**: `pyamdgpuinfo` (Linux specific).
