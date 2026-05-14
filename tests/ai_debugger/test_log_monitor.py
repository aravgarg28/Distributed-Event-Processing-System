"""Tests for LogMonitor — Docker log tailing and error burst detection."""
import time
from unittest.mock import MagicMock, patch, call
import pytest

from log_monitor import LogMonitor, ErrorBurst


class TestErrorBurstDataclass:
    def test_fields_are_accessible(self):
        burst = ErrorBurst(
            container="ingress",
            lines=["ERROR: failed", "FATAL: crash"],
            detected_at=1234567890.0,
        )
        assert burst.container == "ingress"
        assert burst.lines == ["ERROR: failed", "FATAL: crash"]
        assert burst.detected_at == 1234567890.0

    def test_summary_joins_lines(self):
        burst = ErrorBurst(container="proc", lines=["E1", "E2"], detected_at=0.0)
        assert burst.summary == "E1\nE2"


class TestLogMonitorInit:
    def test_stores_container_names(self):
        monitor = LogMonitor(containers=["ingress", "processor-1"], error_threshold=3)
        assert monitor.containers == ["ingress", "processor-1"]

    def test_default_threshold(self):
        monitor = LogMonitor(containers=["c1"])
        assert monitor.error_threshold == 5

    def test_custom_window_seconds(self):
        monitor = LogMonitor(containers=["c1"], window_seconds=30)
        assert monitor.window_seconds == 30


class TestLogMonitorIsErrorLine:
    def setup_method(self):
        self.monitor = LogMonitor(containers=[])

    def test_detects_error_keyword(self):
        assert self.monitor.is_error_line("ERROR: connection refused") is True

    def test_detects_fatal_keyword(self):
        assert self.monitor.is_error_line("FATAL: segfault at 0x0") is True

    def test_detects_exception_keyword(self):
        assert self.monitor.is_error_line("Exception in thread main") is True

    def test_detects_traceback_keyword(self):
        assert self.monitor.is_error_line("Traceback (most recent call last):") is True

    def test_case_insensitive(self):
        assert self.monitor.is_error_line("error: something bad") is True

    def test_normal_line_is_not_error(self):
        assert self.monitor.is_error_line("INFO: processing event abc") is False

    def test_empty_line_is_not_error(self):
        assert self.monitor.is_error_line("") is False


class TestLogMonitorCollectBurst:
    def setup_method(self):
        self.monitor = LogMonitor(containers=[], error_threshold=3, window_seconds=60)

    def test_returns_none_below_threshold(self):
        lines = ["ERROR: one", "ERROR: two"]
        assert self.monitor.collect_burst("c1", lines) is None

    def test_returns_burst_at_threshold(self):
        lines = ["ERROR: a", "FATAL: b", "Exception: c"]
        burst = self.monitor.collect_burst("c1", lines)
        assert burst is not None
        assert burst.container == "c1"
        assert len(burst.lines) == 3

    def test_burst_contains_only_error_lines(self):
        lines = ["INFO: ok", "ERROR: bad", "DEBUG: fine", "FATAL: crash", "ERROR: also bad"]
        burst = self.monitor.collect_burst("c1", lines)
        assert burst is not None
        for line in burst.lines:
            assert self.monitor.is_error_line(line)

    def test_returns_none_when_no_error_lines(self):
        lines = ["INFO: ok", "DEBUG: fine", "INFO: done"]
        assert self.monitor.collect_burst("c1", lines) is None


class TestLogMonitorTailContainer:
    def test_tails_logs_from_docker_client(self):
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_client.containers.get.return_value = mock_container
        mock_container.logs.return_value = iter([
            b"INFO: started\n",
            b"ERROR: connection refused\n",
            b"FATAL: shutting down\n",
            b"ERROR: timeout\n",
        ])

        monitor = LogMonitor(containers=["ingress"], error_threshold=3)
        lines = list(monitor.tail_container(mock_client, "ingress", tail=100))

        mock_client.containers.get.assert_called_once_with("ingress")
        mock_container.logs.assert_called_once()
        assert len(lines) == 4

    def test_returns_empty_on_missing_container(self):
        import docker
        mock_client = MagicMock()
        mock_client.containers.get.side_effect = docker.errors.NotFound("ingress")

        monitor = LogMonitor(containers=["ingress"])
        lines = list(monitor.tail_container(mock_client, "ingress", tail=50))
        assert lines == []


class TestLogMonitorScan:
    def test_scan_yields_bursts_for_containers_with_enough_errors(self):
        mock_client = MagicMock()

        error_lines = [
            b"ERROR: a\n", b"FATAL: b\n", b"Exception: c\n",
            b"ERROR: d\n", b"FATAL: e\n",
        ]
        ok_lines = [b"INFO: all good\n", b"DEBUG: ok\n"]

        def fake_get(name):
            c = MagicMock()
            if name == "ingress":
                c.logs.return_value = iter(error_lines)
            else:
                c.logs.return_value = iter(ok_lines)
            return c

        mock_client.containers.get.side_effect = fake_get

        monitor = LogMonitor(containers=["ingress", "processor-1"], error_threshold=3)
        bursts = list(monitor.scan(mock_client))

        assert len(bursts) == 1
        assert bursts[0].container == "ingress"

    def test_scan_yields_nothing_when_no_errors(self):
        mock_client = MagicMock()
        mock_container = MagicMock()
        mock_client.containers.get.return_value = mock_container
        mock_container.logs.return_value = iter([b"INFO: ok\n"])

        monitor = LogMonitor(containers=["c1"], error_threshold=3)
        bursts = list(monitor.scan(mock_client))
        assert bursts == []
