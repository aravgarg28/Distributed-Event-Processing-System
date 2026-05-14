#pragma once

#include <memory>
#include <string>

// Forward-declare so callers that only hold a pointer don't need the full
// prometheus headers compiled into their translation units.
namespace prometheus {
class Registry;
class Exposer;
template <typename T>
class Family;
class Counter;
class Histogram;
}  // namespace prometheus

namespace deps {

// IngressMetrics owns the prometheus Registry and the CivetWeb HTTP exposer.
// Callers record individual RPC outcomes; the exposer serves /metrics on the
// configured port for Prometheus to scrape.
//
// PIMPL is *not* used here because the forward declarations above are
// sufficient to keep the prometheus headers out of server.h / kafka_producer.h.
class IngressMetrics {
public:
    // start_http_server=false skips starting the CivetWeb exposer — used in
    // unit tests to avoid binding a real port.
    explicit IngressMetrics(const std::string& bind_address = "0.0.0.0:8080",
                            bool start_http_server = true);
    ~IngressMetrics();

    IngressMetrics(const IngressMetrics&)            = delete;
    IngressMetrics& operator=(const IngressMetrics&) = delete;

    // Record one completed Submit or SubmitBatch RPC.
    // method: "Submit" | "SubmitBatch"
    void RecordRequest(const std::string& method, bool success, double duration_s);

    // Record one Kafka produce attempt from PublishEvent().
    void RecordKafkaPublish(bool success);

    // Expose the registry for test introspection (collect metric families).
    std::shared_ptr<prometheus::Registry> GetRegistry() const;

private:
    std::shared_ptr<prometheus::Registry>  registry_;
    std::unique_ptr<prometheus::Exposer>   exposer_;

    prometheus::Family<prometheus::Counter>*   requests_total_;
    prometheus::Family<prometheus::Counter>*   errors_total_;
    prometheus::Family<prometheus::Histogram>* duration_seconds_;
    prometheus::Family<prometheus::Counter>*   kafka_published_;
    prometheus::Family<prometheus::Counter>*   kafka_errors_;
};

}  // namespace deps
