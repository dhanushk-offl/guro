import json
from unittest.mock import Mock, patch
from contextlib import contextmanager

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


@pytest.mark.parametrize('command,constructor,method,options', [
    ('monitor', 'SystemMonitor', 'run_performance_test', []),
    ('heatmap', 'SystemHeatmap', 'run', ['--estimates']),
    ('benchmark', 'SafeSystemBenchmark', 'mini_test', ['--type', 'mini']),
])
def test_initialization_spinner_exits_before_live_view(command, constructor, method, options):
    state = {'active': False, 'entries': 0}

    @contextmanager
    def status(*args, **kwargs):
        assert not state['active']
        state['active'] = True
        state['entries'] += 1
        try:
            yield
        finally:
            state['active'] = False

    instance = Mock()

    def run(**kwargs):
        assert not state['active'], 'Initialization spinner overlaps live rendering'
        return {'status': 'completed'} if command == 'benchmark' else 1

    getattr(instance, method).side_effect = run
    with patch('guro.cli.main.console.status', side_effect=status), patch('guro.cli.main.' + constructor, return_value=instance) as factory:
        result = CliRunner().invoke(cli, [command] + options)
    assert result.exit_code == 0, result.output
    assert state['entries'] == 1
    factory.assert_called_once()
    if command == 'heatmap':
        factory.assert_called_once_with(estimates=True)
    getattr(instance, method).assert_called_once()


@pytest.mark.parametrize('command,constructor', [
    ('monitor', 'SystemMonitor'), ('heatmap', 'SystemHeatmap'),
    ('benchmark', 'SafeSystemBenchmark'),
])
def test_structured_commands_never_start_initialization_spinners(command, constructor):
    instance = Mock()
    instance.collect_sample.return_value = {'cpu_usage': 1}
    instance.get_readings.return_value = {}
    instance.mini_test.return_value = {'status': 'completed'}
    with patch('guro.cli.main.' + constructor, return_value=instance), patch('guro.cli.main.console.status') as status, patch('guro.cli.main.Schedule.wait', side_effect=KeyboardInterrupt):
        result = CliRunner().invoke(cli, [command, '--format', 'json'])
    assert result.exit_code == 0, result.output
    json.loads(result.stdout)
    status.assert_not_called()
