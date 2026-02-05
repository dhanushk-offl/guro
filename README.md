<div align="center">

# Guro: A System Tool-kit for Real-time Monitoring and Analysis
**Professional real-time monitoring, thermal analysis, and hardware benchmarking.**

[![Python package](https://github.com/dhanushk-offl/guro/actions/workflows/python-package.yml/badge.svg)](https://github.com/dhanushk-offl/guro/actions/workflows/python-package.yml)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/dhanushk-offl/guro/badge)](https://scorecard.dev/viewer/?uri=github.com/dhanushk-offl/guro)
[![CodeQL Advanced](https://github.com/dhanushk-offl/guro/actions/workflows/codeql.yml/badge.svg)](https://github.com/dhanushk-offl/guro/actions/workflows/codeql.yml)
[![PyPI version](https://img.shields.io/pypi/v/guro.svg)](https://pypi.org/project/guro/)
[![PyPI Downloads](https://img.shields.io/pypi/dm/guro.svg?label=PyPI%20downloads)](https://pypi.org/project/guro/)
[![License: MIT](https://img.shields.io/badge/License-MIT-gray.svg)](https://opensource.org/licenses/MIT)
[![GitHub Stars](https://img.shields.io/github/stars/dhanushk-offl/guro.svg?style=social&label=Star&maxAge=2592000)](https://github.com/dhanushk-offl/guro)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-Donate-orange.svg)](https://buymeacoffee.com/itzmedhanu)

</div>

---

## Overview

Guro is a sophisticated terminal-based diagnostic toolkit designed for granular system resource monitoring and hardware analysis. Built for engineers and enthusiasts, it provides a desktop-class dashboard experience within the command-line environment, delivering precise telemetry across Linux, macOS, and Windows.

---

## Visual Presentation

### 1. Performance Telemetry View
![Performance Dashboard](https://res.cloudinary.com/dwir71gi2/image/upload/v1770200721/monitor_dashboard_odhdgo.png)
*High-concurrency monitoring of CPU cores, memory allocation, and active process telemetry*

### 2. Hardware Thermal Schematic
![Thermal Heatmap](https://res.cloudinary.com/dwir71gi2/image/upload/v1770200720/thermal_heatmap_x4mcib.png)
*Spatial temperature mapping across integrated hardware components with synchronized trend analysis.*

---

## Key Capabilities

### Intelligent Monitoring
The performance module utilizes high-frequency sampling to provide real-time ASCII-based historic trending. It offers a comprehensive view of system load including individual core utilization and physical/virtual memory envelopes.

### Thermal Intelligence
Guro implements a robust, regex-free data acquisition layer for hardware sensors. By interfacing directly with `lm-sensors` on Linux and `WMI` on Windows, it provides reliable thermal mapping even across diverse kernel and driver versions.

### Hardware-Agnostic Benchmarking
The benchmarking suite is designed with hardware safety as a priority. It ensures system stability by monitoring thermal thresholds during heavy load tests. It features full awareness for NVIDIA, AMD, and Integrated graphics solutions.

---

## Installation

### Standard Method
```bash
pip install guro
```

### Isolated Environment (Recommended)
```bash
pipx install guro
```

---

## Operational Interface

Access Guro via its unified command-line interface.

| Module | Command | Description |
| :--- | :--- | :--- |
| **Monitor** | `guro monitor` | Launches the interactive system performance dashboard. |
| **Thermal** | `guro heatmap` | Initiates spatial hardware heatmapping and trend analysis. |
| **Graphics** | `guro gpu` | Executes a diagnostic status report for all detected GPUs. |
| **Bench** | `guro benchmark` | Performs high-load system stability and speed testing. |

---

## Community and Development

Guro is an open-source project that adheres to professional development standards.

- **Developer Guide**: Comprehensive guidelines can be found in [CONTRIBUTING.md](CONTRIBUTING.md).
- **Architecture**: In-depth module analysis is available in the project documentation.
- **License**: Released under the MIT License.
- **Support**: [Buy Me A Coffee](https://buymeacoffee.com/itzmedhanu)

### Star History

[![Star History Chart](https://api.star-history.com/svg?repos=dhanushk-offl/guro&type=Date)](https://star-history.com/#dhanushk-offl/guro&Date)

---

<div align="center">
Developed with ❤️ by <b>Dhanush Kandhan</b>.
</div>
