#pragma once

#include <memory>
#include <string>

#include <grpcpp/grpcpp.h>

#include "event.grpc.pb.h"
#include "kafka_producer.h"
#include "metrics.h"

namespace deps {

// gRPC service implementation. Accepts events and hands them off to the
// IKafkaProducer — injected so unit tests can supply a mock.
// metrics is optional: pass nullptr to disable recording (test mode).
class EventIngressServiceImpl final : public deps::EventIngress::Service {
public:
    EventIngressServiceImpl(std::shared_ptr<IKafkaProducer> producer,
                             std::shared_ptr<IngressMetrics> metrics = nullptr);

    grpc::Status Submit(
        grpc::ServerContext*       ctx,
        const deps::SubmitRequest* req,
        deps::SubmitResponse*      resp) override;

    grpc::Status SubmitBatch(
        grpc::ServerContext*            ctx,
        const deps::SubmitBatchRequest* req,
        deps::SubmitResponse*           resp) override;

private:
    // Serialize event and forward to Kafka. Returns false on produce failure.
    bool PublishEvent(const deps::Event& event);

    std::shared_ptr<IKafkaProducer> producer_;
    std::shared_ptr<IngressMetrics> metrics_;
};

// Owns the gRPC server lifecycle.
class IngressServer {
public:
    IngressServer(const std::string&              address,
                  std::shared_ptr<IKafkaProducer> producer,
                  std::shared_ptr<IngressMetrics> metrics = nullptr);

    // Blocks until Shutdown() is called (e.g. from a signal handler).
    void Run();
    void Shutdown();

private:
    std::string                       address_;
    EventIngressServiceImpl           service_;
    std::unique_ptr<grpc::Server>     server_;
};

}  // namespace deps
