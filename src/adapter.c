#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "bsp/board_api.h"
#include "tusb.h"

#include "pico/stdio.h"

#include "reports.h"
#include "transport.h"
#include "uart_config.h"
#include "ring_buffer.h"
#include "debugprintf.h"
#include "crc8.h"

#include "pico/stdlib.h"
#include "hardware/uart.h"
#include "hardware/irq.h"

buffer_t rx_buffer;
buffer_t tx_buffer;

int UART_IRQ = UART_ID == uart0 ? UART0_IRQ : UART1_IRQ;

uint8_t nonce_id;
uint8_t nonce[280];
uint8_t nonce_part = 0;
uint8_t signature[1064];
uint8_t signature_part = 0;
uint8_t signature_ready = 0;
uint8_t nonce_ready = 0;

uint8_t expected_part = 0;

uint8_t wheel_device = 0;
uint8_t wheel_instance = 0;
uint8_t auth_device = 0;
uint8_t auth_instance = 0;

bool busy = false;

enum {
    IDLE = 0,
    SENDING_RESET = 1,
    SENDING_NONCE = 2,
    WAITING_FOR_SIG = 3,
    RECEIVING_SIG = 4,
};

uint8_t state = IDLE;

bool initialized = true;

uint8_t get_buffer[64];
uint8_t set_buffer[64];
uint8_t ff_buf[TX_FFB_DATA_LENGTH] = { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00 };
uint8_t prev_ff_buf[TX_FFB_DATA_LENGTH] = { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00 };

g29_report_t report;
g29_report_t prev_report;

// G29
const uint8_t output_0x03[] = {
    0x21, 0x27, 0x03, 0x11, 0x06, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x0D, 0x0D, 0x00, 0x00, 0x00, 0x00,
    0x0D, 0x84, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
};

const uint8_t output_0xf3[] = { 0x0, 0x38, 0x38, 0, 0, 0, 0 };


void dump_g29_report(g29_report_t* report)
{
    debugprintf("ry     is 0x%x\n", report->ry);
    debugprintf("wheel  is 0x%x\n", report->wheel);
    debugprintf("clutch is 0x%x\n", report->clutch);
}

void unpack_buffer_to_g29(uint8_t* buffer, g29_report_t* report)
{
    const uint8_t skip1_len = sizeof(((g29_report_t*)0)->reserved);
    const uint8_t skip2_len = sizeof(((g29_report_t*)0)->reserved2);
    
    uint8_t* b = buffer;
    uint8_t* r = (uint8_t*)report;
    size_t remaining = RX_DATA_LENGTH;
    uint8_t to_copy = 0;
    uint8_t bytes_written = 0;


    // Copy first 7 bytes of report
    to_copy = 7;
    memcpy(r,b, to_copy);
    b += to_copy;
    r += to_copy;
    bytes_written += to_copy;

    // Skip the next 35 bytes
    r += skip1_len;

    // Copy the next 9 bytes
    to_copy = 9;
    memcpy(r,b, to_copy);
    b += to_copy;
    r += (to_copy);
    bytes_written += to_copy;

    // Skip the next 2 bytes
    r += skip2_len;
    
    // Copy remainder
    memcpy(r,b, RX_DATA_LENGTH - bytes_written);

    // dump_g29_report(report);
}


void on_uart_irq0() {
    if(uart_is_readable(uart0)) {
        uint8_t byte_got = uart_getc(uart0);
        rb_push(&rx_buffer, byte_got);
    }
}

void setup_uart(){
	uart_init(UART_ID,BAUD_RATE);
    uart_set_hw_flow(UART_ID, false, false);
    uart_set_format(UART_ID, DATA_BITS, STOP_BITS, PARITY);
    uart_set_fifo_enabled(UART_ID, false);
    UART_IRQ = UART_ID == uart0 ? UART0_IRQ : UART1_IRQ;

    // if(uart){
	// 	irq_set_exclusive_handler(UART_IRQ, on_uart_irq1);
    // 	irq_set_enabled(UART_IRQ, true);
	// } else {
    irq_set_exclusive_handler(UART_IRQ, on_uart_irq0);
    irq_set_enabled(UART_IRQ, true);
	// }
    uart_set_irq_enables(UART_ID, true, false);

#ifdef DEBUG_PRINT
    uart_puts(UART_ID, "UART is ready\n");
#endif

}


