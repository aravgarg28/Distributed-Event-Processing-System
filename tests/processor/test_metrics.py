"""
Tests for the processor metrics module.

prometheus_client uses a global registry, so counters accumulate across tests.
We capture the value *before* and assert the *delta*, which is test-order
independent.
"""
import pytest

import metrics as m


def _counter_value(counter, node_id: str) -> float:
    try:
        return counter.labels(node_id=node_id)._value.get()
    except Exception:
        return 0.0


NODE = "test-node-metrics"


def test_record_event_processed_increments_by_one():
    before = _counter_value(m.EVENTS_PROCESSED, NODE)
    m.record_event_processed(NODE)
    assert _counter_value(m.EVENTS_PROCESSED, NODE) - before == 1.0


def test_record_event_skipped_increments_by_one():
    before = _counter_value(m.EVENTS_SKIPPED, NODE)
    m.record_event_skipped(NODE)
    assert _counter_value(m.EVENTS_SKIPPED, NODE) - before == 1.0


def test_record_processing_duration_does_not_raise():
    m.record_processing_duration(NODE, 0.005)
    m.record_processing_duration(NODE, 0.1)


def test_record_kafka_error_increments_by_one():
    before = _counter_value(m.KAFKA_CONSUMER_ERRORS, NODE)
    m.record_kafka_error(NODE)
    assert _counter_value(m.KAFKA_CONSUMER_ERRORS, NODE) - before == 1.0


def test_record_failover_increments_by_one():
    before = _counter_value(m.FAILOVERS_TOTAL, NODE)
    m.record_failover(NODE)
    assert _counter_value(m.FAILOVERS_TOTAL, NODE) - before == 1.0


def test_update_store_sizes_sets_gauges():
    m.update_store_sizes(NODE, primary=42, replica=17)
    assert m.PRIMARY_STORE_ENTITIES.labels(node_id=NODE)._value.get() == 42.0
    assert m.REPLICA_STORE_ENTITIES.labels(node_id=NODE)._value.get() == 17.0


def test_multiple_calls_accumulate():
    before = _counter_value(m.EVENTS_PROCESSED, NODE + "-acc")
    for _ in range(5):
        m.record_event_processed(NODE + "-acc")
    assert _counter_value(m.EVENTS_PROCESSED, NODE + "-acc") - before == 5.0
