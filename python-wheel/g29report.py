import struct
import ctypes



class G29Report(ctypes.LittleEndianStructure):
    _pack_ = 1  # Ensure the structure is packed
    _fields_ = [
        ("lx", ctypes.c_uint8),
        ("ly", ctypes.c_uint8),
        ("rx", ctypes.c_uint8),
        ("ry", ctypes.c_uint8),
        # 4 bytes
        ("dpad", ctypes.c_uint8, 4),
        ("square", ctypes.c_uint8, 1),
        ("cross", ctypes.c_uint8, 1),
        ("circle", ctypes.c_uint8, 1),
        ("triangle", ctypes.c_uint8, 1),
        # 1 Byte
        ("L1Paddle", ctypes.c_uint8, 1),
        ("R1Paddle", ctypes.c_uint8, 1),
        ("L2", ctypes.c_uint8, 1),
        ("R2", ctypes.c_uint8, 1),
        ("selectShare", ctypes.c_uint8, 1),
        ("startOptions", ctypes.c_uint8, 1),
        ("L3", ctypes.c_uint8, 1),
        ("R3", ctypes.c_uint8, 1),
        # 1 Byte
        ("PS", ctypes.c_uint8, 1),
        ("touchpad", ctypes.c_uint8, 1),
        ("counter", ctypes.c_uint8, 6),
        # ("reserved2", ctypes.c_uint8 * 35),  # Array of 35 bytes
        ("wheel", ctypes.c_uint16),
        ("throttle", ctypes.c_uint16),
        ("brake", ctypes.c_uint16),
        ("clutch", ctypes.c_uint16),
        ("gear1", ctypes.c_uint8, 1),
        ("gear2", ctypes.c_uint8, 1),
        ("gear3", ctypes.c_uint8, 1),
        ("gear4", ctypes.c_uint8, 1),
        ("gear5", ctypes.c_uint8, 1),
        ("gear6", ctypes.c_uint8, 1),
        ("gear7", ctypes.c_uint8, 1),
        ("gearR", ctypes.c_uint8, 1),
        # ("reserved2", ctypes.c_uint16),
        ("enter", ctypes.c_uint8, 1),
        ("minus", ctypes.c_uint8, 1),
        ("plus", ctypes.c_uint8, 1),
        ("dial_ccw", ctypes.c_uint8, 1),
        ("dial_cw", ctypes.c_uint8, 1),
        # ("reserved3", ctypes.c_uint8 * 9)  # Array of 13 bytes
    ]


    def get(self):
        report = G29Report()
        report.lx = 128
        report.ly = 128
        report.rx = 128
        report.ry = 128
        report.brake = 0xFFFF
        report.throttle = 0xFFFF
        report.clutch = 0xFFFF
        return report


    def pack(self):
        return bytes(self)
    
    @classmethod
    def size(cls):
        temp = G29Report()
        temp = temp.get()
        temp = temp.pack()
        temp = list(temp)
        temp = len(temp)
        return temp

if __name__ == "__main__":
    report = G29Report()
    report.lx = 255
    report.ly = 128
    report.rx = 128
    report.ry = 128
    report.dpad = 1
    report.square = 1
    report.cross = 0
    report.circle = 0
    report.triangle = 0
    report.L1Paddle = 0
    report.R1Paddle = 0
    report.L2 = 0
    report.R2 = 0
    report.selectShare = 0
    report.startOptions = 0
    report.L3 = 0
    report.R3 = 0
    report.PS = 0
    report.touchpad = 0
    report.counter = 0
    report.wheel = 0
    report.throttle = 0
    report.brake = 0
    report.clutch = 0

    packed_data = bytes(report)

    print(packed_data)
    
    if __name__ == "__main__":
        print(G29Report.size())