uint8_t pusb_ffb_packet_to_tx_buffer(buffer_t* b, uint8_t* payload, uint8_t payload_len)
{
    if ((sizeof(b->buffer) - b->size) >= (payload_len + sizeof(header_t)))
    {
        rb_push(b, HEADER_BYTE_0);
        rb_push(b, HEADER_BYTE_1);
        for (uint8_t i = 0; i < payload_len; i++)
        {
            rb_push(b, *(payload + i));
        }

        return 0;
    }

    return 1;
}

bool get_payload(buffer_t *b, uint8_t *payload_out)
{
    uint8_t sync_0;
    uint8_t sync_1;
    uint8_t crc;
    while (b->size >= RX_PACKET_LEN)
    {

        if (rb_pop(b, &sync_0) != 0)
        {
            return false;
        }

        if (sync_0 != HEADER_BYTE_0)
        {
            continue;
        }

        if (rb_pop(b, &sync_1) != 0)
        {
            return false;
        }

        if (sync_1 != HEADER_BYTE_1)
        {
            continue;
        }

        if (sync_0 != HEADER_BYTE_0 && sync_1 != HEADER_BYTE_1)
        {
            return false;
        }

        if (rb_pop(b, &crc) != 0)
        {
            return false;
        }

        for (uint8_t i = 0; i < (uint8_t)RX_DATA_LENGTH; i++)
        {
            if (rb_pop(b, payload_out + i) != 0)
            {
                debugprintf("pop fail\n");
                return false;
            }  
        }


#define CRC_CHECK
#ifdef CRC_CHECK
        if (crc8_calculate(payload_out, RX_DATA_LENGTH) != crc)
        {
            // debugprintf("bad crc\n");
            return false;
        }
#endif

        return true;
    }
    

    return false;

}

void get_uart_input_report_task()
{
    static uint8_t test_buf[RX_DATA_LENGTH];
    uint8_t* ptr = (uint8_t*)&test_buf;

    if (get_payload(&rx_buffer, ptr)) {
        unpack_buffer_to_g29(ptr,&report);
    }
}

void flush_tx_ffb_packet_out()
{
    if (tx_buffer.size >= TX_FFB_DATA_LENGTH + sizeof(header_t))
    {
        if (uart_is_writable(uart0))
        {
            uint8_t temp;
            rb_pop(&tx_buffer, &temp);
            uart_putc_raw(uart0, temp);
        }
    }
}

void report_init() {
    memset(&report, 0, sizeof(report));
    report.lx = 0x80;
    report.ly = 0x80;
    report.rx = 0x80;
    report.ry = 0x80;
    report.clutch = 0xFFFF;
    memcpy(&prev_report, &report, sizeof(report));
}

void hid_task() {
    if (!tud_hid_ready()) {
        // debugprintf("Console not connected\n");
        return;
    }

    if (memcmp(&prev_report, &report, sizeof(report))) {
        tud_hid_report(1, &report, sizeof(report));
        memcpy(&prev_report, &report, sizeof(report));
    }

    if (memcmp(prev_ff_buf, ff_buf, sizeof(ff_buf))) {
        if (wheel_device) {
            tuh_hid_send_report(wheel_device, wheel_instance, 0, ff_buf, sizeof(ff_buf));
        }
        pusb_ffb_packet_to_tx_buffer(&tx_buffer, (uint8_t*)&ff_buf, sizeof(ff_buf));
        memcpy(prev_ff_buf, ff_buf, sizeof(ff_buf));
    }
}

