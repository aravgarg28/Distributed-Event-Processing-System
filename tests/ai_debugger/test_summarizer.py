"""Tests for LogSummarizer — LangChain chain that extracts root causes from error logs."""
from unittest.mock import MagicMock, patch
import pytest

from log_monitor import ErrorBurst
from summarizer import LogSummarizer


class TestLogSummarizerInit:
    def test_stores_model_name(self):
        s = LogSummarizer(model="llama-3.3-70b-versatile", api_key="k")
        assert s.model == "llama-3.3-70b-versatile"

    def test_default_model(self):
        s = LogSummarizer(api_key="k")
        assert s.model == "llama-3.3-70b-versatile"


class TestLogSummarizerSummarize:
    def _make_burst(self, lines):
        return ErrorBurst(container="ingress", lines=lines, detected_at=0.0)

    def test_returns_string_summary(self):
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "Root cause: Kafka broker unreachable."

        s = LogSummarizer(api_key="test-key")
        s._chain = mock_chain

        burst = self._make_burst(["ERROR: Kafka connection refused", "FATAL: shutdown"])
        result = s.summarize(burst)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_passes_log_text_to_chain(self):
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "Root cause: OOM."

        s = LogSummarizer(api_key="test-key")
        s._chain = mock_chain

        burst = self._make_burst(["ERROR: out of memory", "FATAL: killed"])
        s.summarize(burst)

        call_kwargs = mock_chain.invoke.call_args
        invoked_input = call_kwargs[0][0] if call_kwargs[0] else call_kwargs[1]
        log_text = invoked_input.get("logs") or invoked_input.get("log_text") or list(invoked_input.values())[0]
        assert "ERROR: out of memory" in log_text

    def test_passes_container_name_to_chain(self):
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "Root cause: network partition."

        s = LogSummarizer(api_key="test-key")
        s._chain = mock_chain

        burst = ErrorBurst(container="processor-2", lines=["ERROR: x"], detected_at=0.0)
        s.summarize(burst)

        call_input = mock_chain.invoke.call_args[0][0]
        combined = " ".join(str(v) for v in call_input.values())
        assert "processor-2" in combined

    def test_chain_invoked_once_per_summarize_call(self):
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "summary"

        s = LogSummarizer(api_key="test-key")
        s._chain = mock_chain

        burst = self._make_burst(["ERROR: something"])
        s.summarize(burst)
        assert mock_chain.invoke.call_count == 1

    def test_truncates_oversized_log_bursts(self):
        from summarizer import MAX_LOG_LINES, MAX_LOG_CHARS
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = "summary"

        s = LogSummarizer(api_key="test-key")
        s._chain = mock_chain

        burst = self._make_burst([f"ERROR: line {i} " + "x" * 200 for i in range(500)])
        s.summarize(burst)

        sent_logs = mock_chain.invoke.call_args[0][0]["logs"]
        assert len(sent_logs) <= MAX_LOG_CHARS
        assert len(sent_logs.splitlines()) <= MAX_LOG_LINES

    def test_build_chain_creates_chain_attribute(self):
        with patch("summarizer.ChatGroq") as mock_llm_cls:
            mock_llm = MagicMock()
            mock_llm_cls.return_value = mock_llm
            mock_llm.__or__ = MagicMock(return_value=MagicMock())

            s = LogSummarizer(api_key="fake-key")
            s.build_chain()
            assert s._chain is not None
