import json
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from guro.cli.main import cli


@pytest.mark.parametrize('args', [
    ['monitor', '--interval', '0'], ['monitor', '--duration', '-1'],
    ['benchmark', '--cpu-only', '--gpu-only'],
    ['network', '--speed', '--interfaces'],
])
def test_invalid_arguments_fail(args):
    assert CliRunner().invoke(cli, args).exit_code != 0


def test_initialization_failure_returns_nonzero():
    with patch('guro.cli.main.SystemMonitor', side_effect=RuntimeError('probe failed')):
        result = CliRunner().invoke(cli, ['monitor'])
    assert result.exit_code == 1
    assert 'probe failed' in result.output


@pytest.mark.parametrize('fmt', ['json', 'jsonl'])
def test_monitor_output_is_machine_readable_without_banner(fmt):
    runner = CliRunner()
    # Interrupt after one row instead of waiting for the real duration.
    with patch('guro.cli.main.Schedule.wait', side_effect=KeyboardInterrupt):
        result = runner.invoke(cli, ['monitor', '--format', fmt])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    row = data[0] if fmt == 'json' else data
    assert 'cpu_usage' in row and 'timestamp' in row


def test_heatmap_json_output_has_source_and_nulls():
    with patch('guro.core.heatmap.SystemHeatmap.get_linux_temps', return_value={c: None for c in ('CPU', 'GPU', 'RAM', 'Storage', 'Motherboard')}), patch('guro.cli.main.Schedule.wait', side_effect=KeyboardInterrupt):
        result = CliRunner().invoke(cli, ['heatmap', '--format', 'json'])
    assert result.exit_code == 0, result.output
    assert 'source' in json.loads(result.output)[0]['temperatures']['CPU']


def test_doctor_writes_file(tmp_path):
    path = tmp_path / 'doctor.json'
    with patch('guro.cli.main.capabilities', return_value={'gpu_workload': 'unsupported'}):
        result = CliRunner().invoke(cli, ['doctor', '--format', 'json', '--output', str(path)])
    assert result.exit_code == 0, result.output
    assert result.output == ''
    assert json.loads(path.read_text()) == {'gpu_workload': 'unsupported'}


def test_network_denied_is_not_empty_success():
    import psutil
    with patch('psutil.net_connections', side_effect=psutil.AccessDenied):
        result = CliRunner().invoke(cli, ['network', '--connections', '--format', 'json'])
    assert result.exit_code == 0
    assert json.loads(result.output)['status'] == 'permission denied'


def test_unsupported_gpu_workload_is_structured_and_nonzero():
    with patch('guro.core.benchmark.GPUDetector.get_all_gpus', return_value={'available': False, 'gpus': []}):
        result = CliRunner().invoke(cli, ['benchmark', '--gpu-only', '--format', 'json'])
    assert result.exit_code == 1
    assert json.loads(result.stdout)['status'] == 'unsupported'
