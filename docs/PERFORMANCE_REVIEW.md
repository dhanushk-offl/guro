# Collector performance checks

Measured locally on Linux with Python 3.14, comparing the original master monitor against this branch. These measurements describe collector overhead, not hardware benchmark scores.

| Check | Original | Updated |
| :--- | ---: | ---: |
| Median process-table collection/render time, seven samples | 51.860 ms | 0.472 ms |
| Peak traced Python allocations for 20,000 network export rows | 5,717,154 bytes | 270,094 bytes |

The process-table comparison loaded the original monitor source from Git, disabled GPU discovery for both implementations, and timed `_get_process_table()` with `perf_counter`. The original method sleeps for 50 ms and scans processes twice; the updated method uses persistent psutil counters and one scan. Initial process CPU deltas can be zero until a second sample is available.

The export check used tracemalloc with identical generated rows. The original behavior retained every row in a list. The updated behavior wrote rows through SampleWriter to a temporary CSV and retained a deque of at most 60 rows. This measures Python allocations, not total RSS or OS filesystem cache. Each row is flushed for recoverability, so storage latency remains part of export cost.

Regression tests also assert one TCP enumeration per network snapshot, one process-name lookup per PID within a snapshot, bounded history, monotonic scheduling, and no artificial process-sampling sleep. End-to-end CPU use and timing vary with process count, interface count, available sensors, vendor tools, terminal size, and output storage.
