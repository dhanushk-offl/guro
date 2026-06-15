# Guro Release Notes 🚀

## v1.2.0 — Network Intelligence
*June 15, 2026*

**New** — Real-time network monitoring with bandwidth sparklines, TCP state analysis, process-level connection tracking, and protocol statistics. Zero additional dependencies.

### 🌐 What's New?

#### 📡 Network Dashboard
- Multi-pane live TUI with per-interface bandwidth history, adapter specs, and protocol stats.
- Dedicated Bandwidth History panel with 30-sample upload/download sparklines and current speed values.
- `guro network --speed` — single-shot speed snapshot across all active interfaces.
- `guro network --interfaces` — full adapter listing with IP, MAC, speed, duplex.
- `guro network --connections` — active TCP connections with PID, process, and remote address.

#### 🖧 TCP & Protocol Analysis
- Real-time TCP state distribution (ESTABLISHED, LISTEN, TIME_WAIT, etc.).
- Retransmission ratio from `/proc/net/snmp` on Linux.
- Per-connection process resolution with graceful permission fallback.

#### 📦 Export & CSV Logging
- `guro network --export` / `-e` flag to log bandwidth data to timestamped CSV files.

#### 🛠️ Removed
- `guro network --test` (speed test) has been removed to keep the module focused on real-time monitoring.

### 👩‍💻 Installation
```bash
pip install guro --upgrade
```

## v1.1.3 - Release Updates
*February 04, 2026*

This version includes minor version updates and configuration synchronizations.

## v1.1.2 - The "Cult & Classic" Dashboard Release
*February 04, 2026*

This release marks a significant evolution for Guro, transitioning from a basic terminal tool to a high-fidelity monitoring dashboard. We've focused on visual excellence, real-time accuracy, and robust hardware support.

### ✨ What's New?

#### 📊 Overhauled Monitoring Dashboard
- Switched to a multi-pane layout using `rich.layout`.
- Added **Live ASCIIGraphs** for real-time CPU and Memory usage history.
- Improved multi-threaded update logic for smoother, flicker-free rendering.
- Organized process table and GPU details into distinct UI panels.

#### 🌡️ Premium Thermal Heatmap
- Re-engineered the heatmap with a new dashboard view.
- Added synchronized thermal trend graphs for CPU and GPU side-by-side with the map.
- Improved temperature parsing accuracy for Linux (`lm-sensors`) and Windows (`WMI`).
- Category-based robust extraction removes reliance on fragile output order.

#### 🚀 Enhanced Multi-GPU Support
- Robust detection for NVIDIA, AMD, and Integrated GPUs across all platforms.
- Per-device metrics (Temperature, Load, Memory, Power) now visible in all monitoring modes.
- Fixed multi-GPU statistics collection during benchmarking.

#### 📦 Performance & Maintenance
- **Lean Installation**: Streamlined `setup.py` to only install essential production dependencies. Moved heavy libraries (matplotlib, plotly, pandas) out of the core requirements to keep the package small and fast.
- **Improved Testing**: Achieved 100% test passing status with a new robust mocking suite for simulated hardware environments.
- **Version Synchronization**: All CLI components and about pages are now synchronized to v1.1.2.

### 🛠️ Bug Fixes
- Fixed `NameError` in heatmap and monitor loops.
- Fixed `TypeError` in benchmark loop when GPU stats were mocked.
- Resolved "flickering" issues in long-duration monitoring.
- Corrected coordinate mapping in the system thermal layout.

### 👩‍💻 Installation
```bash
pip install guro --upgrade
```

---
*Guro: A Simple System Monitoring & Benchmarking Toolkit.*
