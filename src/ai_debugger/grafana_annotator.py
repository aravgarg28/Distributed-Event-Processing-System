"""Pushes human-readable root-cause summaries to Grafana as annotations."""
import time
from typing import List

import requests

from log_monitor import ErrorBurst


class GrafanaAnnotator:
    REQUEST_TIMEOUT_S = 10

    def __init__(self, grafana_url: str, api_token: str, tags: List[str] = None):
        self.grafana_url = grafana_url.rstrip("/")
        self.api_token = api_token
        self.tags = tags if tags is not None else ["ai-debugger"]

    def annotate(self, text: str, tags: List[str]) -> int:
        url = f"{self.grafana_url}/api/annotations"
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "text": text,
            "tags": list(set(self.tags + tags)),
            "time": int(time.time() * 1000),
        }
        try:
            resp = requests.post(
                url, headers=headers, json=payload, timeout=self.REQUEST_TIMEOUT_S
            )
        except requests.RequestException as e:
            raise RuntimeError(f"Grafana annotation request failed: {e}") from e
        if resp.status_code != 200:
            raise RuntimeError(
                f"Grafana annotation failed: {resp.status_code} — {resp.text}"
            )
        return resp.json()["id"]

    def annotate_burst(self, burst: ErrorBurst, summary: str) -> int:
        text = f"[{burst.container}] {summary}"
        return self.annotate(text=text, tags=[burst.container])
