#pragma once

#include <memory>
#include <string>

namespace deps {

// Abstract interface — lets test doubles replace the real librdkafka producer.
class IKafkaProducer {
public:
    virtual ~IKafkaProducer() = default;

    // Async produce. key routes the message to the correct partition (entity_id).
    // Returns false if the local queue is full or the broker is unreachable.
    virtual bool Produce(const std::string& key, const std::string& value) = 0;

    // Block until all queued messages are delivered or timeout_ms elapses.
    virtual void Flush(int timeout_ms = 5000) = 0;
};

// Concrete librdkafka implementation. PIMPL hides rdkafka headers from callers.
class KafkaProducer : public IKafkaProducer {
public:
    KafkaProducer(const std::string& brokers, const std::string& topic);
    ~KafkaProducer() override;

    KafkaProducer(const KafkaProducer&)            = delete;
    KafkaProducer& operator=(const KafkaProducer&) = delete;

    bool Produce(const std::string& key, const std::string& value) override;
    void Flush(int timeout_ms = 5000) override;

private:
    struct Impl;
    std::unique_ptr<Impl> impl_;
};

}  // namespace deps
