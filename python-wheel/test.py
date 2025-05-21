import serial
from g29report import G29Report
import time
import random

if __name__ == "__main__":

    ser = serial.Serial('/dev/ttyUSB0',baudrate=921600)  # open serial port
    print(ser.name)         # check which port was really used

    report = G29Report()
    boole = True

    while (1):
        SYNC = bytearray([0xA1, 0x36])

        # Reverse byte order
        # SYNC = bytearray([0xCC, 0xF0])
        # PAYLOAD = bytearray([0x0,0x1, 0x2, 0x3, 0x4,0x5, 0x6, 0x7, 0x8,0x9, 0xa, 0xb, 0xc,0xd, 0xe, 0xf])


        # packet = SYNC + PAYLOAD
        # i += ser.write(packet)
        # print(i)
        # break

        # report.lx = random.randint(0, 255)
        # report.ly = random.randint(0, 255)
        # report.rx = random.randint(0, 255)
        # report.ry = random.randint(0, 255)
        # report.wheel = random.randint(0, 1<<15)
        # report.throttle = random.randint(0, 1<<15)
        # report.brake = random.randint(0, 1<<15)
        report.clutch = 0xABCD
        report.touchpad = boole
        # report.dpad = boole
        boole = not boole

        print("{",end="")
        for x in report.pack():
            print(f"{x},",end="")
        print("};")

        packed = report.pack()
        packed = SYNC + packed
        print(packed)
        x = ser.write(packed)
        print(x)
        # break
        time.sleep(0.5)

    ser.close()             # close port
