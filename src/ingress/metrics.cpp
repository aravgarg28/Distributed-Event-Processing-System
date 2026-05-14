#include "metrics.h"

#include <prometheus/counter.h>
#include <prometheus/exposer.h>
#include <prometheus/histogram.h>
#include <prometheus/registry.h>

namespace deps {

IngressMetrics::IngressMetrics(const std::string& bind_address,
                                bool start_http_server)
    : registry_(std::make_shared<prometheus::Registry>()) {

    requests_total_ = &prometheus::BuildCounter()
        .Name("deps_ingress_requests_total")
        .Help("Total gRPC requests received by the ingress service")
        .Register(*registry_);

    errors_total_ = &prometheus::BuildCounter()
        .Name("deps_ingress_requests_errors_total")
        .Help("Total gRPC requests that resulted in a non-OK status")
        .Register(*registry_);

    duration_seconds_ = &prometheus::BuildHistogram()
        .Name("deps_ingress_request_duration_seconds")
        .Help("gRPC request processing latency in seconds")
        .Register(*registry_);

    kafka_published_ = &prometheus::BuildCounter()
        .Name("deps_ingress_kafka_published_total")
        .Help("Total events successfully enqueued into the Kafka producer")
        .Register(*registry_);

    kafka_errors_ = &prometheus::BuildCounter()
        .Name("deps_ingress_kafka_publish_errors_total")
        .Help("Total Kafka produce failures")
        .Register(*registry_);

    if (start_http_server) {
        exposer_ = std::make_unique<prometheus::Exposer>(bind_address);
        exposer_->RegisterCollectable(registry_);
    }
}

IngressMetrics::~IngressMetrics() = default;

void IngressMetrics::RecordRequest(const std::string& method,
                                    bool success,
                                    double duration_s) {
    static const prometheus::Histogram::BucketBoundaries kBuckets{
        .0001, .0005, .001, .005, .01, .025, .05, .1, .25, .5, 1.0
    };

    requests_total_->Add({{"method", method}}).Increment();

    if (!success) {
        errors_total_->Add({{"method", method}}).Increment();
    }

    duration_seconds_
        ->Add({{"method", method}}, kBuckets)
        .Observe(duration_s);
}

void IngressMetrics::RecordKafkaPublish(bool success) {
    if (success) {
        kafka_published_->Add({}).Increment();
    } else {
        kafka_errors_->Add({}).Increment();
    }
}

std::shared_ptr<prometheus::Registry> IngressMetrics::GetRegistry() const {
    return registry_;
}

}  // namespace deps
