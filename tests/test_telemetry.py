import io
import json
from unittest.mock import Mock, patch

import pytest

from guro.core.heatmap import SystemHeatmap
from guro.core.monitor import GPUDetector
from guro.core.telemetry import Reading, SampleWriter, Schedule


def test_unavailable_temperatures_stay_missing():
    heatmap = SystemHeatmap()
    heatmap.system = 'unknown'
    with patch('guro.core.heatmap.shutil.which', return_value=None):
        readings = heatmap.get_readings()
    assert all(r.value is None and not r.available for r in readings.values())
    assert heatmap.format_temp('CPU', None) == 'N/A'


def test_estimates_are_opt_in_and_labeled():
    heatmap = SystemHeatmap(estimates=True)
    heatmap.system = 'unknown'
    with patch('guro.core.heatmap.shutil.which', return_value=None):
        readings = heatmap.get_readings()
    assert all(r.source == 'estimate' for r in readings.values())
    assert 'estimated' in heatmap.format_temp('CPU', 40)


def test_low_measured_temperature_wins_over_estimate():
    heatmap = SystemHeatmap(estimates=True)
    heatmap.system = 'Windows'
    heatmap.wmi_connection = Mock()
    heatmap.wmi_connection.Sensor.return_value = [Mock(Name='CPU Package', SensorType='Temperature', Value=40)]
    with patch.object(heatmap, 'get_fallback_temps', return_value={c: 80 for c in heatmap.components}):
        reading = heatmap.get_readings()['CPU']
    assert reading.value == 40
    assert reading.source != 'estimate'


@pytest.mark.parametrize('value', [float('nan'), float('inf'), 200, -100, None])
def test_invalid_reading_is_unavailable(value):
    assert not Reading.temperature(value, 'test').available


def test_linux_hwmon_selects_hottest_real_cpu_and_nvme():
    heatmap = SystemHeatmap()
    with patch('psutil.sensors_temperatures', create=True, return_value={
        'coretemp': [Mock(label='Core 0', current=32), Mock(label='Package id 0', current=40)],
        'nvme': [Mock(label='Composite', current=38)],
    }):
        temps = heatmap.get_linux_temps()
    assert temps['CPU'] == 40
    assert temps['Storage'] == 38
    assert temps['GPU'] is None


def test_heatmap_has_no_random_variation():
    heatmap = SystemHeatmap()
    heatmap.update_component_map('CPU', 40)
    assert (heatmap.temp_maps['CPU'] == 40).all()


def test_space_separated_pci_output_and_identity():
    with patch('platform.system', return_value='Linux'), patch('subprocess.check_output', return_value='00:02.0 "VGA compatible controller" "Intel Corporation" "UHD Graphics"\n'):
        gpus = GPUDetector.get_integrated_info()
    assert len(gpus) == 1
    assert gpus[0]['name'] == 'Intel Corporation UHD Graphics'
    assert gpus[0]['id'] == '00:02.0'


def test_gpu_deduplication_by_bus_instead_of_name():
    with patch.object(GPUDetector, 'get_nvidia_info', return_value=[{'name': 'NVIDIA RTX', 'id': '00000000:01:00.0'}]), patch.object(GPUDetector, 'get_amd_info', return_value=[]), patch.object(GPUDetector, 'get_integrated_info', return_value=[{'name': 'Other description', 'id': '01:00.0'}]):
        assert len(GPUDetector.get_all_gpus()['gpus']) == 1


@pytest.mark.parametrize('fmt', ['json', 'jsonl', 'csv'])
def test_stream_flushes_and_preserves_rows_on_error(fmt):
    stream = io.StringIO()
    with pytest.raises(RuntimeError):
        with SampleWriter(stream, fmt, ['value']) as writer:
            writer.write({'value': 1})
            assert '1' in stream.getvalue()
            raise RuntimeError('collection failed')
    if fmt == 'json':
        assert json.loads(stream.getvalue()) == [{'value': 1}]
    elif fmt == 'jsonl':
        assert json.loads(stream.getvalue().strip()) == {'value': 1}
    else:
        assert stream.getvalue().splitlines() == ['value', '1']


def test_schedule_deducts_collection_time_and_clamps_to_duration():
    with patch('guro.core.telemetry.time.monotonic', side_effect=[0, 0.4, 1.8]), patch('guro.core.telemetry.time.sleep') as sleep:
        schedule = Schedule(1, 1.5)
        schedule.wait()
        assert sleep.call_args.args[0] == pytest.approx(0.6)
        schedule.wait()
        assert sleep.call_args.args[0] == 0


@pytest.mark.parametrize('interval,duration', [(0, 1), (-1, 1), (float('nan'), 1), (1, 0), (1, float('inf'))])
def test_invalid_schedule_rejected(interval, duration):
    with pytest.raises(ValueError):
        Schedule(interval, duration)


def test_nvidia_temperature_cache_preserves_acquisition_time():
    heatmap = SystemHeatmap()
    heatmap.system = 'unknown'
    with patch('guro.core.heatmap.shutil.which', return_value='/bin/nvidia-smi'), patch.object(GPUDetector, 'get_nvidia_info', return_value=[{'temperature': 42}]) as detector:
        first = heatmap.get_readings()['GPU']
        second = heatmap.get_readings()['GPU']
    assert detector.call_count == 1
    assert first == second
    assert first.value == 42
    assert first.source == 'nvidia-smi'
