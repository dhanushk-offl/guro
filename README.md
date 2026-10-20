<div align="center">

# Guro: A System Tool-kit for Real-time Monitoring and Analysis
**Professional real-time monitoring, thermal analysis, and hardware benchmarking.**

[![Python package](https://github.com/dhanushk-offl/guro/actions/workflows/python-package.yml/badge.svg)](https://github.com/dhanushk-offl/guro/actions/workflows/python-package.yml)
[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/dhanushk-offl/guro/badge)](https://scorecard.dev/viewer/?uri=github.com/dhanushk-offl/guro)

[![Known Vulnerabilities](https://snyk.io/test/github/dhanushk-offl/guro/badge.svg)](https://snyk.io/test/github/dhanushk-offl/guro)
[![CodeQL Advanced](https://github.com/dhanushk-offl/guro/actions/workflows/codeql.yml/badge.svg)](https://github.com/dhanushk-offl/guro/actions/workflows/codeql.yml)
[![PyPI version](https://img.shields.io/pypi/v/guro.svg)](https://pypi.org/project/guro/)
[![Total Downloads](https://pepy.tech/badge/guro)](https://clickpy.clickhouse.com/dashboard/guro)
[![Monthly Downloads](https://img.shields.io/pypi/dm/guro.svg?label=Monthly%20downloads)](https://pypi.org/project/guro/)
[![License: MIT](https://img.shields.io/badge/License-MIT-gray.svg)](https://opensource.org/licenses/MIT)
[![GitHub Stars](https://img.shields.io/github/stars/dhanushk-offl/guro.svg?style=social&label=Star&maxAge=2592000)](https://github.com/dhanushk-offl/guro)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-Donate-orange.svg)](https://buymeacoffee.com/itzmedhanu)

</div>

---

## Overview

Guro is a sophisticated terminal-based diagnostic toolkit designed for granular system resource monitoring and hardware analysis. Built for engineers and enthusiasts, it provides a desktop-class dashboard experience within the command-line environment, delivering telemetry across Linux, macOS, and Windows, with explicit availability reporting for unsupported sensors.

🌐 **Website**: [guro.pages.dev](https://guro.pages.dev/)

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
The performance module utilizes high-frequency sampling to provide real-time ASCII-based historic trending. It shows aggregate CPU utilization, memory usage, GPU metrics where supported, and the ten processes using the most CPU.

### Thermal Intelligence
Guro reads Linux hwmon sensors through psutil, OpenHardwareMonitor WMI sensors on Windows, and available powermetrics readings on macOS. NVIDIA temperatures can also come from nvidia-smi. Missing readings display as `N/A`. The heatmap is a component schematic; its cells do not represent independently measured spatial temperatures. Optional estimates require `--estimates` and are labeled.

### Hardware-Agnostic Benchmarking
CPU benchmarks report NumPy/BLAS matrix throughput; memory benchmarks report copy bandwidth using reusable buffers capped at 32 MiB and 1% of available memory. Runs stop at 90% system memory use or a measured component temperature of 90°C. Thermal coverage depends on exposed sensors and is included in the report. GPU workloads are currently unsupported; `guro gpu` provides device telemetry.

### Network Intelligence
Real-time bandwidth monitoring with per-interface upload/download sparklines, TCP state distribution (ESTABLISHED, LISTEN, TIME_WAIT, etc.), process-level connection tracking, and `/proc/net/snmp` protocol statistics — all with zero additional dependencies beyond psutil.

---

## Installation

Current release: **1.1.7**. See the [detailed release notes](RELEASE_NOTES.md#v117--trustworthy-telemetry-bounded-benchmarks-and-diagnostics).

Requires Python 3.9 or newer.

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
| **Doctor** | `guro doctor` | Reports tools, sensor availability, connection permissions, and GPU capabilities. |
| **Monitor** | `guro monitor` | Launches the interactive system performance dashboard. |
| **Thermal** | `guro heatmap` | Initiates spatial hardware heatmapping and trend analysis. |
| **Graphics** | `guro gpu` | Executes a diagnostic status report for all detected GPUs. |
| **Bench** | `guro benchmark` | Performs high-load system stability and speed testing. |
| **Network** | `guro network` | Real-time dashboard: bandwidth, adapters, TCP states, connections. |
| | `guro network --speed` | Snapshot of current upload/download speeds on all interfaces. |
| | `guro network --interfaces` | List all network adapters with IP, MAC, speed, and duplex. |
| | `guro network --connections` | Show active TCP connections with process names and states. |

---

## Structured output and exports

```bash
guro doctor --format json
guro monitor --duration 10 --format jsonl --output samples.jsonl
guro heatmap --duration 10 --format json --output temperatures.json
guro network --duration 10 --export --output bandwidth.csv
guro gpu --format json
guro benchmark --type mini --cpu-only --format json --output benchmark.json
```

`--format json` writes a JSON array for monitoring sessions and a single JSON value for snapshots and benchmark reports. `jsonl` writes one JSON value per line. Structured output contains no banners or status spinners. `--output` writes to a file; otherwise structured output goes to stdout. Errors go to stderr and return a nonzero exit status. Existing destination files are replaced.

CSV (`--export`) and structured monitoring exports stream and flush each sample. Recent dashboard history is bounded to 60 samples. JSON arrays close on normal completion, Ctrl+C, and handled collection errors; use JSONL for recovery after abrupt process termination. Network speed pairs are `[upload_bytes_per_second, download_bytes_per_second]`. Connection permissions are reported separately from an empty connection list. Network totals may include virtual and loopback interfaces.

Temperature objects include `value` (null when unavailable), `unit`, `source`, `timestamp`, and `available`. `--estimates` affects only missing heatmap readings; measured readings always take precedence. Estimates are excluded from benchmark safety decisions.

`mini` and `god` request total budgets of 30 and 60 seconds. Default runs split time between CPU and memory workloads; `--cpu-only` uses the full budget for CPU. Collection and individual operations can overrun a deadline. Reports include actual elapsed time, configuration, and an explicit completion/abort outcome. GPU-only requests return `unsupported` with a nonzero status. Throughput excludes telemetry time; results depend on the NumPy/BLAS build, thread settings, cache behavior, and background load. Memory copy MB/s counts payload bytes copied, not combined read/write bus traffic.

## Roadmap

> 🚀 **Coming soon — PRs, ideas, and discussions are warmly welcomed!**

| Area | Description |
| :--- | :--- |
| **GPU Benchmarking** 🎮 | **⚠️ NEEDS CONTRIBUTORS!** — Native CUDA benchmarks for NVIDIA GPUs: compute performance, memory bandwidth, and thermal profiling. [Want to help?](https://github.com/dhanushk-offl/guro/issues) |
| **Network Diagnostics** 🌐 | ✅ **Done** — Live dashboard with bandwidth sparklines, adapter specs, TCP state analysis, and active connection tracking. |
| **Storage I/O** 💾 | Real-time disk throughput, IOPS, and queue-depth monitoring for server environments. |

Have a feature in mind? [Open an issue](https://github.com/dhanushk-offl/guro/issues) or start a discussion — every idea counts.

### 💖 Why Funding Matters

Testing system-level tooling demands real hardware — high-end GPUs, multi-CPU servers, and diverse cloud VMs for cross-platform validation. Your support helps rent these environments so Guro can be tested thoroughly across Linux, macOS, and Windows.

---

## Community and Development

Guro is an open-source project that adheres to professional development standards.

- **Website**: [guro.pages.dev](https://guro.pages.dev/)
- **Developer Guide**: Comprehensive guidelines can be found in [CONTRIBUTING.md](CONTRIBUTING.md).
- **Architecture**: In-depth module analysis is available in the project documentation.
- **License**: Released under the MIT License.
- **Support**: [GitHub Sponsors](https://github.com/sponsors/dhanushk-offl) · [Buy Me A Coffee](https://buymeacoffee.com/itzmedhanu)

### Star History

[![Star History Chart](https://api.star-history.com/svg?repos=dhanushk-offl/guro&type=Date)](https://star-history.com/#dhanushk-offl/guro&Date)

---

<div align="center">
Developed with ❤️ by <b>Dhanush Kandhan</b>.
</div>
