# Thermal acquisition and display

Linux temperatures come from psutil's hwmon sensor readings. Sensors are categorized by device and label, using the highest valid reading within each component. Windows uses temperature sensors exposed through OpenHardwareMonitor WMI. macOS attempts powermetrics with existing permissions; Guro never invokes sudo or prompts for credentials. NVIDIA GPU temperatures are queried through nvidia-smi when the platform provider lacks a GPU reading and are cached for two seconds with their original acquisition timestamp.

Every reading carries its unit, source, timestamp, and availability. Values outside -50 to 150 Celsius and nonfinite values are rejected. Missing components display N/A. Passing `--estimates` fills only missing readings with explicitly labeled utilization-based estimates. Real measurements always take precedence, including measurements below the estimated value.

The fixed schematic shows one aggregate temperature per component. Cells have uniform values; there is no generated noise or claim of measured spatial variation. The motherboard background is drawn before foreground components. History contains measured values, or labeled estimates only when requested.

The heatmap provides color thresholds for display. Benchmark stop conditions are implemented separately and never use estimates. Unsupported sensors remain unavailable, so thermal coverage must be read alongside benchmark results.
