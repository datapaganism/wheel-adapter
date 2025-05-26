#pragma once
#include <stdint.h>

#define HEADER_BYTE_0 0xA1
#define HEADER_BYTE_1 0x36

typedef struct __attribute__((packed))
{
    uint16_t sync_phrase;
} header_t;

#define MESSAGE_LEN 16

typedef struct __attribute__((packed))
{
    header_t header;
    uint8_t bytes[MESSAGE_LEN];
} packet_t;


#define PACKET_LEN (sizeof(packet_t))

#define RX_TX_BUFFER_LEN ((256 - PACKET_LEN) + PACKET_LEN)




void rx_read();