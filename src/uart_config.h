#pragma once

#include "pico/stdlib.h"
#include "hardware/uart.h"

#define UART_ID uart0
#define BAUD_RATE PICO_DEFAULT_UART_BAUD_RATE
#define DATA_BITS 8
#define STOP_BITS 1
#define PARITY    UART_PARITY_NONE

#define UART_TX_PIN PICO_DEFAULT_UART_TX_PIN
#define UART_RX_PIN PICO_DEFAULT_UART_RX_PIN