project(PackageTest C)
cmake_minimum_required(VERSION 3.0)

include(${CMAKE_CURRENT_BINARY_DIR}/conanbuildinfo.cmake)
conan_basic_setup(TARGETS)

enable_testing()

add_executable(test_pcre2_CONAN_PKG test_pcre.c)
target_link_libraries(test_pcre2_CONAN_PKG CONAN_PKG::pcre2)
set_target_properties(test_pcre2_CONAN_PKG
    PROPERTIES
    INSTALL_RPATH "$ORIGIN"
    BUILD_WITH_INSTALL_RPATH True
)
add_test(
    NAME test_pcre2_CONAN_PKG
    WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/bin
    COMMAND test_pcre2_CONAN_PKG
)

find_package(PCRE2 REQUIRED)
message(STATUS "PCRE2_VERSION: ${PCRE2_VERSION}")

add_executable(test_pcre2 test_pcre.c)
target_link_libraries(test_pcre2 PCRE2::PCRE2)
set_target_properties(test_pcre2
    PROPERTIES
    INSTALL_RPATH "$ORIGIN"
    BUILD_WITH_INSTALL_RPATH True
)
add_test(
    NAME test_pcre2
    WORKING_DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/bin
    COMMAND test_pcre2
)