void wheel_init_task() {

    if (wheel_device && !initialized) {
        initialized = true;
        static uint8_t buf[] = { 0xf5, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00 };  // disable autocenter
        tuh_hid_send_report(wheel_device, wheel_instance, 0, buf, sizeof(buf));
    }
}

void auth_task() {
    if (!busy && auth_device) {
        switch (state) {
            case IDLE:
                break;
            case SENDING_RESET:
                tuh_hid_get_report(auth_device, auth_instance, 0xF3, HID_REPORT_TYPE_FEATURE, get_buffer, 7 + 1);
                busy = true;
                break;
            case SENDING_NONCE:
                set_buffer[0] = 0xF0;
                set_buffer[1] = nonce_id;
                set_buffer[2] = nonce_part;
                set_buffer[3] = 0;
                memcpy(set_buffer + 4, nonce + (nonce_part * 56), 56);
                debugprintf(".");
                tuh_hid_set_report(auth_device, auth_instance, 0xF0, HID_REPORT_TYPE_FEATURE, set_buffer, 64);
                busy = true;
                nonce_part++;
                break;
            case WAITING_FOR_SIG:
                tuh_hid_get_report(auth_device, auth_instance, 0xF2, HID_REPORT_TYPE_FEATURE, get_buffer, 15 + 1);
                busy = true;
                break;
            case RECEIVING_SIG:
                tuh_hid_get_report(auth_device, auth_instance, 0xF1, HID_REPORT_TYPE_FEATURE, get_buffer, 63 + 1);
                busy = true;
                break;
        }
    }
}



void tuh_hid_get_report_complete_cb(uint8_t dev_addr, uint8_t idx, uint8_t report_id, uint8_t report_type, uint16_t len) {
    if (dev_addr == auth_device) {
        busy = false;
        switch (report_id) {
            case 0xF3:
                debugprintf("Sending nonce to auth controller");
                state = SENDING_NONCE;
                break;
            case 0xF2:
                // debugprintf(".");
                if (get_buffer[2] == 0) {
                    signature_part = 0;
                    state = RECEIVING_SIG;
                    debugprintf("\n");
                    debugprintf("Receiving signature from auth controller");
                }
                break;
            case 0xF1:
                memcpy(signature + (signature_part * 56), get_buffer + 4, 56);
                signature_part++;
                debugprintf(".");
                if (signature_part == 19) {
                    state = IDLE;
                    expected_part = 0;
                    signature_ready = true;
                    signature_part = 0;
                    debugprintf("\n");
                }
                break;
        }
    }
}

void tuh_hid_set_report_complete_cb(uint8_t dev_addr, uint8_t idx, uint8_t report_id, uint8_t report_type, uint16_t len) {
    if ((dev_addr == auth_device) && (report_id == 0xF0)) {
        busy = false;
        if (nonce_part == 5) {
            debugprintf("\n");
            debugprintf("Waiting for auth controller to sign...\n");
            state = WAITING_FOR_SIG;
        }
    }
}

uint16_t tud_hid_get_report_cb(uint8_t itf, uint8_t report_id, hid_report_type_t report_type, uint8_t* buffer, uint16_t reqlen) {
    switch (report_id) {
        case 0x03:
            memcpy(buffer, output_0x03, reqlen);
            board_led_write(false);
            return reqlen;
        case 0xF3:
            memcpy(buffer, output_0xf3, reqlen);
            signature_ready = false;
            return reqlen;
        case 0xF1: {  // GET_SIGNATURE_NONCE
            buffer[0] = nonce_id;
            buffer[1] = signature_part;
            buffer[2] = 0;
            if (signature_part == 0) {
                debugprintf("Sending signature to PS5");
            }
            debugprintf(".");
            memcpy(&buffer[3], &signature[signature_part * 56], 56);
            signature_part++;
            if (signature_part == 19) {
                signature_part = 0;
                debugprintf("\n");
                board_led_write(true);
            }
            return reqlen;
        }
        case 0xF2: {  // GET_SIGNING_STATE
            debugprintf("PS5 asks if signature ready (%s).\n", signature_ready ? "yes" : "no");
            buffer[0] = nonce_id;
            buffer[1] = signature_ready ? 0 : 16;
            memset(&buffer[2], 0, 9);
            return reqlen;
        }
    }
    return reqlen;
}

