#pragma once
#include <stdint.h>

#define SYNC_PHRASE 0xF0CC
#define HEADER_BYTE_1 0xA1
#define HEADER_BYTE_2 0x36

typedef struct __attribute__((packed))
{
    uint16_t sync_phrase;
    // uint8_t payload_length;
} header_t;

#define MESSAGE_LEN 16

typedef struct __attribute__((packed))
{
    header_t header;
    uint8_t bytes[MESSAGE_LEN];
} packet_t;

typedef struct __attribute__((packed))
{
    packet_t packet;
    uint8_t paddinglmao[128];
} transport_t;

#define PACKET_LEN (sizeof(packet_t))

#define RX_TX_BUFFER_LEN (sizeof(transport_t))




void rx_read();