[![Python package](https://github.com/dhanushk-offl/guro/actions/workflows/python-package.yml/badge.svg)](https://github.com/dhanushk-offl/guro/actions/workflows/python-package.yml)
# Guro - A Simple System Monitoring & Benchmarking Toolkit 🚀


Welcome to **Guro**, the ultimate toolkit for **system monitoring** and **benchmarking**. It’s simple, fast, and designed for developers and enthusiasts who want to monitor system performance, run benchmarks, and visualize system heatmaps in an intuitive way.

### Features:
- 📊 **Real-time system monitoring** – Monitor CPU, memory, and disk usage in real-time.
- 🔥 **Performance benchmarking** – Run benchmarks with mini and full-scale tests for your CPU and GPU.
- 🌡️ **Hardware heatmap** – Visualize your system's temperature with a heatmap in real-time.
- 💾 **Export data** – Export monitoring data to CSV for analysis.
  
### Installation

```bash
pipx install guro
```

### Usage

Run the following commands for monitoring, benchmarking, or heatmap analysis:

#### 1. **Monitor System Resources**
```bash
guro monitor --interval 1.0 --duration 60
```

#### 2. **Run Benchmark Tests**
```bash
guro benchmark --type mini --cpu-only
```

#### 3. **Visualize System Heatmap**
```bash
guro heatmap --interval 1.0 --duration 30
```

#### 4. **List All Commands**
```bash
guro list
```

For more details, check out our [documentation](https://github.com/dhanushk-offl/guro/wiki).

### Demo

[Watch the demo video here](https://www.youtube.com/watch?v=xyz123)

### License

MIT License. See LICENSE for more details.
