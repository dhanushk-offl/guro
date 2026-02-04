# Benchmarking Protocols

The benchmarking module in Guro is designed to assess system stability and performance under controlled stress conditions.

## Methodology

Guro implements a tiered benchmarking approach, allowing for varying levels of resource intensity.

### 1. Mini-Benchmark
- **Duration**: 30 seconds.
- **Scope**: Targeted stress test of the primary CPU cores and discovered discrete graphics units.
- **Objective**: Rapid verification of system stability and basic performance indexing.

### 2. God-Mode Benchmark
- **Duration**: 60 seconds.
- **Scope**: Comprehensive saturation of all available system resources (CPU threads, maximum VRAM allocation, and peak GPU core clock stimulation).
- **Objective**: Full-scale performance analysis and thermal stability validation.

## Resource Safety Engine

To prevent hardware damage, the benchmark engine includes a real-time safety monitor:
- **Throttling Detection**: Monitors for frequency drops indicates thermal throttling.
- **Safety Exit**: If the system exceeds pre-defined thermal safety thresholds, the benchmark is automatically terminated.

## Reporting Architecture

Upon completion of a benchmark run, Guro generates a technical summary including:
- **Peak vs. Average Utilization**: Highlights performance consistency.
- **Thermal Delta**: Measures the temperature increase from idle to peak load.
- **Memory Bandwidth Analysis**: Reports on VRAM and system RAM throughput efficiency.
