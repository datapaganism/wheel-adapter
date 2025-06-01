#pragma once
#include <stdint.h>
#include "reports.h"

#define HEADER_BYTE_0 0xA1
#define HEADER_BYTE_1 0x36

typedef struct __attribute__((packed))
{
    uint16_t sync_phrase;
    uint8_t crc;
} header_t;

#define TX_FFB_DATA_LENGTH 7
#define RX_DATA_LENGTH (sizeof(g29_report_t) - (sizeof((g29_report_t*)0)->reserved + sizeof((g29_report_t*)0)->reserved3))

typedef struct __attribute__((packed))
{
    header_t header;
    uint8_t bytes[RX_DATA_LENGTH];
} rx_packet_t;


#define RX_PACKET_LEN (sizeof(rx_packet_t))

#define RX_TX_BUFFER_LEN ((256 - RX_PACKET_LEN) + RX_PACKET_LEN)




void rx_read();