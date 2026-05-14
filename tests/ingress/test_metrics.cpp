#include <gtest/gtest.h>

#include <prometheus/registry.h>

#include "metrics.h"

namespace deps {
namespace {

// Helper: sum all sample values across all metrics in a family by name.
static double SumFamily(const std::shared_ptr<prometheus::Registry>& reg,
                        const std::string& name) {
    double total = 0.0;
    for (const auto& family : reg->Collect()) {
        if (family.name != name) continue;
        for (const auto& metric : family.metric) {
            total += metric.counter.value;
        }
    }
    return total;
}

// Helper: check that a named family exists in the registry.
static bool FamilyExists(const std::shared_ptr<prometheus::Registry>& reg,
                          const std::string& name) {
    for (const auto& family : reg->Collect()) {
        if (family.name == name) return true;
    }
    return false;
}

// ---------------------------------------------------------------------------
// Tests — no HTTP server started (start_http_server=false)
// ---------------------------------------------------------------------------

TEST(IngressMetricsTest, AllExpectedFamiliesRegistered) {
    IngressMetrics m("", false);
    auto reg = m.GetRegistry();

    EXPECT_TRUE(FamilyExists(reg, "deps_ingress_requests_total"));
    EXPECT_TRUE(FamilyExists(reg, "deps_ingress_requests_errors_total"));
    EXPECT_TRUE(FamilyExists(reg, "deps_ingress_request_duration_seconds"));
    EXPECT_TRUE(FamilyExists(reg, "deps_ingress_kafka_published_total"));
    EXPECT_TRUE(FamilyExists(reg, "deps_ingress_kafka_publish_errors_total"));
}

TEST(IngressMetricsTest, RecordSuccessfulRequestIncrementsTotal) {
    IngressMetrics m("", false);
    m.RecordRequest("Submit", true, 0.001);
    m.RecordRequest("Submit", true, 0.002);

    EXPECT_DOUBLE_EQ(SumFamily(m.GetRegistry(), "deps_ingress_requests_total"), 2.0);
    EXPECT_DOUBLE_EQ(SumFamily(m.GetRegistry(), "deps_ingress_requests_errors_total"), 0.0);
}

TEST(IngressMetricsTest, RecordFailedRequestIncrementsBothTotalAndError) {
    IngressMetrics m("", false);
    m.RecordRequest("Submit", false, 0.05);

    EXPECT_DOUBLE_EQ(SumFamily(m.GetRegistry(), "deps_ingress_requests_total"), 1.0);
    EXPECT_DOUBLE_EQ(SumFamily(m.GetRegistry(), "deps_ingress_requests_errors_total"), 1.0);
}

TEST(IngressMetricsTest, RecordKafkaPublishSuccessIncrementPublished) {
    IngressMetrics m("", false);
    m.RecordKafkaPublish(true);
    m.RecordKafkaPublish(true);

    EXPECT_DOUBLE_EQ(SumFamily(m.GetRegistry(), "deps_ingress_kafka_published_total"), 2.0);
    EXPECT_DOUBLE_EQ(SumFamily(m.GetRegistry(), "deps_ingress_kafka_publish_errors_total"), 0.0);
}

TEST(IngressMetricsTest, RecordKafkaPublishFailureIncrementErrors) {
    IngressMetrics m("", false);
    m.RecordKafkaPublish(false);

    EXPECT_DOUBLE_EQ(SumFamily(m.GetRegistry(), "deps_ingress_kafka_publish_errors_total"), 1.0);
    EXPECT_DOUBLE_EQ(SumFamily(m.GetRegistry(), "deps_ingress_kafka_published_total"), 0.0);
}

TEST(IngressMetricsTest, MultipleMethodsTrackedIndependently) {
    IngressMetrics m("", false);
    m.RecordRequest("Submit",      true, 0.001);
    m.RecordRequest("Submit",      true, 0.002);
    m.RecordRequest("SubmitBatch", true, 0.010);

    // All three requests land in the same family; total = 3.
    EXPECT_DOUBLE_EQ(SumFamily(m.GetRegistry(), "deps_ingress_requests_total"), 3.0);
}

}  // namespace
}  // namespace deps
