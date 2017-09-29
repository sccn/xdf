cmake_minimum_required(VERSION 3.7)
set(CMAKE_OSX_DEPLOYMENT_TARGET 10.9)

project(libxdf)

set(SOURCES
    xdf.h
    xdf.cpp
    pugixml/pugiconfig.hpp
    pugixml/pugixml.hpp
    pugixml/pugixml.cpp
    smarc/filtering.h
    smarc/filtering.c
    smarc/multi_stage.h
    smarc/multi_stage.c
    smarc/polyfilt.h
    smarc/polyfilt.c
    smarc/remez_lp.h
    smarc/remez_lp.c
    smarc/smarc.h
    smarc/smarc.c
    smarc/stage_impl.h
    smarc/stage_impl.c
)

add_library(xdf-static STATIC ${SOURCES})
add_library(xdf-shared SHARED ${SOURCES})

set_property(TARGET xdf-static xdf-shared PROPERTY CXX_STANDARD 11)
set_property(TARGET xdf-static xdf-shared PROPERTY C_STANDARD 99)
set_target_properties(xdf-static PROPERTIES OUTPUT_NAME xdf)
set_target_properties(xdf-shared PROPERTIES OUTPUT_NAME xdf)
