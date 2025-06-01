cmake_minimum_required(VERSION 3.13)
set(target_name adapter)

set(BAUD "115200")
add_compile_definitions(PICO_DEFAULT_UART_BAUD_RATE=${BAUD})
add_compile_definitions(PICO_DEFAULT_UART_TX_PIN=16)
add_compile_definitions(PICO_DEFAULT_UART_RX_PIN=17)
add_compile_definitions(PICO_DEFAULT_PIO_USB_DP_PIN=0)
# add_compile_definitions(CFG_TUSB_DEBUG=3)

set(PICO_SDK_PATH "${CMAKE_CURRENT_LIST_DIR}/pico-sdk")
set(PICO_TINYUSB_PATH "${CMAKE_CURRENT_LIST_DIR}/tinyusb")
set(PICO_PIO_USB_PATH "${CMAKE_CURRENT_LIST_DIR}/Pico-PIO-USB")


include(pico_sdk_import.cmake)


project(${target_name})


pico_sdk_init()

add_executable(${target_name}
    src/adapter.c
    src/descriptors.c
    src/ring_buffer.c
    src/crc8.c
)
target_include_directories(${target_name} PRIVATE src)

target_link_libraries(${target_name}
    pico_stdlib
    tinyusb_host
    tinyusb_device
    tinyusb_board
    tinyusb_pico_pio_usb
)


pico_add_extra_outputs(${target_name})
pico_enable_stdio_usb(${target_name} 0)
pico_enable_stdio_uart(${target_name} 1)