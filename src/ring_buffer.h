#pragma once

#include <stdint.h>
#include <stdio.h>
#include <stdbool.h>

#include "transport.h"

typedef struct __attribute__((packed))
{
    uint8_t buffer[RX_TX_BUFFER_LEN];
    volatile size_t head;
    volatile size_t tail;
    volatile size_t size;
} buffer_t;

uint8_t rb_push(buffer_t* buffer, uint8_t value);
uint8_t rb_pop(buffer_t* buffer, uint8_t* out);
uint8_t rb_pop_by(buffer_t* buffer, size_t amount);
uint8_t rb_peek(buffer_t* buffer, uint8_t* out, uint8_t offset);
uint8_t rb_reset(buffer_t* buffer);
bool rb_is_available(buffer_t *buffer, size_t size);




