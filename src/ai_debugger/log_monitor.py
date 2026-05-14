"""Tails Docker container logs and detects error bursts."""
import time
from dataclasses import dataclass, field
from typing import Iterator, List, Optional

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

    def tail_container(
        self, client: docker.DockerClient, container_name: str, tail: int = 200
    ) -> List[str]:
        try:
            container = client.containers.get(container_name)
            raw = container.logs(tail=tail, timestamps=False)
            lines = []
            for chunk in raw:
                text = chunk.decode("utf-8", errors="replace").rstrip("\n")
                lines.append(text)
            return lines
        except docker.errors.NotFound:
            return []

    def scan(self, client: docker.DockerClient) -> Iterator[ErrorBurst]:
        for name in self.containers:
            lines = self.tail_container(client, name)
            burst = self.collect_burst(name, lines)
            if burst:
                yield burst
