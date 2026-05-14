find_package(Protobuf REQUIRED)
find_package(gRPC    CONFIG REQUIRED)
find_package(PkgConfig REQUIRED)
pkg_check_modules(RDKAFKA REQUIRED rdkafka++)

find_program(PROTOC_EXEC      protoc         REQUIRED)
find_program(GRPC_CPP_PLUGIN  grpc_cpp_plugin REQUIRED)

# ---------------------------------------------------------------------------
# prometheus-cpp — fetched at configure time; statically linked
# ---------------------------------------------------------------------------
include(FetchContent)
FetchContent_Declare(
    prometheus-cpp
    GIT_REPOSITORY https://github.com/jupp0r/prometheus-cpp.git
    GIT_TAG        v1.2.4
    GIT_SHALLOW    TRUE
)
set(ENABLE_TESTING    OFF CACHE BOOL "" FORCE)
set(ENABLE_COMPRESSION OFF CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(prometheus-cpp)

# ---------------------------------------------------------------------------
# Proto code generation
# ---------------------------------------------------------------------------

set(PROTO_OUT_DIR "${CMAKE_BINARY_DIR}/proto")
file(MAKE_DIRECTORY "${PROTO_OUT_DIR}")

add_custom_command(
    OUTPUT
        "${PROTO_OUT_DIR}/event.pb.cc"
        "${PROTO_OUT_DIR}/event.pb.h"
        "${PROTO_OUT_DIR}/event.grpc.pb.cc"
        "${PROTO_OUT_DIR}/event.grpc.pb.h"
    COMMAND "${PROTOC_EXEC}"
        --cpp_out  "${PROTO_OUT_DIR}"
        --grpc_out "${PROTO_OUT_DIR}"
        "--plugin=protoc-gen-grpc=${GRPC_CPP_PLUGIN}"
        -I "${CMAKE_CURRENT_SOURCE_DIR}"
        "${CMAKE_CURRENT_SOURCE_DIR}/event.proto"
    DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/event.proto"
    COMMENT "Compiling event.proto → C++ (pb + grpc)"
)

add_library(event_proto OBJECT
    "${PROTO_OUT_DIR}/event.pb.cc"
    "${PROTO_OUT_DIR}/event.grpc.pb.cc"
)
target_include_directories(event_proto PUBLIC "${PROTO_OUT_DIR}")
target_link_libraries(event_proto PUBLIC protobuf::libprotobuf gRPC::grpc++)

# ---------------------------------------------------------------------------
# ingress_lib — core logic, shared by binary and test suite
# ---------------------------------------------------------------------------

add_library(ingress_lib STATIC
    kafka_producer.cpp
    metrics.cpp
    server.cpp
)
target_include_directories(ingress_lib
    PUBLIC  "${CMAKE_CURRENT_SOURCE_DIR}" "${PROTO_OUT_DIR}"
    PRIVATE ${RDKAFKA_INCLUDE_DIRS}
)
target_link_libraries(ingress_lib
    PUBLIC  event_proto gRPC::grpc++ protobuf::libprotobuf
            prometheus-cpp::pull prometheus-cpp::core
    PRIVATE ${RDKAFKA_LIBRARIES}
)

# ---------------------------------------------------------------------------
# ingress_server binary
# ---------------------------------------------------------------------------

add_executable(ingress_server main.cpp)
target_link_libraries(ingress_server PRIVATE ingress_lib)
