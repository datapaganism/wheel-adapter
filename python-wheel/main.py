#!.venv/bin/python3

import threading
import serial
import hid
import time
from controllers.GameControllerInput import GameControllerInput
from controllers.Wheel import WheelController, OFFB_CMD, OFFB_FORCE_TYPE
from controllers.ProController import *
from controllers.ShifterController import *
from controllers.PedalsController import *
from controllers.DrivingForceButtons import *
from utils import *
from g29report import G29Report

"""
TODO
Implement all other ffb types (spring, stop etc)
Fix and improve the variable command
Multiple inputs are crashing,
  File "hid.pyx", line 235, in hid.device.read
OSError: read error
Code cleanup
Test higher baud rates
"""

SYNC = bytearray([0xA1, 0x36])

PRINT_ALL_UART_MSG = True
BAUDRATE = 115200
# BAUDRATE = 921600
REPORT_OUT_RATE_HZ = 400
REPORT_DATA_LEN = G29Report.size()
REPORT_HEADER_LEN = len(SYNC)

UART_DATA_BITS = 8
UART_STOP_BITS = 1
UART_PARITY = "N"

uart_saturation_pc = (((UART_DATA_BITS + UART_STOP_BITS)  * ( REPORT_HEADER_LEN + REPORT_DATA_LEN) * REPORT_OUT_RATE_HZ ) / BAUDRATE) * 100



# Check if we need
pos = 0
rot_deg = 0
report_prev = None
effects = []



def read_uart_thread(inputQueue, ser, stop_event):
    while not stop_event.is_set():
        if ser.inWaiting() > 0:
            x = ser.read(ser.inWaiting())
            # Print anything that isn't a FFB packet
            if x[0] != 0x36 and PRINT_ALL_UART_MSG:
                print(x)
                pass
            inputQueue.put(x)
        # time.sleep(0.01)
    print("closing serial")
    ser.close()


def send_g29_report(ser, controllers):
    global report_prev

    # Merge all byte arrays
    final = bytearray([0]) * REPORT_DATA_LEN
    for controller in controllers:
        if not controller.connected:
            continue

        temp = controller.get_g29report()
        for i, val in enumerate(list(temp)):
            if val != 0:
                final[i] |= val

    if final == report_prev:
        return
    
    # print(final)

    report_prev = final
    final = SYNC + final
    x = ser.write(final)


def main():
    print(f"Serial Max saturation is {uart_saturation_pc}%")

    stop_event = threading.Event()
    ser = serial.Serial(
        "/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0",
        baudrate=BAUDRATE, bytesize=UART_DATA_BITS, stopbits=UART_STOP_BITS, parity=UART_PARITY
    )

    # Place in order of priority, higher index takes priority
    controllers: GameControllerInput = [
        WheelController(),
        PedalsController(),
        ProController(),
        DrivingForceButtons(),
        Shifter(),
    ]
    threads = []

    for control in controllers:
        thread = threading.Thread(
            target=control.thread_job,
            args=(stop_event,),
            daemon=False,
            name=control.product_string,
        )
        thread.start()
        threads.append(thread)

    ffboard_device = None
    for controller in controllers:
        if controller.product_string == "Wheel":
            ffboard_device = controller
            break

    if ffboard_device is not None:
        read_uart_ffb_thread = threading.Thread(
            target=read_uart_thread, args=(ffboard_device.rx_uart_queue, ser, stop_event), daemon=False
        )
        read_uart_ffb_thread.start()

    try:
        while not stop_event.is_set():
            send_g29_report(ser,controllers)
            time.sleep(1/REPORT_OUT_RATE_HZ)

    except KeyboardInterrupt:
        print("Bye")
        stop_event.set()
    except Exception as e:
        print(e)
        print("Main loop exception")
        raise

    stop_event.set()
    print("Good Bye for real")


if __name__ == "__main__":
    main()
