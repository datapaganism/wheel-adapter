import threading
import serial
import hid
import time
from controllers.GameControllerInput import GameControllerInput 
from controllers.Wheel import WheelController, OFFB_CMD, OFFB_FORCE_TYPE
from controllers.ProController import *
from controllers.ShifterController import *
from controllers.PedalsController import*
from utils import *

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
BAUDRATE = 115200
BAUDRATE = 230400

FX_MANAGER = 0xA03
AXIS = 0xA01
AXIS_POS_COMMAND = 0xE
AXIS_ROTATION_COMMAND = 0x1

MASTER_SCALE = 1.0
#                  161    54
SYNC = bytearray([0xA1, 0x36])


# Check if we need
pos = 0
rot_deg = 0
report_prev = None
effects = []


def read_uart_thread(inputQueue, ser, stop_event):
    while not stop_event.is_set():
        if ser.inWaiting() > 0:
            x = ser.read(ser.inWaiting())
            inputQueue.put(x)
        # time.sleep(0.01)
    print("closing serial")
    ser.close()


def send_g29_report(ser, controllers):
    global report_prev

    # Merge all byte arrays    
    final = bytearray([0]) * 16    
    for controller in controllers:
        temp = controller.get_g29report()
        for i in range(len(temp)):
            final[i] |= temp[i]
    
    # if final == report_prev:
        # return

    report_prev = final
    final = SYNC + final
    x = ser.write(final)
    # print(x)


def main():

    stop_event = threading.Event()
    ser = serial.Serial(
        "/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0",
        baudrate=BAUDRATE,
    )

    controllers: GameControllerInput = [
        WheelController(),
        # PedalsController(),
        ProController(),
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
        # time.sleep(0.01)
        
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
            time.sleep(1/300)

    except KeyboardInterrupt:
        print("Bye")
        stop_event.set()
    except Exception as e:
        print(e)
        print("Main loop exception")
        raise

    stop_event.set()
    # ffboard_device.writeData(FX_MANAGER, 0, 0, 0)  # Disable FFB
    # ffboard_device.close()
    print("Good Bye for real")


if __name__ == "__main__":
    main()
