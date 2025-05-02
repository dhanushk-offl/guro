[![Python package](https://github.com/dhanushk-offl/guro/actions/workflows/python-package.yml/badge.svg)](https://github.com/dhanushk-offl/guro/actions/workflows/python-package.yml) [![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/dhanushk-offl/guro/badge)](https://scorecard.dev/viewer/?uri=github.com/dhanushk-offl/guro) [![CodeQL Advanced](https://github.com/dhanushk-offl/guro/actions/workflows/codeql.yml/badge.svg)](https://github.com/dhanushk-offl/guro/actions/workflows/codeql.yml) [![PyPI Downloads](https://img.shields.io/pypi/dm/guro.svg?label=PyPI%20downloads)](https://pypi.org/project/guro/) ![GitHub Sponsors](https://img.shields.io/github/sponsors/dhanushk-offl)


[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://buymeacoffee.com/itzmedhanu)

# Guro - A Simple System Monitoring & Benchmarking Toolkit 🚀

Welcome to **Guro**, the ultimate toolkit for **system monitoring** and **benchmarking**. It’s simple, fast, and designed for developers and enthusiasts who want to monitor system performance, run benchmarks, and visualize system heatmaps in an intuitive way.

### Features:
- 📊 **Real-time system monitoring** – Monitor CPU, memory, and disk usage in real-time.
- 🔥 **Performance benchmarking** – Run benchmarks with mini and full-scale tests for your CPU and GPU.
- 🌡️ **Hardware heatmap** – Visualize your system's temperature with a heatmap in real-time.
- 💾 **Export data** – Export monitoring data to CSV for analysis.
flowchart TD
    %% User Input Layer
    CLI["CLI Interface"]:::cli

    %% Core Modules
    subgraph "Core Modules"
        MON["Monitor Module"]:::core
        BEN["Benchmark Module"]:::core
        HMAP["Heatmap Module"]:::core
        EXPORT["Data Export"]:::export
    end

    %% External Systems
    subgraph "External Systems"
        OS["OS APIs"]:::external
        FS["File System"]:::external
    end

    %% Connections from CLI to Core Modules
    CLI -->|"trigger_monitor"| MON
    CLI -->|"trigger_benchmark"| BEN
    CLI -->|"trigger_heatmap"| HMAP

    %% Connections within Core Modules and External Systems
    MON -->|"collect_metrics"| OS
    MON -->|"export_data"| EXPORT
    EXPORT -->|"write_output"| FS
    BEN -->|"run_benchmarks"| OS
    HMAP -->|"generate_visual"| FS

    %% Click Events for Components
    click CLI "https://github.com/dhanushk-offl/guro/blob/master/src/guro/cli/main.py"
    click MON "https://github.com/dhanushk-offl/guro/blob/master/src/guro/core/monitor.py"
    click BEN "https://github.com/dhanushk-offl/guro/blob/master/src/guro/core/benchmark.py"
    click HMAP "https://github.com/dhanushk-offl/guro/blob/master/src/guro/core/heatmap.py"

    %% Styles
    classDef cli fill:#ffcccc,stroke:#990000,stroke-width:2px;
    classDef core fill:#cce5ff,stroke:#004085,stroke-width:2px;
    classDef export fill:#d4edda,stroke:#155724,stroke-width:2px;
    classDef external fill:#e2f0d9,stroke:#0b6623,stroke-width:2px;

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
