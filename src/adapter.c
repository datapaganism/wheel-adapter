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

#include "pico/stdlib.h"
#include "hardware/uart.h"
#include "hardware/irq.h"





void dump_g29_report(g29_report_t* report)
{
    printf("ry     is 0x%x\n", report->ry);
    printf("wheel  is 0x%x\n", report->wheel);
    printf("clutch is 0x%x\n", report->clutch);
}


void unpack_buffer_to_g29(uint8_t* buffer, g29_report_t* report)
{
    uint8_t* b = buffer;
    uint8_t* r = (uint8_t*)report;

    memcpy(r,b, 8);
    b += 8;
    r += (8 + 34);
    memcpy(r,b, 8);
    // dump_g29_report(report);
}

buffer_t rx_buffer;
buffer_t tx_buffer;

int UART_IRQ = UART_ID == uart0 ? UART0_IRQ : UART1_IRQ;

uint8_t* com1Tx_buf = (uint8_t*)&tx_buffer.buffer;											// pointer to the buffer for transmitted characters
volatile int com1Tx_head, com1Tx_tail;	

void on_uart_irq0() {
    if(uart_is_readable(uart0)) {
        uint8_t byte_got = uart_getc(uart0);
        rb_push(&rx_buffer, byte_got);
    }
    // if(uart_is_writable(uart0)){
	// 	if(com1Tx_head != com1Tx_tail) {
	// 		uart_putc_raw(uart0,com1Tx_buf[com1Tx_tail]);
	// 		com1Tx_tail = (com1Tx_tail + 1) % sizeof(tx_buffer.buffer);       // advance the tail of the queue
	// 	} else {
	// 		uart_set_irq_enables(uart0, true, false);
	// 	}
    // }

    // irq_set_enabled(UART_IRQ, true);
}

void setupuart(){
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

    uart_puts(UART_ID, "\nHello, its a me, uart\n");

}


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
uint8_t ff_buf[] = { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00 };
uint8_t prev_ff_buf[] = { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00 };

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


bool get_payload(buffer_t *ptr, uint8_t *payload_out)
{
    if (ptr->size >= PACKET_LEN)
    {
        uint8_t sync_0;
        uint8_t sync_1;

        if (rb_pop(ptr, &sync_0) != 0)
        {
            return false;
        }

        if (rb_pop(ptr, &sync_1) != 0)
        {
            return false;
        }

        if (sync_0 == HEADER_BYTE_1 && sync_1 == HEADER_BYTE_2)
        {
            // printf("\n");

            // Valid header found, copy payload
            for (uint8_t i = 0; i < (uint8_t)MESSAGE_LEN; i++)
            {
                if (rb_pop(ptr, payload_out + i) != 0)
                {
                    printf("pop fail\n");
                    return false;
                }
                // printf("%i ", *(payload_out + i));

            }
                // printf("\n");

            return true;
        }
        else
        {
            printf("BAD H\n");
            rb_pop(ptr, NULL);
        }
    }

    return false;

}

void uart_task()
{

    static uint8_t test_buf[MESSAGE_LEN];
    uint8_t* ptr = (uint8_t*)&test_buf;

    if (get_payload(&rx_buffer, ptr)) {
        unpack_buffer_to_g29(ptr,&report);

        if (report.PS == true)
        {
            printf("PS is 0x%x\n", report.PS);
        }

        // if (report.cross == true)
        // {
        //     printf("cross is 0x%x\n", report.cross);
        // }

            // Process payload
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
                printf(".");
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

int main() {
    board_init();
    report_init();
    tusb_init();
    stdio_init_all();

    memset(&rx_buffer, 0, sizeof(buffer_t));
    memset(&tx_buffer, 0, sizeof(buffer_t));

    setupuart();

    while (1) {
        tuh_task();
        tud_task();
        uart_task();
        hid_task();
        auth_task();
        wheel_init_task();
    }

    return 0;
}

void tuh_hid_get_report_complete_cb(uint8_t dev_addr, uint8_t idx, uint8_t report_id, uint8_t report_type, uint16_t len) {
    if (dev_addr == auth_device) {
        busy = false;
        switch (report_id) {
            case 0xF3:
                printf("Sending nonce to auth controller");
                state = SENDING_NONCE;
                break;
            case 0xF2:
                // printf(".");
                if (get_buffer[2] == 0) {
                    signature_part = 0;
                    state = RECEIVING_SIG;
                    printf("\n");
                    printf("Receiving signature from auth controller");
                }
                break;
            case 0xF1:
                memcpy(signature + (signature_part * 56), get_buffer + 4, 56);
                signature_part++;
                printf(".");
                if (signature_part == 19) {
                    state = IDLE;
                    expected_part = 0;
                    signature_ready = true;
                    signature_part = 0;
                    printf("\n");
                }
                break;
        }
    }
}

void tuh_hid_set_report_complete_cb(uint8_t dev_addr, uint8_t idx, uint8_t report_id, uint8_t report_type, uint16_t len) {
    if ((dev_addr == auth_device) && (report_id == 0xF0)) {
        busy = false;
        if (nonce_part == 5) {
            printf("\n");
            printf("Waiting for auth controller to sign...\n");
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
                printf("Sending signature to PS5");
            }
            printf(".");
            memcpy(&buffer[3], &signature[signature_part * 56], 56);
            signature_part++;
            if (signature_part == 19) {
                signature_part = 0;
                printf("\n");
                board_led_write(true);
            }
            return reqlen;
        }
        case 0xF2: {  // GET_SIGNING_STATE
            printf("PS5 asks if signature ready (%s).\n", signature_ready ? "yes" : "no");
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
            printf("Getting nonce from PS5");
        }
        printf(".");
        if (part > 4) {
            return;
        }
        expected_part = part + 1;
        memcpy(&nonce[part * 56], &buffer[3], 56);
        if (part == 4) {
            nonce_ready = 1;
            printf("\n");
            printf("Sending reset to auth controller...\n");
            state = SENDING_RESET;
            nonce_part = 0;
        }
    } else {
        if (bufsize > sizeof(ff_buf)) {
            // printf("Got FFB packet\n");
            // pass everything through to the wheel
            memcpy(ff_buf, buffer + 1, sizeof(ff_buf));
        }
    }
}

void tuh_hid_mount_cb(uint8_t dev_addr, uint8_t instance, uint8_t const* desc_report, uint16_t desc_len) {
    uint16_t vid;
    uint16_t pid;
    tuh_vid_pid_get(dev_addr, &vid, &pid);

    printf("tuh_hid_mount_cb %04x:%04x %d %d\n", vid, pid, dev_addr, instance);

    // initialized = false;

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
    printf("tuh_hid_umount_cb\n");
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
