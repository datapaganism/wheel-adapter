#include "ring_buffer.h"

uint8_t rb_push(buffer_t *buffer, uint8_t value)
{
    if (!buffer)
    {
        printf("no buffer\n");
        return 2;
    }

    if (((buffer->head + 1) % sizeof(buffer->buffer)) == buffer->tail)
    {
        printf("can't push\n");
        return 1;
    }

    buffer->buffer[buffer->head] = value;
    buffer->head = (buffer->head + 1) % sizeof(buffer->buffer);
    buffer->size++;

    return 0;
}

uint8_t rb_pop(buffer_t *buffer, uint8_t *out)
{
    if (!buffer)
    {
        printf("no buffer\n");
        return 2;
    }

    if ((buffer->head == buffer->tail) || (buffer->size == 0))
    {
        printf("pop fail empty\n");
        return 1;
    }

    if (out)
    {
        *out = buffer->buffer[buffer->tail];
    }

    buffer->tail = (buffer->tail + 1) % sizeof(buffer->buffer);
    buffer->size--;

    return 0;
}

uint8_t rb_pop_by(buffer_t *buffer, size_t amount)
{
    if (!buffer)
    {
        printf("no buffer\n");
        return 2;
    }

    for (size_t i; i < amount; i++)
    {
        if (!rb_pop(buffer, NULL))
        {
            printf("pop fail multiple\n");
            return 1;
        }
    }

    return 0;
}

uint8_t rb_peek(buffer_t *buffer, uint8_t *out, uint8_t offset)
{
    if (!buffer)
    {
        printf("no buffer\n");
        return 2;
    }

    if ((buffer->head == buffer->tail) || (buffer->size == 0))
    {
        printf("empty buffer\n");
        return 1;
    }

    *out = buffer->buffer[(buffer->tail + offset) % sizeof(buffer->buffer)];

    return 0;
}

uint8_t rb_reset(buffer_t *buffer)
{
    if (!buffer)
    {
        printf("no buffer\n");
        return 2;
    }

    buffer->head = buffer->tail = buffer->size = 0;
    return 0;
}

bool rb_is_available(buffer_t *buffer, size_t size)
{
    if (!buffer)
    {
        printf("no buffer\n");
        return false;
    }

    if (buffer->head == buffer->tail)
    {
        return false;
    }

    // size_t remaining = (buffer->head - buffer->tail) + (-((size_t) (end <= start)) & bufferSize);



    size_t available = (buffer->head >= buffer->tail) ? (buffer->head - buffer->tail) : (sizeof(buffer->buffer) - buffer->tail + buffer->head);
    printf("available %i\n", available);
    return (available >= size);

}
