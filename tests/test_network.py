import pytest
from unittest.mock import patch, MagicMock, mock_open
import time
import socket

import psutil

from guro.core.network import (
    NetworkMonitor, _format_bytes, _format_speed, _sparkline, _get_proc_net_snmp,
)


class FakeAddr:
    def __init__(self, family, address, netmask=None, broadcast=None):
        self.family = family
        self.address = address
        self.netmask = netmask
        self.broadcast = broadcast


class FakeStat:
    def __init__(self, isup=True, duplex=1, speed=1000, mtu=1500):
        self.isup = isup
        self.duplex = duplex
        self.speed = speed
        self.mtu = mtu


class FakeIO:
    def __init__(self, bytes_sent=0, bytes_recv=0, packets_sent=0,
                 packets_recv=0, errin=0, errout=0, dropin=0, dropout=0):
        self.bytes_sent = bytes_sent
        self.bytes_recv = bytes_recv
        self.packets_sent = packets_sent
        self.packets_recv = packets_recv
        self.errin = errin
        self.errout = errout
        self.dropin = dropin
        self.dropout = dropout


class FakeConn:
    def __init__(self, status='ESTABLISHED', pid=1234, laddr=None, raddr=None):
        self.status = status
        self.pid = pid
        self.laddr = laddr
        self.raddr = raddr


class FakeConnAddr:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port


class TestFormatBytes:
    @pytest.mark.parametrize("value,expected", [
        (0, "0.0 B"),
        (500, "500.0 B"),
        (1024, "1.0 KB"),
        (1536, "1.5 KB"),
        (1048576, "1.0 MB"),
        (1073741824, "1.0 GB"),
        (1099511627776, "1.0 TB"),
    ])
    def test_format_bytes(self, value, expected):
        assert _format_bytes(value) == expected

    @pytest.mark.parametrize("value,expected", [
        (0, "0.0 B/s"),
        (1024, "1.0 KB/s"),
        (1048576, "1.0 MB/s"),
    ])
    def test_format_speed(self, value, expected):
        assert _format_speed(value) == expected


class TestSparkline:
    def test_empty(self):
        assert _sparkline([], width=5) == '     '

    def test_single_value(self):
        result = _sparkline([100], width=5)
        assert len(result) == 5
        assert result.endswith('█')

    def test_all_values(self):
        result = _sparkline([0, 50, 100], width=10)
        assert len(result) == 10

    def test_zero_max(self):
        result = _sparkline([0, 0, 0], width=3)
        assert result == '   '

    def test_width_limit(self):
        result = _sparkline(list(range(100)), width=10)
        assert len(result) == 10


class TestGetProcNetSnmp:
    @patch('guro.core.network._SYSTEM', 'Linux')
    def test_parse_snmp(self):
        fake_content = (
            "Tcp: RtoAlgorithm RtoMin RtoMax MaxConn ActiveOpens "
            "PassiveOpens AttemptFails EstabResets InSegs OutSegs "
            "RetransSegs InErrs OutRsts InCsumErrors\n"
            "Tcp: 1 200 120000 -1 100 50 2 3 45000 52000 15 0 10 0\n"
            "Udp: InDatagrams OutDatagrams NoPorts InErrors OutErrors\n"
            "Udp: 10000 8000 5 2 0\n"
        )
        with patch('builtins.open', mock_open(read_data=fake_content)):
            result = _get_proc_net_snmp()
        assert result['tcp']['ActiveOpens'] == 100
        assert result['tcp']['OutSegs'] == 52000
        assert result['tcp']['RetransSegs'] == 15
        assert result['udp']['InDatagrams'] == 10000
        assert result['udp']['InErrors'] == 2

    @patch('guro.core.network._SYSTEM', 'Linux')
    def test_missing_file(self):
        with patch('builtins.open', side_effect=FileNotFoundError):
            result = _get_proc_net_snmp()
        assert result == {'tcp': {}, 'udp': {}}

    @patch('guro.core.network._SYSTEM', 'Windows')
    def test_non_linux(self):
        result = _get_proc_net_snmp()
        assert result == {'tcp': {}, 'udp': {}}


