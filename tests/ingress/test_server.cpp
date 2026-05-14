#include <gmock/gmock.h>
#include <gtest/gtest.h>

#include "server.h"

namespace deps {
namespace {

// ---------------------------------------------------------------------------
// Mock
// ---------------------------------------------------------------------------

class MockKafkaProducer : public IKafkaProducer {
public:
    MOCK_METHOD(bool, Produce,
                (const std::string& key, const std::string& value), (override));
    MOCK_METHOD(void, Flush, (int timeout_ms), (override));
};

// ---------------------------------------------------------------------------
// Fixture
// ---------------------------------------------------------------------------

class ServerTest : public ::testing::Test {
protected:
    void SetUp() override {
        mock    = std::make_shared<MockKafkaProducer>();
        service = std::make_unique<EventIngressServiceImpl>(mock);
    }

    std::shared_ptr<MockKafkaProducer>   mock;
    std::unique_ptr<EventIngressServiceImpl> service;
};

// Helper: build a minimal valid Event
static deps::Event MakeEvent(const std::string& entity_id) {
    deps::Event e;
    e.set_event_id("evt-" + entity_id);
    e.set_entity_id(entity_id);
    e.set_event_type("test.event");
    e.set_timestamp_ms(1700000000000LL);
    return e;
}

// ---------------------------------------------------------------------------
// Submit — single event
// ---------------------------------------------------------------------------

TEST_F(ServerTest, SubmitPublishesWithEntityIdAsKey) {
    EXPECT_CALL(*mock, Produce(testing::Eq("entity-abc"), testing::_))
        .WillOnce(testing::Return(true));

    SubmitRequest req;
    *req.mutable_event() = MakeEvent("entity-abc");

    SubmitResponse   resp;
    grpc::ServerContext ctx;
    auto status = service->Submit(&ctx, &req, &resp);

    EXPECT_TRUE(status.ok());
    EXPECT_TRUE(resp.success());
    EXPECT_EQ(resp.accepted_count(), 1);
}

TEST_F(ServerTest, SubmitReturnsInternalWhenKafkaFails) {
    EXPECT_CALL(*mock, Produce(testing::_, testing::_))
        .WillOnce(testing::Return(false));

    SubmitRequest req;
    *req.mutable_event() = MakeEvent("entity-xyz");

    SubmitResponse   resp;
    grpc::ServerContext ctx;
    auto status = service->Submit(&ctx, &req, &resp);

    EXPECT_EQ(status.error_code(), grpc::StatusCode::INTERNAL);
    EXPECT_FALSE(resp.success());
    EXPECT_EQ(resp.accepted_count(), 0);
}

TEST_F(ServerTest, SubmitWithNoEventReturnsInvalidArgument) {
    // Producer must never be called for an empty request
    EXPECT_CALL(*mock, Produce(testing::_, testing::_)).Times(0);

    SubmitRequest req;  // event field intentionally absent
    SubmitResponse   resp;
    grpc::ServerContext ctx;
    auto status = service->Submit(&ctx, &req, &resp);

    EXPECT_EQ(status.error_code(), grpc::StatusCode::INVALID_ARGUMENT);
    EXPECT_FALSE(resp.success());
}

// ---------------------------------------------------------------------------
// SubmitBatch
// ---------------------------------------------------------------------------

TEST_F(ServerTest, SubmitBatchPublishesAllEventsSuccessfully) {
    EXPECT_CALL(*mock, Produce(testing::_, testing::_))
        .Times(3)
        .WillRepeatedly(testing::Return(true));

    SubmitBatchRequest req;
    for (int i = 0; i < 3; ++i)
        *req.add_events() = MakeEvent("entity-" + std::to_string(i));

    SubmitResponse   resp;
    grpc::ServerContext ctx;
    auto status = service->SubmitBatch(&ctx, &req, &resp);

    EXPECT_TRUE(status.ok());
    EXPECT_TRUE(resp.success());
    EXPECT_EQ(resp.accepted_count(), 3);
}

TEST_F(ServerTest, SubmitBatchReportsPartialFailures) {
    // Second produce call fails; the rest succeed
    EXPECT_CALL(*mock, Produce(testing::_, testing::_))
        .WillOnce(testing::Return(true))
        .WillOnce(testing::Return(false))
        .WillOnce(testing::Return(true));

    SubmitBatchRequest req;
    for (int i = 0; i < 3; ++i)
        *req.add_events() = MakeEvent("entity-" + std::to_string(i));

    SubmitResponse   resp;
    grpc::ServerContext ctx;
    auto status = service->SubmitBatch(&ctx, &req, &resp);

    EXPECT_TRUE(status.ok());           // batch RPC itself succeeded
    EXPECT_FALSE(resp.success());       // not all events accepted
    EXPECT_EQ(resp.accepted_count(), 2);
}

TEST_F(ServerTest, SubmitBatchWithEmptyListSucceedsWithZeroAccepted) {
    EXPECT_CALL(*mock, Produce(testing::_, testing::_)).Times(0);

    SubmitBatchRequest req;  // no events
    SubmitResponse   resp;
    grpc::ServerContext ctx;
    auto status = service->SubmitBatch(&ctx, &req, &resp);

    EXPECT_TRUE(status.ok());
    EXPECT_TRUE(resp.success());
    EXPECT_EQ(resp.accepted_count(), 0);
}

}  // namespace
}  // namespace deps
