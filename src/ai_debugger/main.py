"""AI Debugger service — polls Docker logs, summarizes errors, annotates Grafana."""
import os
import signal
import time

import docker

from grafana_annotator import GrafanaAnnotator
from log_monitor import LogMonitor
from summarizer import LogSummarizer

CONTAINERS = os.environ.get("WATCH_CONTAINERS", "ingress,processor-1,processor-2").split(",")
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL_SECONDS", "30"))
ERROR_THRESHOLD = int(os.environ.get("ERROR_THRESHOLD", "5"))
WINDOW_SECONDS = int(os.environ.get("WINDOW_SECONDS", "60"))
GRAFANA_URL = os.environ.get("GRAFANA_URL", "http://grafana:3000")
GRAFANA_TOKEN = os.environ.get("GRAFANA_API_TOKEN", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL = os.environ.get("LLM_MODEL", "claude-haiku-4-5-20251001")

_running = True


def _handle_signal(sig, frame):
    global _running
    print(f"Received signal {sig}, shutting down.")
    _running = False


def main():
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    docker_client = docker.from_env()
    monitor = LogMonitor(
        containers=CONTAINERS,
        error_threshold=ERROR_THRESHOLD,
        window_seconds=WINDOW_SECONDS,
    )
    summarizer = LogSummarizer(api_key=ANTHROPIC_API_KEY, model=MODEL)
    annotator = GrafanaAnnotator(grafana_url=GRAFANA_URL, api_token=GRAFANA_TOKEN)

    print(f"AI Debugger watching: {CONTAINERS} — polling every {POLL_INTERVAL}s")

    while _running:
        for burst in monitor.scan(docker_client):
            print(f"[{burst.container}] Error burst detected ({len(burst.lines)} lines)")
            summary = summarizer.summarize(burst)
            print(f"[{burst.container}] Summary: {summary}")
            try:
                ann_id = annotator.annotate_burst(burst=burst, summary=summary)
                print(f"[{burst.container}] Grafana annotation created: id={ann_id}")
            except RuntimeError as e:
                print(f"[{burst.container}] Grafana annotation failed: {e}")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