void tud_hid_set_report_cb(uint8_t itf, uint8_t report_id, hid_report_type_t report_type, uint8_t const* buffer, uint16_t bufsize) {
    if (report_id == 0xF0) {  // SET_AUTH_PAYLOAD
        uint8_t part = expected_part;
        if (bufsize == 63) {
            nonce_id = buffer[0];
            part = buffer[1];
        }
        if (part == 0) {
            debugprintf("Getting nonce from PS5");
        }
        debugprintf(".");
        if (part > 4) {
            return;
        }
        expected_part = part + 1;
        memcpy(&nonce[part * 56], &buffer[3], 56);
        if (part == 4) {
            nonce_ready = 1;
            debugprintf("\n");
            debugprintf("Sending reset to auth controller...\n");
            state = SENDING_RESET;
            nonce_part = 0;
        }
    } else {
        if (bufsize > sizeof(ff_buf)) {
            // pass everything through to the wheel
            memcpy(ff_buf, buffer + 1, sizeof(ff_buf));
        }
    }
}

void tuh_hid_mount_cb(uint8_t dev_addr, uint8_t instance, uint8_t const* desc_report, uint16_t desc_len) {
    uint16_t vid;
    uint16_t pid;
    if (!tuh_vid_pid_get(dev_addr, &vid, &pid))
    {
        debugprintf("failed to pid/vid get for %d %d\n", dev_addr, instance);
        return;
    }
    debugprintf("tuh_hid_mount_cb %04x:%04x %d %d\n", vid, pid, dev_addr, instance);

    if ((vid == 0x046d) && (pid == 0xc294)) {  // Driving Force (or another wheel in compatibility mode)
        wheel_device = dev_addr;
        wheel_instance = instance;
        tuh_hid_receive_report(dev_addr, instance);
        initialized = false;
    } else {  // assume everything else is the controller we use for authentication
        auth_device = dev_addr;
        auth_instance = instance;
    }
}

void tuh_hid_umount_cb(uint8_t dev_addr, uint8_t instance) {
    debugprintf("tuh_hid_umount_cb\n");
    if (dev_addr == wheel_device) {
        wheel_device = 0;
        wheel_instance = 0;
    }
    if (dev_addr == auth_device) {
        auth_device = 0;
        auth_instance = 0;
    }
}

void tuh_hid_report_received_cb(uint8_t dev_addr, uint8_t instance, uint8_t const* report_, uint16_t len) {
    if (len > 0) {
        if (dev_addr == wheel_device) {
            df_report_t* df = (df_report_t*) report_;
            report.wheel = df->wheel << 6;
            report.throttle = df->throttle << 8;
            report.brake = df->brake << 8;
            report.dpad = df->hat;
            report.cross = df->cross;
            report.square = df->square;
            report.circle = df->circle;
            report.triangle = df->triangle;
            report.L2 = df->L2;
            report.L1 = df->L1;
            report.R2 = df->R2;
            report.R1 = df->R1;
            report.select = df->select;
            report.start = df->start;
            report.R3 = df->R3;
            report.L3 = df->L3;
        }
    }

    tuh_hid_receive_report(dev_addr, instance);
}

int main() {
    board_init();
    report_init();
    tusb_init();
    stdio_init_all();

    memset(&rx_buffer, 0, sizeof(buffer_t));
    memset(&tx_buffer, 0, sizeof(buffer_t));

    // Uart needs to be setup last
    setup_uart();

    while (1) {
        tuh_task();
        tud_task();

        get_uart_input_report_task();
        hid_task();
        flush_tx_ffb_packet_out();
        auth_task();
        wheel_init_task();
    }

    return 0;
}