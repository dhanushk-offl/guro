[![Python package](https://github.com/dhanushk-offl/guro/actions/workflows/python-package.yml/badge.svg)](https://github.com/dhanushk-offl/guro/actions/workflows/python-package.yml)
# Guro - A Simple System Monitoring & Benchmarking Toolkit 🚀

Welcome to **Guro**, the ultimate toolkit for **system monitoring** and **benchmarking**. It’s simple, fast, and designed for developers and enthusiasts who want to monitor system performance, run benchmarks, and visualize system heatmaps in an intuitive way.

### Features:
- 📊 **Real-time system monitoring** – Monitor CPU, memory, and disk usage in real-time.
- 🔥 **Performance benchmarking** – Run benchmarks with mini and full-scale tests for your CPU and GPU.
- 🌡️ **Hardware heatmap** – Visualize your system's temperature with a heatmap in real-time.
- 💾 **Export data** – Export monitoring data to CSV for analysis.

### Installation

For General Installation:
```bash
pip install guro
```

For **Linux** & **MacOS** users, we recommend installing via `pipx` for better isolation or use can virtual environments:
```bash
pipx install guro
```

For **Windows** users, use a virtual environment to manage the CLI-based package:
```bash
python -m venv guro_env
source guro_env/bin/activate  # On Windows: guro_env\Scripts\activate
pip install guro
```

### Usage

Run the following commands for monitoring, benchmarking, or heatmap analysis:

#### 1. **Monitor System Resources**
```bash
guro monitor --interval 1.0 --duration 60
```
- **Options**:
  - `--interval/-i`: Monitoring interval in seconds (default: 1.0).
  - `--duration/-d`: Monitoring duration in seconds.
  - `--export/-e`: Export monitoring data to a CSV file.

#### 2. **Run Benchmark Tests**
```bash
guro benchmark --type mini --cpu-only
```
- **Options**:
  - `--type/-t`: Type of benchmark test to run (`mini` or `god`).
  - `--cpu-only`: Run only CPU benchmark.
  - `--gpu-only`: Run only GPU benchmark.

#### 3. **Visualize System Heatmap**
```bash
guro heatmap --interval 1.0 --duration 30
```
- **Options**:
  - `--interval/-i`: Update interval in seconds (must be greater than 0.1).
  - `--duration/-d`: Duration to run in seconds (default: 10).

#### 4. **List All Commands**
```bash
guro list
```
- Displays all available commands and options for the toolkit.

#### 5. **About Guro**
```bash
guro about
```
- Displays information about Guro, including version, author, and features.


### License

MIT License. See [[LICENSE](https://github.com/dhanushk-offl/guro/LICENSE)] for more details.

For more details, check out our [[documentation](https://github.com/dhanushk-offl/guro/wiki)].
