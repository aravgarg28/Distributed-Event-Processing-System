#include "kafka_producer.h"

#include <iostream>
#include <stdexcept>

#include <librdkafka/rdkafkacpp.h>

namespace deps {

// ---------------------------------------------------------------------------
// PIMPL internals
// ---------------------------------------------------------------------------

struct KafkaProducer::Impl {
    // Logs delivery failures to stderr; successes are silently discarded to
    // keep the hot path allocation-free.
    class DeliveryReportCb : public RdKafka::DeliveryReportCb {
    public:
        void dr_cb(RdKafka::Message& msg) override {
            if (msg.err()) {
                std::cerr << "[KafkaProducer] delivery failed topic="
                          << msg.topic_name()
                          << " err=" << msg.errstr() << "\n";
            }
        }
    } dr_cb;

    std::unique_ptr<RdKafka::Producer> producer;
    std::string                         topic_name;
};

// ---------------------------------------------------------------------------
// KafkaProducer
// ---------------------------------------------------------------------------

KafkaProducer::KafkaProducer(const std::string& brokers,
                              const std::string& topic)
    : impl_(std::make_unique<Impl>()) {
    std::string errstr;

    auto conf =
        std::unique_ptr<RdKafka::Conf>(RdKafka::Conf::create(RdKafka::Conf::CONF_GLOBAL));

    auto set = [&](const char* key, const char* val) {
        if (conf->set(key, val, errstr) != RdKafka::Conf::CONF_OK)
            throw std::runtime_error(std::string("Kafka conf ") + key + ": " + errstr);
    };

    set("bootstrap.servers", brokers.c_str());
    set("dr_cb",             "");  // placeholder; real cb set below

    if (conf->set("dr_cb", &impl_->dr_cb, errstr) != RdKafka::Conf::CONF_OK)
        throw std::runtime_error("Kafka conf dr_cb: " + errstr);

    // Tune for throughput: batch up to 5 ms of messages before flushing.
    set("linger.ms",            "5");
    set("batch.num.messages",   "10000");
    set("compression.type",     "lz4");

    impl_->producer.reset(RdKafka::Producer::create(conf.get(), errstr));
    if (!impl_->producer)
        throw std::runtime_error("Failed to create Kafka producer: " + errstr);

    impl_->topic_name = topic;
}

KafkaProducer::~KafkaProducer() {
    Flush(10'000);
}

bool KafkaProducer::Produce(const std::string& key, const std::string& value) {
    RdKafka::ErrorCode err = impl_->producer->produce(
        impl_->topic_name,
        RdKafka::Topic::PARTITION_UA,           // partitioner chooses shard via key
        RdKafka::Producer::RK_MSG_COPY,         // copy payload — caller owns its buffer
        const_cast<void*>(static_cast<const void*>(value.data())),
        value.size(),
        key.data(),
        key.size(),
        0,       // timestamp: 0 = broker assigns current time
        nullptr  // msg_opaque
    );

    if (err != RdKafka::ERR_NO_ERROR) {
        std::cerr << "[KafkaProducer] produce failed: "
                  << RdKafka::err2str(err) << "\n";
        return false;
    }

    // Poll with zero timeout to serve delivery-report callbacks without blocking.
    impl_->producer->poll(0);
    return true;
}

void KafkaProducer::Flush(int timeout_ms) {
    impl_->producer->flush(timeout_ms);
}

}  // namespace deps
