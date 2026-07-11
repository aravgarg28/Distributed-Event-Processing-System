"""Tests for GrafanaAnnotator — pushes text annotations to Grafana via REST API."""
from unittest.mock import MagicMock, patch
import pytest

from grafana_annotator import GrafanaAnnotator


class TestGrafanaAnnotatorInit:
    def test_stores_url_and_token(self):
        ann = GrafanaAnnotator(grafana_url="http://grafana:3000", api_token="secret")
        assert ann.grafana_url == "http://grafana:3000"
        assert ann.api_token == "secret"

    def test_trailing_slash_stripped(self):
        ann = GrafanaAnnotator(grafana_url="http://grafana:3000/", api_token="t")
        assert not ann.grafana_url.endswith("/")

    def test_default_tag(self):
        ann = GrafanaAnnotator(grafana_url="http://g:3000", api_token="t")
        assert "ai-debugger" in ann.tags


class TestGrafanaAnnotatorAnnotate:
    def _make_annotator(self):
        return GrafanaAnnotator(grafana_url="http://grafana:3000", api_token="tok")

    def test_posts_to_annotations_endpoint(self):
        ann = self._make_annotator()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": 1}

        with patch("grafana_annotator.requests.post", return_value=mock_resp) as mock_post:
            ann.annotate(text="Root cause: Kafka down.", tags=["ingress"])
            mock_post.assert_called_once()
            url = mock_post.call_args[0][0]
            assert "/api/annotations" in url

    def test_sends_bearer_token_in_header(self):
        ann = self._make_annotator()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": 1}

        with patch("grafana_annotator.requests.post", return_value=mock_resp) as mock_post:
            ann.annotate(text="summary", tags=[])
            headers = mock_post.call_args[1]["headers"]
            assert headers.get("Authorization") == "Bearer tok"

    def test_sends_text_in_json_body(self):
        ann = self._make_annotator()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": 1}

        with patch("grafana_annotator.requests.post", return_value=mock_resp) as mock_post:
            ann.annotate(text="Root cause: OOM killer.", tags=["processor-1"])
            payload = mock_post.call_args[1]["json"]
            assert payload["text"] == "Root cause: OOM killer."

    def test_merges_default_tags_with_passed_tags(self):
        ann = self._make_annotator()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": 1}

        with patch("grafana_annotator.requests.post", return_value=mock_resp) as mock_post:
            ann.annotate(text="summary", tags=["processor-2"])
            payload = mock_post.call_args[1]["json"]
            assert "ai-debugger" in payload["tags"]
            assert "processor-2" in payload["tags"]

    def test_returns_annotation_id_on_success(self):
        ann = self._make_annotator()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": 42}

        with patch("grafana_annotator.requests.post", return_value=mock_resp):
            result = ann.annotate(text="summary", tags=[])
            assert result == 42

    def test_sends_request_with_timeout(self):
        ann = self._make_annotator()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": 1}

        with patch("grafana_annotator.requests.post", return_value=mock_resp) as mock_post:
            ann.annotate(text="summary", tags=[])
            assert mock_post.call_args[1]["timeout"] == GrafanaAnnotator.REQUEST_TIMEOUT_S

    def test_raises_runtime_error_on_connection_failure(self):
        import requests as requests_lib
        ann = self._make_annotator()

        with patch(
            "grafana_annotator.requests.post",
            side_effect=requests_lib.ConnectionError("refused"),
        ):
            with pytest.raises(RuntimeError, match="request failed"):
                ann.annotate(text="summary", tags=[])

    def test_raises_on_non_200_response(self):
        ann = self._make_annotator()
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.text = "Unauthorized"

        with patch("grafana_annotator.requests.post", return_value=mock_resp):
            with pytest.raises(RuntimeError, match="401"):
                ann.annotate(text="summary", tags=[])

    def test_annotate_from_burst_uses_container_as_tag(self):
        from log_monitor import ErrorBurst
        ann = self._make_annotator()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": 7}

        burst = ErrorBurst(container="processor-1", lines=["ERROR: x"], detected_at=0.0)

        with patch("grafana_annotator.requests.post", return_value=mock_resp) as mock_post:
            ann.annotate_burst(burst=burst, summary="Root cause: partition lag.")
            payload = mock_post.call_args[1]["json"]
            assert "processor-1" in payload["tags"]
            assert "Root cause: partition lag." in payload["text"]
