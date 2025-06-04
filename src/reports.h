#ifndef _REPORTS_H_
#define _REPORTS_H_

#include <stdint.h>

// G29 HID report
typedef struct __attribute__((packed)) {
    uint8_t lx;
    uint8_t ly;
    uint8_t rx;
    uint8_t ry;
    // 4 Bytes
    uint8_t dpad : 4;
    uint8_t square : 1;
    uint8_t cross : 1;
    uint8_t circle : 1;
    uint8_t triangle : 1;
    // 5
    uint8_t L1 : 1;
    uint8_t R1 : 1;
    uint8_t L2 : 1;
    uint8_t R2 : 1;
    uint8_t select : 1;
    uint8_t start : 1;
    uint8_t L3 : 1;
    uint8_t R3 : 1;
    // 6
    uint8_t PS : 1;
    uint8_t touchpad : 1;
    uint8_t counter : 6;
    // 7
    uint8_t reserved[35];
    
    uint16_t wheel;
    uint16_t throttle;
    uint16_t brake;
    uint16_t clutch;
    // 8
    uint8_t gear1 : 1;
    uint8_t gear2 : 1;
    uint8_t gear3 : 1;
    uint8_t gear4 : 1;
    uint8_t gear5 : 1;
    uint8_t gear6 : 1;
    uint8_t gear7 : 1;
    uint8_t gearR : 1;
    // 9
    uint16_t reserved2;
    uint8_t enter : 1;
    uint8_t minus : 1;
    uint8_t plus :  1;
    uint8_t dual_ccw : 1;
    uint8_t dial_cw : 1;

    uint8_t reserved3[9];
} g29_report_t;

// Driving Force HID report
typedef struct __attribute__((packed)) {
    uint32_t wheel : 10;
    uint32_t cross : 1;
    uint32_t square : 1;
    uint32_t circle : 1;
    uint32_t triangle : 1;
    uint32_t R1 : 1;
    uint32_t L1 : 1;
    uint32_t R2 : 1;
    uint32_t L2 : 1;
    uint32_t select : 1;
    uint32_t start : 1;
    uint32_t R3 : 1;
    uint32_t L3 : 1;
    uint32_t whatever : 2;
    uint8_t y;
    uint32_t hat : 4;
    uint32_t whatever2 : 4;
    uint8_t throttle;
    uint8_t brake;
} df_report_t;

#endif