class TestNetworkMonitor:
    @pytest.fixture
    def monitor(self):
        m = NetworkMonitor()
        m._prev_io = {}
        m._prev_time = time.time()
        return m

    @patch('psutil.net_if_stats')
    @patch('psutil.net_if_addrs')
    def test_get_interfaces(self, mock_addrs, mock_stats):
        mock_stats.return_value = {
            'eth0': FakeStat(isup=True, speed=1000),
            'lo': FakeStat(isup=True, speed=0),
        }
        mock_addrs.return_value = {
            'eth0': [
                FakeAddr(family=psutil.AF_LINK, address='aa:bb:cc:dd:ee:ff'),
                FakeAddr(family=socket.AF_INET, address='192.168.1.5',
                         netmask='255.255.255.0'),
                FakeAddr(family=socket.AF_INET6, address='fe80::1'),
            ],
            'lo': [
                FakeAddr(family=socket.AF_INET, address='127.0.0.1'),
            ],
        }
        m = NetworkMonitor()
        interfaces = m.get_interfaces()
        assert len(interfaces) == 2
        eth0 = [i for i in interfaces if i['name'] == 'eth0'][0]
        assert eth0['isup'] is True
        assert eth0['mac'] == 'aa:bb:cc:dd:ee:ff'
        assert '192.168.1.5' in eth0['ipv4']
        assert 'fe80::1' in eth0['ipv6']
        assert eth0['speed'] == 1000

    @patch('psutil.net_if_stats')
    @patch('psutil.net_if_addrs')
    def test_get_active_interfaces(self, mock_addrs, mock_stats):
        mock_stats.return_value = {
            'eth0': FakeStat(isup=True, speed=1000),
            'eth1': FakeStat(isup=False, speed=0),
        }
        mock_addrs.return_value = {}
        m = NetworkMonitor()
        active = m.get_active_interfaces()
        assert 'eth0' in active
        assert 'eth1' not in active

    @patch('psutil.net_io_counters')
    def test_get_speeds(self, mock_counters):
        mock_counters.return_value = {
            'eth0': FakeIO(bytes_sent=1000, bytes_recv=2000),
        }
        m = NetworkMonitor()
        m._prev_io = {'eth0': FakeIO(bytes_sent=0, bytes_recv=0)}
        m._prev_time = time.time() - 1.0
        m._ensure_history(['eth0'])
        speeds = m.get_speeds()
        assert 'eth0' in speeds
        up, down = speeds['eth0']
        assert up == pytest.approx(1000.0, rel=1)
        assert down == pytest.approx(2000.0, rel=1)

    @patch('psutil.net_io_counters')
    def test_get_speeds_zero_elapsed(self, mock_counters):
        mock_counters.return_value = {
            'eth0': FakeIO(bytes_sent=500, bytes_recv=1000),
        }
        m = NetworkMonitor()
        m._prev_io = {'eth0': FakeIO(bytes_sent=0, bytes_recv=0)}
        m._prev_time = time.time()
        m._ensure_history(['eth0'])
        speeds = m.get_speeds()
        assert 'eth0' in speeds

    @patch('psutil.net_io_counters')
    def test_get_speeds_first_call(self, mock_counters):
        mock_counters.return_value = {
            'eth0': FakeIO(bytes_sent=100, bytes_recv=200),
        }
        m = NetworkMonitor()
        m._prev_io = {}
        speeds = m.get_speeds()
        assert speeds['eth0'] == (0.0, 0.0)

    @patch('psutil.net_connections')
    def test_get_tcp_states(self, mock_connections):
        mock_connections.return_value = [
            FakeConn(status='ESTABLISHED', pid=1),
            FakeConn(status='ESTABLISHED', pid=2),
            FakeConn(status='LISTEN', pid=3),
            FakeConn(status='TIME_WAIT', pid=4),
        ]
        m = NetworkMonitor()
        states = m.get_tcp_states()
        assert states.get('ESTABLISHED') == 2
        assert states.get('LISTEN') == 1
        assert states.get('TIME_WAIT') == 1

    @patch('psutil.net_connections')
    def test_get_tcp_states_access_denied(self, mock_connections):
        mock_connections.side_effect = psutil.AccessDenied()
        m = NetworkMonitor()
        assert m.get_tcp_states() == {}

    @patch('psutil.net_connections')
    def test_get_connections(self, mock_connections):
        mock_connections.return_value = [
            FakeConn(
                status='ESTABLISHED', pid=42,
                laddr=FakeConnAddr('10.0.0.1', 54321),
                raddr=FakeConnAddr('93.184.216.34', 443),
            ),
            FakeConn(
                status='LISTEN', pid=1,
                laddr=FakeConnAddr('0.0.0.0', 22),
                raddr=None,
            ),
        ]
        with patch('psutil.Process') as mock_proc:
            mock_proc.return_value.name.return_value = 'sshd'
            m = NetworkMonitor()
            conns = m.get_connections()
            assert len(conns) == 2
            estab = [c for c in conns if c['status'] == 'ESTABLISHED'][0]
            assert estab['pid'] == 42
            assert estab['remote'] == '93.184.216.34:443'

    @patch('psutil.net_connections')
    def test_get_connections_no_remote_listen(self, mock_connections):
        mock_connections.return_value = [
            FakeConn(
                status='LISTEN', pid=1,
                laddr=FakeConnAddr('0.0.0.0', 80),
                raddr=None,
            ),
            FakeConn(status='NONE', pid=None, laddr=None, raddr=None),
        ]
        m = NetworkMonitor()
        conns = m.get_connections()
        assert len(conns) == 1

    @patch('psutil.net_connections')
    def test_get_connections_process_error(self, mock_connections):
        mock_connections.return_value = [
            FakeConn(
                status='ESTABLISHED', pid=9999,
                laddr=FakeConnAddr('10.0.0.1', 1234),
                raddr=FakeConnAddr('8.8.8.8', 53),
            ),
        ]
        with patch('psutil.Process', side_effect=psutil.NoSuchProcess(9999)):
            m = NetworkMonitor()
            conns = m.get_connections()
            assert conns[0]['process'] == '?'

    def test_running_property(self):
        m = NetworkMonitor()
        assert m.running is True
        m.running = False
        assert m.running is False
        m.running = True
        assert m.running is True

    def test_ensure_history(self):
        m = NetworkMonitor()
        m._ensure_history(['eth0', 'wlan0'])
        assert 'eth0_up' in m._speed_history
        assert 'eth0_down' in m._speed_history
        assert 'wlan0_up' in m._speed_history
        assert 'wlan0_down' in m._speed_history
        assert len(m._speed_history['eth0_up']) == 0
        assert m._speed_history['eth0_up'].maxlen == 60

    @patch('psutil.net_if_stats')
    @patch('psutil.net_if_addrs')
    def test_list_interfaces_empty(self, mock_addrs, mock_stats):
        mock_stats.return_value = {}
        mock_addrs.return_value = {}
        m = NetworkMonitor()
        assert m.get_interfaces() == []

    @patch('guro.core.network._get_proc_net_snmp')
    @patch('psutil.net_connections')
    @patch('psutil.net_io_counters')
    @patch('psutil.net_if_stats')
    @patch('psutil.net_if_addrs')
    def test_run_dashboard_duration(
        self, mock_addrs, mock_stats, mock_counters,
        mock_connections, mock_snmp
    ):
        mock_stats.return_value = {'eth0': FakeStat(isup=True, speed=1000)}
        mock_addrs.return_value = {
            'eth0': [FakeAddr(family=2, address='10.0.0.1')],
        }
        mock_counters.return_value = {
            'eth0': FakeIO(bytes_sent=0, bytes_recv=0),
        }
        mock_connections.return_value = []
        mock_snmp.return_value = {'tcp': {}, 'udp': {}}

        m = NetworkMonitor()
        m.running = True
        m._prev_io = {'eth0': FakeIO(bytes_sent=0, bytes_recv=0)}
        m._prev_time = time.time()

        with patch('time.sleep', return_value=None):
            m.run_dashboard(interval=0.01, duration=0.02)
        assert m.running is False

    @patch('guro.core.network._get_proc_net_snmp')
    @patch('psutil.net_connections')
    @patch('psutil.net_io_counters')
    @patch('psutil.net_if_stats')
    @patch('psutil.net_if_addrs')
    def test_run_dashboard_export(
        self, mock_addrs, mock_stats, mock_counters,
        mock_connections, mock_snmp
    ):
        mock_stats.return_value = {'eth0': FakeStat(isup=True, speed=1000)}
        mock_addrs.return_value = {
            'eth0': [FakeAddr(family=2, address='10.0.0.1')],
        }
        mock_counters.return_value = {
            'eth0': FakeIO(bytes_sent=10, bytes_recv=20),
        }
        mock_connections.return_value = []
        mock_snmp.return_value = {'tcp': {}, 'udp': {}}

        m = NetworkMonitor()
        m.running = True
        m._prev_io = {'eth0': FakeIO(bytes_sent=0, bytes_recv=0)}
        m._prev_time = time.time()

        with patch('time.sleep', return_value=None):
            with patch.object(m, 'export_csv') as mock_export:
                m.run_dashboard(interval=0.01, duration=0.02, export=True)
                assert len(m._export_data) > 0
                mock_export.assert_called_once()

    def test_export_csv_no_data(self):
        m = NetworkMonitor()
        m._export_data = []
        with patch.object(m._console, 'print') as mock_print:
            m.export_csv()
            mock_print.assert_called_once()

    @patch('psutil.net_if_stats')
    @patch('psutil.net_if_addrs')
    def test_show_speed(self, mock_addrs, mock_stats):
        mock_stats.return_value = {'eth0': FakeStat(isup=True, speed=1000)}
        mock_addrs.return_value = {
            'eth0': [FakeAddr(family=2, address='10.0.0.1')],
        }
        m = NetworkMonitor()
        m._prev_io = {'eth0': FakeIO(bytes_sent=1000, bytes_recv=2000)}
        m._prev_time = time.time() - 1.0

        with patch('psutil.net_io_counters') as mock_counters:
            mock_counters.return_value = {
                'eth0': FakeIO(bytes_sent=2000, bytes_recv=4000),
            }
            with patch.object(m._console, 'print') as mock_print:
                m.show_speed()
                mock_print.assert_called_once()

    @patch('psutil.net_connections')
    def test_show_connections_no_conns(self, mock_connections):
        mock_connections.side_effect = psutil.AccessDenied()
        m = NetworkMonitor()
        with patch.object(m._console, 'print') as mock_print:
            m.show_connections()
            mock_print.assert_called_once()



