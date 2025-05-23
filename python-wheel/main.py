import threading
import queue
import serial
from g29report import G29Report
from openffboard import OpenFFBoard
import hid
import time

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
BAUDRATE = 921600
BAUDRATE = 115200

FX_MANAGER = 0xA03
AXIS = 0xA01
AXIS_POS_COMMAND = 0xE
AXIS_ROTATION_COMMAND = 0x1

MASTER_SCALE = 0.5
#                  161    54
SYNC = bytearray([0xA1, 0x36])

pos = 0
rot_deg = 0
report_prev = None
effects = []
ser = serial.Serial(
    "/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0",
    baudrate=BAUDRATE,
)
report = G29Report().get()


class GameControllerInput:
    running = True
    connected = False
    hid_device = None
    buttons = []
    axes = []
    vid = 0
    pid = 0

    button_index_start = 0
    button_index_len = 0
    axes_index_start = 0
    axes_index_len = 0

    def process_inputs(self, report):
        pass

    def __init__(self):
        try:
            self.hid_device = hid.device()
            self.hid_device.open(self.vid, self.pid)
            self.connected = True
        except:
            print("Not connected")
        pass

    def close(self):
        self.hid_device.close()

    def __repr__(self):
        return f"Buttons: {self.buttons}, Axes: {self.axes}"

    def get_buttons(self):
        return self.buttons

    def get_axis(self):
        return self.axes

    def stop(self):
        self.running = False

    def decode(self, report, signed=False):

        # for x in report:
        #     hex_padded = f"{x:02x}"  ## Format specifier for 2-digit hex
        #     print(f"{hex_padded}, ", end="")

        #     # print(f"{y:04x},",end="")
        # print("\n")

        if self.button_index_start != -1 and self.button_index_len != -1:

            raw_buttons = report[
                self.button_index_start : self.button_index_start
                + self.button_index_len
            ]

            # Convert button states from bytes to a list of booleans
            self.buttons = [
                (raw_buttons[i // 8] & (1 << (i % 8))) != 0
                for i in range(len(raw_buttons) * 8)
            ]

        if self.axes_index_start != -1 and self.axes_index_len != -1:
            raw_axes = report[
                self.axes_index_start : self.axes_index_start + self.axes_index_len
            ]
            # print(raw_axes)

            # Convert axis values (assuming they are 16-bit signed integers)
            AXIS_WIDTH = 2  # 16bit
            self.axes = [
                int.from_bytes(
                    raw_axes[i : i + AXIS_WIDTH], byteorder="little", signed=signed
                )
                for i in range(0, len(raw_axes), AXIS_WIDTH)
            ]
            # for x in self.axes:
            #     x &= (1 < 10)
            # print(self.axes)


class ProController(GameControllerInput):
    vid = 0x057E
    pid = 0x2009
    button_index_start = 3
    button_index_len = 3
    axes_index_start = 7
    axes_index_len = 4

    def process_inputs(self, report):
        if not self.connected:
            return

        device_hid_report = self.hid_device.read(64)  # Read 64 bytes
        if device_hid_report:
            self.decode(device_hid_report)
            buttons = self.get_buttons()

            report.cross = buttons[2]
            report.circle = buttons[3]
            report.triangle = buttons[1]
            report.square = buttons[0]

            report.PS = buttons[12]
            report.start = buttons[9]
            throt = buttons[7]
            brake = buttons[23]

            # if (report.throttle )
            # report.throttle = int(num_to_range(throt, 0, 1, 0xFFFF, 0))
            
            # report.brake = int(num_to_range(brake, 0, 1, 0xFFFF, 0))

            dpad = buttons[16 : 16 + 4]
            ddown = dpad[0]
            dup = dpad[1]
            dleft = dpad[3]
            dright = dpad[2]
            final = 0b1000
            if dup:
                final = 0b0000
            if ddown:
                final = 0b0100
            if dleft:
                final = 0b0110
            if dright:
                final = 0b0010
            report.dpad = final


class PedalsController(GameControllerInput):
    vid = 0x1209
    pid = 0xA136
    button_index_start = -1
    button_index_len = -1
    axes_index_start = 5
    axes_index_len = 2 * 6  # 6 16bit axes

    def process_inputs(self, report):
        if not self.connected:
            print("Not connected")
            return

        device_hid_report = self.hid_device.read(64)  # Read 64 bytes
        if device_hid_report:
            self.decode(device_hid_report, signed=True)
            axes = self.get_axis()

            throt = axes[0]
            brake = axes[1]
            clutch = axes[2]
            report.throttle = int(num_to_range(throt, -(1 << 15), (1 << 15), 0xFFFF, 0))
            report.brake = int(num_to_range(brake, -(1 << 15), (1 << 15), 0xFFFF, 0))
            # report.clutch = int(num_to_range(clutch, -(1 << 15), (1 << 15), 0xFFFF, 0))
            


def read_uart_thread(inputQueue):
    while True:
        if ser.inWaiting() > 0:
            x = ser.read(ser.inWaiting())
            inputQueue.put(x)
        time.sleep(0.01)


def read_controller_thread(device: GameControllerInput, report):
    while device.running:
        device.process_inputs(report)
        time.sleep(0.01)


def getSignedNumber(number, bitLength):
    mask = (2**bitLength) - 1
    if number & (1 << (bitLength - 1)):
        return number | ~mask
    else:
        return number & mask


def parse_ffb_packet(inputQueue, ffboard):
    g29_ffb_packet = None
    if inputQueue.qsize() > 0:
        input_str = inputQueue.get()
        if len(input_str) == 9:
            # This is weird, the header is split but the FFB packet inside look good to me
            if input_str[0] == SYNC[1] and input_str[8] == SYNC[0]:
                g29_ffb_packet = input_str[1:-1]
                # for x in input_str:
                #     print(f"{hex(x)},",end="")
                # print("\n")

    if g29_ffb_packet != None:
        cmd = g29_ffb_packet[0] & 0b00001111
        force_slot = (g29_ffb_packet[0] & 0b11110000) >> 4

        if cmd == 0x1:  # Download and Play Force
            force_type = g29_ffb_packet[1]
            if force_type == 0x8:  # Variable

                # L1 and L2 look signed to me
                L1 = g29_ffb_packet[2]
                L2 = g29_ffb_packet[3]
                T1 = (g29_ffb_packet[4] & 0b11110000) >> 4
                S1 = g29_ffb_packet[4] & 0b00001111
                T2 = (g29_ffb_packet[5] & 0b11110000) >> 4
                S2 = g29_ffb_packet[5] & 0b00001111
                D1 = g29_ffb_packet[6] & 0b00000001
                D2 = g29_ffb_packet[6] & 0b00010000
                L1 = getSignedNumber(L1, 8)

                ffboard.writeData(
                    FX_MANAGER,
                    0,
                    0x4,
                    data=int(((L1 * 50) * MASTER_SCALE)),
                    adr=effects[0],
                )  # Set constant foce magnitude
        elif cmd == 0x3:  # Stop Force
            pass
            #  ffboard.writeData(
            #         FX_MANAGER, 0, 0x1, data=0, adr=effects[0]
            #     )
        elif cmd == 0x8 and force_slot == 0b1111:
            print("extended command mode")
            ext_cmd = g29_ffb_packet[1]
            match ext_cmd:
                case 0x1:
                    print("EXT Change Mode to Driving Force Pro")
                case 0x2:
                    print("EXT Change Wheel Range to 200 Degrees")
                    ffboard.writeData(
                        AXIS, 0, cmd=AXIS_ROTATION_COMMAND, data=200
                    )

                case 0x3:
                    print("EXT Change Wheel Range to 900 Degrees")
                    ffboard.writeData(
                        AXIS, 0, cmd=AXIS_ROTATION_COMMAND, data=900
                    )

                case 0x9:
                    print("EXT Change Device Mode")
                case 0x0A:
                    print("EXT Revert Identity")
                case 0x10:
                    print("EXT Switch to G25 Identity with USB Detach")
                case 0x11:
                    print("EXT Switch to G25 Identity without USB Detach")
                case 0x12:
                    print("EXT Set RPM LEDs")
                case 0x81:
                    print("EXT Wheel Range Change")
                    target_range = (g29_ffb_packet[3] << 8) | g29_ffb_packet[2]
                    target_range = clamp(target_range, 40, 900)
                    ffboard.writeData(
                        AXIS, 0, cmd=AXIS_ROTATION_COMMAND, data=target_range
                    )

        else:
            print(f"cmd {hex(cmd)} fX {hex(force_slot)}")
            for x in g29_ffb_packet:
                print(f"{hex(x)},", end="")
            print("\n")

        # for x in g29_ffb_packet:
        #     print(f"{hex(x)},",end="")
        # print("\n")


def send_g29_report():
    global report_prev
    packed = report.pack()
    if packed == report_prev:
        return

    report_prev = packed
    packed = SYNC + packed
    x = ser.write(packed)


def num_to_range(num, inMin, inMax, outMin, outMax):
    return outMin + (float(num - inMin) / float(inMax - inMin) * (outMax - outMin))


def readDataCB(cmdtype, cls, inst, cmd, val, addr):
    if cls == FX_MANAGER and cmd == 2:
        effects.append(val)
        print("Got new effect at index", val)

    if cls == AXIS and cmd == AXIS_POS_COMMAND:
        global pos
        pos = val

    if cls == AXIS and cmd == AXIS_ROTATION_COMMAND:
        global rot_deg
        rot_deg = val

    # print(f"Type: {cmdtype}, Class: {cls}.{inst}: cmd: {cmd}, val: {val}, addr: {addr}")


# ffboard_device.readData(AXIS,0,cmd=AXIS_ROTATION_COMMAND)
# ffboard_device.writeData(AXIS,0,cmd=AXIS_ROTATION_COMMAND,data=360)


def clamp(value, min, max):
    if value > max:
        value = max

    if value < min:
        value = min

    return value


def main():

    pedals = PedalsController()
    pro = ProController()

    ffboard_device = OpenFFBoard(OpenFFBoard.findDevices()[0])
    ffboard_device.open()
    ffboard_device.registerReadCallback(readDataCB)

    ffboard_device.readData(FX_MANAGER, 0, 1)  # Reset FFB
    # effects = [] # When reset all effects are reset

    ffboard_device.writeData(FX_MANAGER, 0, 0, 1)  # Enable FFB

    ffboard_device.writeData(FX_MANAGER, 0, 2, 1)  # Make new constant force (1) effect
    print(effects)  # We should have a new effect now
    ffboard_device.writeData(
        FX_MANAGER, 0, 0x5, data=1, adr=effects[0]
    )  #  Enable effect

    # dev.writeData(FX_MANAGER,0,0x4,data=4000,adr=effects[0]) # Set constant foce magnitude
    # time.sleep(1)
    # dev.writeData(FX_MANAGER,0,0x4,data=-2000,adr=effects[0]) # Set constant foce magnitude
    # time.sleep(1)
    # dev.writeData(FX_MANAGER,0,0x4,data=0,adr=effects[0]) # Set constant foce magnitude 0
    # time.sleep(5)
    # exit(0)

    rx_uart_queue = queue.Queue()
    read_uart_ffb_thread = threading.Thread(
        target=read_uart_thread, args=(rx_uart_queue,), daemon=True
    )

    read_pro_controller_thread = threading.Thread(
        target=read_controller_thread, args=(pro, report), daemon=True
    )
    read_pedal_controller_thread = threading.Thread(
        target=read_controller_thread, args=(pedals, report), daemon=True
    )

    read_pro_controller_thread.start()
    read_pedal_controller_thread.start()
    read_uart_ffb_thread.start()

    ffboard_device.writeData(AXIS, 0, cmd=AXIS_ROTATION_COMMAND, data=900)

    try:
        while True:
            ffboard_device.readData(AXIS, 0, cmd=AXIS_ROTATION_COMMAND)
            ffboard_device.readData(AXIS, 0, cmd=AXIS_POS_COMMAND)  # read axis
            global pos
            pos = clamp(pos, -(1 << 15), (1 << 15))

            report.wheel = int(num_to_range(pos, -(1 << 15), (1 << 15), 0xFFFF, 0))

            parse_ffb_packet(rx_uart_queue, ffboard_device)

            send_g29_report()

            time.sleep(0.01)
    except KeyboardInterrupt:
        pass
    finally:
        ffboard_device.writeData(FX_MANAGER, 0, 0, 0)  # Disable FFB
        ffboard_device.close()
        pro.stop()
        pedals.stop()
        pro.close()
        pedals.close()


if __name__ == "__main__":
    main()
