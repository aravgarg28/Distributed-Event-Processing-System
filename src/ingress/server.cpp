#include "server.h"

#include <iostream>
#include <string>

#include <grpcpp/grpcpp.h>

#include "event.pb.h"

namespace deps {

// ---------------------------------------------------------------------------
// EventIngressServiceImpl
// ---------------------------------------------------------------------------

EventIngressServiceImpl::EventIngressServiceImpl(
    std::shared_ptr<IKafkaProducer> producer)
    : producer_(std::move(producer)) {}

bool EventIngressServiceImpl::PublishEvent(const deps::Event& event) {
    std::string serialized;
    if (!event.SerializeToString(&serialized)) {
        std::cerr << "[IngressService] proto serialization failed for event_id="
                  << event.event_id() << "\n";
        return false;
    }
    // entity_id is the partition key: the Kafka default partitioner (murmur2)
    // will hash it, which gives us the same distribution property as consistent
    // hashing at the broker level.
    return producer_->Produce(event.entity_id(), serialized);
}

grpc::Status EventIngressServiceImpl::Submit(
    grpc::ServerContext* /*ctx*/,
    const deps::SubmitRequest* req,
    deps::SubmitResponse*      resp) {

    if (!req->has_event()) {
        resp->set_success(false);
        resp->set_message("event field is required");
        resp->set_accepted_count(0);
        return grpc::Status(grpc::StatusCode::INVALID_ARGUMENT,
                            "event field is required");
    }

    if (PublishEvent(req->event())) {
        resp->set_success(true);
        resp->set_message("OK");
        resp->set_accepted_count(1);
        return grpc::Status::OK;
    }

    resp->set_success(false);
    resp->set_message("failed to publish to Kafka");
    resp->set_accepted_count(0);
    return grpc::Status(grpc::StatusCode::INTERNAL,
                        "failed to publish to Kafka");
}

grpc::Status EventIngressServiceImpl::SubmitBatch(
    grpc::ServerContext* /*ctx*/,
    const deps::SubmitBatchRequest* req,
    deps::SubmitResponse*           resp) {

    int accepted = 0;
    for (const auto& event : req->events()) {
        if (PublishEvent(event)) ++accepted;
    }

    const int total = req->events_size();
    resp->set_success(accepted == total);
    resp->set_message("accepted " + std::to_string(accepted) + "/" +
                      std::to_string(total));
    resp->set_accepted_count(accepted);
    return grpc::Status::OK;
}

// ---------------------------------------------------------------------------
// IngressServer
// ---------------------------------------------------------------------------

IngressServer::IngressServer(const std::string&              address,
                              std::shared_ptr<IKafkaProducer> producer)
    : address_(address), service_(std::move(producer)) {}

void IngressServer::Run() {
    grpc::ServerBuilder builder;
    builder.AddListeningPort(address_, grpc::InsecureServerCredentials());

    // Multi-threaded sync server: gRPC manages a thread pool internally.
    // Avoids blocking on high-traffic bursts without the full async CQ pattern.
    builder.SetSyncServerOption(grpc::ServerBuilder::NUM_CQS, 2);
    builder.SetSyncServerOption(grpc::ServerBuilder::MIN_POLLERS, 2);
    builder.SetSyncServerOption(grpc::ServerBuilder::MAX_POLLERS, 8);

    builder.RegisterService(&service_);

    server_ = builder.BuildAndStart();
    std::cout << "[IngressServer] listening on " << address_ << "\n";
    server_->Wait();
}

void IngressServer::Shutdown() {
    if (server_) server_->Shutdown();
}

}  // namespace deps
