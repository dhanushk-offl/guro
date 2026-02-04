# Guro Release Notes 🚀

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
