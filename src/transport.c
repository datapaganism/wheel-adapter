#include "transport.h"

#include "stdio.h"
#include "uart_config.h"
#include "pico/stdlib.h"
#include "hardware/uart.h"




void rx_read() {

    // uart_read_blocking(UART_ID, (uint8_t*)&rx_buffer.buffer, sizeof(header_t));
    
    // transport_t* t_ptr = (transport_t*)&rx_buffer.buffer;
    // t_ptr->header.sync_phrase;
    // printf("sync %x\n", t_ptr->header.sync_phrase);

}