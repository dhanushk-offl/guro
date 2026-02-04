# Thermal Analysis Methodology

Guro's thermal module provides a spatial and temporal analysis of hardware temperature envelopes.

## Acquisition Protocols

Thermal metrics are retrieved through platform-specific diagnostic interfaces:

### Linux (sysfs/lm-sensors)
Guro parses the output of `sensors` (from the `lm-sensors` package). The implementation prioritizes category-based data extraction over line-based parsing to ensure resilience against varying sensor chip naming conventions across motherboard manufacturers.

### Windows (WMI)
On Windows environments, Guro interfaces with Windows Management Instrumentation (WMI) via the `wmi` Python wrapper. It specifically targets the `MSAcpi_ThermalZoneTemperature` and `Win32_TemperatureProbe` classes where available.

### macOS (SMC)
Thermal data on macOS is acquired through the System Management Control (SMC) interface via `powermetrics` or specialized binary calls.

## Spatial Heatmapping

The TUI generates a localized schematic of the hardware environment. Temperatures are mapped to a 2D coordinate system representing:
- **CPU Cores**: Thermal metrics are mapped to a central processing block.
- **Memory Arrays**: Visualized as modular blocks flanking the CPU.
- **Graphics Units**: Dynamically added based on the count of discovered discrete GPUs.

## Safety Thresholds

The module monitors for critical thermal events. If a component exceeds a predefined safety threshold (typically 90°C), a visual warning is triggered in the TUI to inform the user of potential thermal throttling.
