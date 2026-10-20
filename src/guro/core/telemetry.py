"""Shared measurement, scheduling, and streaming output primitives."""
import csv
import datetime
import json
import math
import time
from dataclasses import asdict, dataclass
from typing import Optional


def timestamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


@dataclass(frozen=True)
class Reading:
    value: Optional[float]
    unit: str
    source: str
    timestamp: str
    available: bool

    @classmethod
    def temperature(cls, value, source):
        valid = value is not None and math.isfinite(value) and -50 <= value <= 150
        return cls(float(value) if valid else None, 'celsius', source,
                   timestamp(), valid)

    def to_dict(self):
        return asdict(self)


def validate_sampling(interval, duration):
    if not math.isfinite(interval) or interval <= 0:
        raise ValueError('Interval must be finite and positive')
    if duration is not None and (not math.isfinite(duration) or duration <= 0):
        raise ValueError('Duration must be finite and positive')


class Schedule:
    """Keep samples on monotonic deadlines, skipping missed ticks."""
    def __init__(self, interval, duration):
        validate_sampling(interval, duration)
        self.interval = interval
        self.start = time.monotonic()
        self.deadline = None if duration is None else self.start + duration
        self.next_tick = self.start

    @property
    def elapsed(self):
        return time.monotonic() - self.start

    @property
    def finished(self):
        return self.deadline is not None and time.monotonic() >= self.deadline

    def wait(self):
        now = time.monotonic()
        self.next_tick += self.interval
        if self.next_tick < now:
            self.next_tick += (math.floor((now - self.next_tick) / self.interval) + 1) * self.interval
        target = min(self.next_tick, self.deadline) if self.deadline is not None else self.next_tick
        time.sleep(max(0, target - now))


class SampleWriter:
    """Write each row immediately; never retain the session in memory."""
    def __init__(self, stream, fmt, fields=None):
        self.stream = stream
        self.fmt = fmt
        self.first = True
        self.csv = csv.DictWriter(stream, fieldnames=fields) if fmt == 'csv' else None

    def __enter__(self):
        if self.csv:
            self.csv.writeheader()
        elif self.fmt == 'json':
            self.stream.write('[')
        self.stream.flush()
        return self

    def write(self, row):
        if self.csv:
            self.csv.writerow(row)
        elif self.fmt == 'json':
            self.stream.write(('' if self.first else ',') + json.dumps(row, allow_nan=False))
        else:
            self.stream.write(json.dumps(row, allow_nan=False) + '\n')
        self.first = False
        self.stream.flush()

    def __exit__(self, *exc):
        if self.fmt == 'json':
            self.stream.write(']\n')
        self.stream.flush()
