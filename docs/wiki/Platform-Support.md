# Platform support

Python 3.9 or later is required. Runtime dependencies are declared in pyproject.toml; use pipx or a virtual environment for installation.

| Platform | System/process monitoring | Temperature acquisition | GPU discovery and metrics |
| :--- | :--- | :--- | :--- |
| Linux | psutil | psutil/hwmon; NVIDIA fallback | nvidia-smi, ROCm JSON, lspci adapter fallback |
| Windows | psutil | OpenHardwareMonitor WMI | nvidia-smi and WMI adapter fallback |
| macOS | psutil | powermetrics with existing permissions | No native Apple GPU discovery provider |

Missing tools and sensors are optional: their values remain unavailable. Guro never installs tools or invokes sudo automatically. TCP connection inspection may be denied by the OS and is reported separately from an empty connection list. Linux protocol counters come from /proc/net/snmp; these are unavailable on other systems.

Run `guro doctor` for actual capabilities on the current machine. CI covers Linux Python versions and Windows/macOS Python 3.12. Passing mocked provider tests does not establish real-hardware coverage for every driver or GPU model.

Core dependencies are Click, Rich, psutil, NumPy, and a Pygments minimum inherited from the existing requirements. Windows additionally installs WMI. Optional extras remain available for compatibility, but current GPU collection uses vendor commands rather than the optional Python bindings.

The minimum Python version is 3.9 to match the existing Pygments 2.20 security requirement, which does not support Python 3.8.
