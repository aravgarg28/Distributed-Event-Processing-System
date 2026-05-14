#include "server.h"

#include <chrono>
#include <iostream>
#include <string>

#include <grpcpp/grpcpp.h>

#include "event.pb.h"

namespace deps {

// ---------------------------------------------------------------------------
// EventIngressServiceImpl
// ---------------------------------------------------------------------------

EventIngressServiceImpl::EventIngressServiceImpl(
    std::shared_ptr<IKafkaProducer> producer,
    std::shared_ptr<IngressMetrics> metrics)
    : producer_(std::move(producer)), metrics_(std::move(metrics)) {}

bool EventIngressServiceImpl::PublishEvent(const deps::Event& event) {
    std::string serialized;
    if (!event.SerializeToString(&serialized)) {
        std::cerr << "[IngressService] proto serialization failed for event_id="
                  << event.event_id() << "\n";
        if (metrics_) metrics_->RecordKafkaPublish(false);
        return false;
    }
    const bool ok = producer_->Produce(event.entity_id(), serialized);
    if (metrics_) metrics_->RecordKafkaPublish(ok);
    return ok;
}

grpc::Status EventIngressServiceImpl::Submit(
    grpc::ServerContext* /*ctx*/,
    const deps::SubmitRequest* req,
    deps::SubmitResponse*      resp) {

    const auto t0 = std::chrono::steady_clock::now();

    if (!req->has_event()) {
        resp->set_success(false);
        resp->set_message("event field is required");
        resp->set_accepted_count(0);
        if (metrics_) {
            const double dur = std::chrono::duration<double>(
                std::chrono::steady_clock::now() - t0).count();
            metrics_->RecordRequest("Submit", false, dur);
        }
        return grpc::Status(grpc::StatusCode::INVALID_ARGUMENT,
                            "event field is required");
    }

    const bool ok = PublishEvent(req->event());
    const double dur = std::chrono::duration<double>(
        std::chrono::steady_clock::now() - t0).count();

    if (ok) {
        resp->set_success(true);
        resp->set_message("OK");
        resp->set_accepted_count(1);
        if (metrics_) metrics_->RecordRequest("Submit", true, dur);
        return grpc::Status::OK;
    }

    resp->set_success(false);
    resp->set_message("failed to publish to Kafka");
    resp->set_accepted_count(0);
    if (metrics_) metrics_->RecordRequest("Submit", false, dur);
    return grpc::Status(grpc::StatusCode::INTERNAL,
                        "failed to publish to Kafka");
}

grpc::Status EventIngressServiceImpl::SubmitBatch(
    grpc::ServerContext* /*ctx*/,
    const deps::SubmitBatchRequest* req,
    deps::SubmitResponse*           resp) {

    const auto t0 = std::chrono::steady_clock::now();

    int accepted = 0;
    for (const auto& event : req->events()) {
        if (PublishEvent(event)) ++accepted;
    }

    const double dur = std::chrono::duration<double>(
        std::chrono::steady_clock::now() - t0).count();
    const int total = req->events_size();
    const bool all_ok = (accepted == total);

    resp->set_success(all_ok);
    resp->set_message("accepted " + std::to_string(accepted) + "/" +
                      std::to_string(total));
    resp->set_accepted_count(accepted);

    if (metrics_) metrics_->RecordRequest("SubmitBatch", all_ok, dur);
    return grpc::Status::OK;
}

// ---------------------------------------------------------------------------
// IngressServer
// ---------------------------------------------------------------------------

IngressServer::IngressServer(const std::string&              address,
                              std::shared_ptr<IKafkaProducer> producer,
                              std::shared_ptr<IngressMetrics> metrics)
    : address_(address),
      service_(std::move(producer), std::move(metrics)) {}

void IngressServer::Run() {
    grpc::ServerBuilder builder;
    builder.AddListeningPort(address_, grpc::InsecureServerCredentials());
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
