find_package(GTest REQUIRED)

add_executable(ingress_tests
    test_server.cpp
    test_kafka_producer.cpp
    test_metrics.cpp
)
target_include_directories(ingress_tests PRIVATE
    "${CMAKE_SOURCE_DIR}/src/ingress"
    "${CMAKE_BINARY_DIR}/proto"
)
target_link_libraries(ingress_tests PRIVATE
    ingress_lib
    GTest::gtest
    GTest::gtest_main
    GTest::gmock
)
add_test(NAME ingress_tests COMMAND ingress_tests)
