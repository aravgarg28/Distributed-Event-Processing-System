#include <gtest/gtest.h>
#include <type_traits>

#include "kafka_producer.h"

namespace deps {

// Verify the IS-A relationship at compile time — caught here before link time.
static_assert(std::is_base_of<IKafkaProducer, KafkaProducer>::value,
              "KafkaProducer must implement IKafkaProducer");

// librdkafka is fully async: construction succeeds even when the broker is
// unreachable, because the actual TCP connection attempt happens in a
// background thread.  This test confirms there is no eager connection or
// synchronous throw on valid (but offline) broker addresses.
TEST(KafkaProducerTest, ConstructsWithoutThrowOnOfflineBroker) {
    EXPECT_NO_THROW({
        KafkaProducer producer("localhost:9092", "events");
    });
}

// Produce must return false (not throw) when the broker is unreachable and
// the local queue overflows — the caller decides whether to retry.
TEST(KafkaProducerTest, ProduceReturnsFalseWhenBrokerUnreachable) {
    KafkaProducer producer("localhost:19092", "events");  // port nothing listens on

    // Exhaust the internal queue (default queue.buffering.max.messages = 100000).
    // After enough calls the queue fills and produce returns ERR__QUEUE_FULL.
    bool any_failure = false;
    for (int i = 0; i < 200'000; ++i) {
        if (!producer.Produce("key", "value")) {
            any_failure = true;
            break;
        }
    }
    EXPECT_TRUE(any_failure)
        << "Expected at least one false return when broker is unreachable and queue fills";
}

}  // namespace deps
