# Guro Technical Wiki

Welcome to the technical documentation for Guro. This wiki provides in-depth analysis of the toolkit's architecture, methodologies, and operational protocols.

## Table of Contents

- [Home](Home.md)
- [System Monitoring Architecture](Architecture-Monitoring.md)
- [Thermal Analysis Methodology](Architecture-Thermal.md)
- [Benchmarking Protocols](Architecture-Benchmarking.md)
- [Network Monitoring Architecture](Architecture-Network.md)
- [Platform Implementation Details](Platform-Support.md)
- [Troubleshooting and Diagnostics](Troubleshooting.md)
- [Collector Performance Measurements](../PERFORMANCE_REVIEW.md)

## Diagnostics and structured output

Start with `guro doctor` to see which sensors, tools, and permissions are available on the current system. For automation, use `--format json` or `--format jsonl` and optionally `--output PATH`. Monitoring exports stream each sample; temperature readings include their source, timestamp, and availability.

See the repository [README](../../README.md#structured-output-and-exports) for command examples and the [release notes](../../RELEASE_NOTES.md) for compatibility changes and validation results.

## Project Links

- **Website**: [guro.pages.dev](https://guro.pages.dev/)
- **Source Code**: [github.com/dhanushk-offl/guro](https://github.com/dhanushk-offl/guro)
- **Issue Tracker**: [github.com/dhanushk-offl/guro/issues](https://github.com/dhanushk-offl/guro/issues)

## Project Vision

Guro is designed to provide high-fidelity system telemetry in a lightweight, terminal-based format — including real-time network bandwidth monitoring, TCP state analysis, and connection tracking. By prioritizing robust data acquisition and structured visualization, Guro serves as a reliable diagnostic bridge between low-level system sensors and the end-user.

## Technical Standards

Guro adheres to the following principles:
- **Accuracy**: Regex-free parsing of system outputs where feasible.
- **Efficiency**: Minimal resource overhead during monitoring.
- **Portability**: Cross-platform compatibility across Windows, Linux, and macOS.
- **Clarity**: High-density information display using advanced TUI layouts.
