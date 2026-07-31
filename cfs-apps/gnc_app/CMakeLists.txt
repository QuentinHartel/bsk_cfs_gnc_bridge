cmake_minimum_required(VERSION 3.5)
project(CFE_GNC_APP C)

add_cfe_app(gnc_app fsw/src/gnc_app.c)

target_include_directories(gnc_app PUBLIC fsw/inc)
