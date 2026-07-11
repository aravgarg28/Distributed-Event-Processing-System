"""AI Debugger service — polls Docker logs, summarizes errors, annotates Grafana."""
import os
import signal
import threading

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
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
MODEL = os.environ.get("LLM_MODEL", "llama-3.3-70b-versatile")

_shutdown = threading.Event()


def _handle_signal(sig, frame):
    print(f"Received signal {sig}, shutting down.")
    _shutdown.set()


def _handle_burst(burst, summarizer, annotator):
    """Summarize and annotate one burst; failures are logged, never fatal."""
    print(f"[{burst.container}] Error burst detected ({len(burst.lines)} lines)")
    try:
        summary = summarizer.summarize(burst)
    except Exception as e:
        print(f"[{burst.container}] LLM summarization failed: {e}")
        return
    print(f"[{burst.container}] Summary: {summary}")
    try:
        ann_id = annotator.annotate_burst(burst=burst, summary=summary)
        print(f"[{burst.container}] Grafana annotation created: id={ann_id}")
    except RuntimeError as e:
        print(f"[{burst.container}] Grafana annotation failed: {e}")


def main():
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    if not GROQ_API_KEY:
        print("WARNING: GROQ_API_KEY is empty — summarization calls will fail.")
    if not GRAFANA_TOKEN:
        print("WARNING: GRAFANA_API_TOKEN is empty — annotations will be rejected.")

    docker_client = docker.from_env()
    monitor = LogMonitor(
        containers=CONTAINERS,
        error_threshold=ERROR_THRESHOLD,
        window_seconds=WINDOW_SECONDS,
    )
    summarizer = LogSummarizer(api_key=GROQ_API_KEY, model=MODEL)
    annotator = GrafanaAnnotator(grafana_url=GRAFANA_URL, api_token=GRAFANA_TOKEN)

    print(f"AI Debugger watching: {CONTAINERS} — polling every {POLL_INTERVAL}s")

    while not _shutdown.is_set():
        try:
            for burst in monitor.scan(docker_client):
                _handle_burst(burst, summarizer, annotator)
        except Exception as e:
            print(f"Scan cycle failed: {e}")
        _shutdown.wait(POLL_INTERVAL)


if __name__ == "__main__":
    main()
