import logging
import os
import signal
import sys

from metrics import start_metrics_server
from worker import ProcessorWorker

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    node_id       = os.environ.get("NODE_ID",          "worker-1")
    brokers       = os.environ.get("KAFKA_BROKERS",    "localhost:9092")
    event_topic   = os.environ.get("KAFKA_TOPIC",      "events")
    state_topic   = os.environ.get("STATE_TOPIC",      "state-updates")
    hb_topic      = os.environ.get("HEARTBEAT_TOPIC",  "heartbeats")
    all_nodes_env = os.environ.get("ALL_NODES",        "worker-1,worker-2")

    all_nodes = [n.strip() for n in all_nodes_env.split(",") if n.strip()]

    metrics_port = int(os.environ.get("METRICS_PORT", "8081"))
    start_metrics_server(metrics_port)
    logger.info(
        "starting | node=%s brokers=%s nodes=%s metrics_port=%d",
        node_id, brokers, all_nodes, metrics_port,
    )

    worker = ProcessorWorker(
        node_id=node_id,
        brokers=brokers,
        event_topic=event_topic,
        state_topic=state_topic,
        heartbeat_topic=hb_topic,
        all_nodes=all_nodes,
    )

    def _shutdown(signum, frame):  # noqa: ANN001
        logger.info("signal %d received — shutting down", signum)
        worker.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    worker.run()


if __name__ == "__main__":
    main()
