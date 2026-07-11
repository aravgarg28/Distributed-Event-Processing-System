"""Tails Docker container logs and detects error bursts."""
import hashlib
import time
from dataclasses import dataclass
from typing import Dict, Iterator, List, Optional

import docker
import docker.errors

_ERROR_KEYWORDS = ("error", "fatal", "exception", "traceback", "panic", "critical")


@dataclass
class ErrorBurst:
    container: str
    lines: List[str]
    detected_at: float

    @property
    def summary(self) -> str:
        return "\n".join(self.lines)

    @property
    def fingerprint(self) -> str:
        digest = hashlib.sha256()
        digest.update(self.container.encode())
        for line in self.lines:
            digest.update(line.encode())
        return digest.hexdigest()


class LogMonitor:
    def __init__(
        self,
        containers: List[str],
        error_threshold: int = 5,
        window_seconds: int = 60,
    ):
        self.containers = containers
        self.error_threshold = error_threshold
        self.window_seconds = window_seconds
        # Last-reported burst fingerprint per container; the log tail keeps old
        # error lines around, so without this every poll would re-report (and
        # re-summarize via the LLM) the same burst indefinitely.
        self._last_fingerprint: Dict[str, str] = {}

    def is_error_line(self, line: str) -> bool:
        lower = line.lower()
        return any(kw in lower for kw in _ERROR_KEYWORDS)

    def collect_burst(self, container: str, lines: List[str]) -> Optional[ErrorBurst]:
        error_lines = [l for l in lines if self.is_error_line(l)]
        if len(error_lines) >= self.error_threshold:
            return ErrorBurst(
                container=container,
                lines=error_lines,
                detected_at=time.time(),
            )
        return None

    def is_new_burst(self, burst: ErrorBurst) -> bool:
        """True if this burst differs from the last one seen for its container."""
        if self._last_fingerprint.get(burst.container) == burst.fingerprint:
            return False
        self._last_fingerprint[burst.container] = burst.fingerprint
        return True

    def tail_container(
        self, client: docker.DockerClient, container_name: str, tail: int = 200
    ) -> List[str]:
        try:
            container = client.containers.get(container_name)
            # stream=False (the default) returns the whole tail as one bytes blob.
            raw = container.logs(tail=tail, timestamps=False)
            if isinstance(raw, (bytes, bytearray)):
                text = raw.decode("utf-8", errors="replace")
            else:
                # Generator of byte chunks (stream=True style) — join first.
                text = b"".join(raw).decode("utf-8", errors="replace")
            return text.splitlines()
        except docker.errors.NotFound:
            return []
        except docker.errors.APIError as e:
            print(f"[LogMonitor] Docker API error for '{container_name}': {e}")
            return []

    def scan(self, client: docker.DockerClient) -> Iterator[ErrorBurst]:
        for name in self.containers:
            lines = self.tail_container(client, name)
            burst = self.collect_burst(name, lines)
            if burst and self.is_new_burst(burst):
                yield burst
