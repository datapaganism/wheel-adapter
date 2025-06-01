#include "crc8.h"

uint8_t crc8_calculate(uint8_t *data, size_t length)
{
    uint8_t crc = 0;
    for (size_t i = 0; i < length; i++)
    {
        crc = crc8_lookup[crc ^ data[i]];
    }

    return crc;
}