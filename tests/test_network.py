import pytest
import time
from guro.core.network import NetworkMonitor
from click.testing import CliRunner
from guro.cli.main import cli


@pytest.fixture
def network_monitor():
    return NetworkMonitor()


def test_get_network_stats(network_monitor):
    stats = network_monitor.get_network_stats()
    assert isinstance(stats, dict), "Stats should be a dictionary"
    assert "bytes_sent" in stats, "Missing 'bytes_sent' key"
    assert "bytes_recv" in stats, "Missing 'bytes_recv' key"
    assert "packets_sent" in stats, "Missing 'packets_sent' key"
    assert "packets_recv" in stats, "Missing 'packets_recv' key"


def test_run_network_monitor(network_monitor):
    try:
        network_monitor.run(interval=0.1, duration=2)
    except Exception as e:
        pytest.fail(f"Network monitoring failed: {e}")

    stats = network_monitor.get_network_stats()  
    assert isinstance(stats, dict), "Stats should be a dictionary after monitoring"
    assert "bytes_sent" in stats, "Missing 'bytes_sent' key after monitoring"
    assert "bytes_recv" in stats, "Missing 'bytes_recv' key after monitoring"


def test_network_monitor_duration(network_monitor):
    start_time = time.time()

    network_monitor.run(interval=0.5, duration=1)

    end_time = time.time()
    elapsed_time = end_time - start_time
    assert 0.9 <= elapsed_time <= 1.1, f"Elapsed time was {elapsed_time:.2f}s, expected ~1s"


def test_net_monitor_command():
    runner = CliRunner()
    result = runner.invoke(cli, ['net-monitor', '--interval', '0.1', '--duration', '1'])

    assert result.exit_code == 0, f"Command failed with exit code {result.exit_code}"
    assert "Monitoring network with interval" in result.output, "Expected output not found"
