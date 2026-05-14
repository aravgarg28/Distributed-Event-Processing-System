#include <csignal>
#include <cstdlib>
#include <iostream>
#include <memory>

#include "kafka_producer.h"
#include "server.h"

static deps::IngressServer* g_server = nullptr;

static void SignalHandler(int /*sig*/) {
    if (g_server) g_server->Shutdown();
}

int main() {
    const char* brokers_env = std::getenv("KAFKA_BROKERS");
    const char* topic_env   = std::getenv("KAFKA_TOPIC");
    const char* addr_env    = std::getenv("GRPC_LISTEN_ADDRESS");

    const std::string brokers = brokers_env ? brokers_env : "localhost:9092";
    const std::string topic   = topic_env   ? topic_env   : "events";
    const std::string address = addr_env    ? addr_env    : "0.0.0.0:50051";

    std::cout << "[main] brokers=" << brokers
              << " topic=" << topic
              << " grpc=" << address << "\n";

    auto producer = std::make_shared<deps::KafkaProducer>(brokers, topic);

    deps::IngressServer server(address, producer);
    g_server = &server;

    std::signal(SIGTERM, SignalHandler);
    std::signal(SIGINT,  SignalHandler);

    server.Run();
    return 0;
}
