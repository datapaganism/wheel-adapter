from .GameControllerInput import GameControllerInput
from utils import *
import threading
import struct
import time
from enum import Enum
import queue
import math

"""
The G29 has 4 effects slots + 2 Spring effects
F0 F1 F2 F3 X Y

How it should work is that we track an array of of all the slots
When we get a FFB command, check if a slot is occupied, then check if they match by type, if not deactivate the effect on OFFB and remove it

Fire off OFFB commands to generate that type of FFB and then process as needed
The stop command would actually act on the correct place then

 
"""


class G29_FORCE_TYPE(Enum):
    Constant = 0x00
    Spring = 0x01
    Damper = 0x02
    Auto_Centering_Spring = 0x03
    Sawtooth_Up = 0x04
    Sawtooth_Down = 0x05
    Trapezoid = 0x06
    Rectangle = 0x07
    Variable = 0x08
    Ramp = 0x09
    Square_Wave = 0x0A
    High_Resolution_Spring = 0x0B
    High_Resolution_Damper = 0x0C
    High_Resolution_Auto_Centering_Spring = 0x0D
    Friction = 0x0E


class G29_COMMAND(Enum):
    Download_Force = 0x00
    Download_and_Play_Force = 0x01
    Play_Force = 0x02
    Stop_Force = 0x03
    Default_Spring_On = 0x04
    Default_Spring_Off = 0x05
    Turn_on_Normal_Mode = 0x08
    Set_LED = 0x09
    Set_Watchdog = 0x0A
    Turn_on_Raw_Mode = 0x0B
    Refresh_Force = 0x0C
    Fixed_Time_Loop = 0x0D
    Set_Default_Spring = 0x0E
    Set_Dead_Band = 0x0F
    Extended_Command = 0xF8



MASTER_SCALE = 1.0
#                  161    54
SYNC = bytearray([0xA1, 0x36])

class OFFB_CLS(Enum):
    FX_MANAGER = 0xA03
    AXIS = 0xA01

AXIS_POS_COMMAND = 0xE
AXIS_ROTATION_COMMAND = 0x1

class OFFB_CMDTYPE(Enum):
    WRITE = 0x00
    READ = 0x01
    WRITEADR = 0x03
    READADR = 0x04
    ACK = 0x0A
    ERR = 0x07

DEFAULT_FFBOARD_POLL_TIMEOUT = 10000

min_gain = 20 * 2
range_start = 0
range_end = 10000 * 0.5

class OFFB_FORCE_TYPE(Enum):
    Constant = 1
    Ramp = 2
    Square = 3
    Sine = 4
    Triangle = 5
    Sawtooth_up = 6
    Sawtooth_down = 7
    Spring = 8
    Damper = 9
    Inertia = 10
    Friction = 11


class OFFB_CMD(Enum):
    id = 0x80000001  # ID of class 	R
    name = 0x80000002  # name of class 	R (STR)
    help = 0x80000003  # Prints help for commands 	R I (STR)
    cmduid = 0x80000005  # Command handler index 	R
    instance = 0x80000004  # Command handler instance number 	R
    cmdinfo = 0x80000007  # Flags of a command id (adr). -1 if cmd id invalid 	RA
    ffbstate = 0x0  # FFB active 	R W
    type = 0x3  # Effect type 	RA
    reset = 0x1  # Reset all effects or effect adr 	R RA
    new = 0x2  # Create new effect of type val. Returns index or -1 on err 	W I
    mag = 0x4  # 	16b magnitude of non cond. effect adr 	WA RA
    state = 0x5  # Enable/Disable effect adr 	WA RA
    period = 0x6  # Period of effect adr 	WA RA
    duration = 0x7  # Duration of effect adr 	WA RA
    offset = 0x8  # Offset of cond. effect adr 	WA RA
    deadzone = 0x9  # Deadzone of cond. effect adr 	WA RA
    sat = 0xA  # Saturation of cond. effect adr 	WA RA
    coeff = 0xB  # Coefficient of cond. effect adr 	WA RA
    axisgain = 0xC



class WheelController(GameControllerInput):
    product_string = "Wheel"
    vid = 0x1209
    pid = 0xFFB0
    button_index_start = -1
    button_index_len = -1
    axes_index_start = 9
    axes_index_len = 2 * 1

    callback = None
    latest_report = None
    mutex = threading.Lock()
    ffb_queue = queue.Queue()

    ffb_enabled = False
    requested_ffb_type = None
    ffb_effects = []
    rx_uart_queue = queue.Queue()

    axis_pos = 0
    
    def reset_ffb(self):
        self.readData(OFFB_CLS.FX_MANAGER, 0, OFFB_CMD.reset)
        
    def enable_ffb(self):
        self.writeData(OFFB_CLS.FX_MANAGER, 0, OFFB_CMD.ffbstate, 1)
        
    def disable_ffb(self):
        self.writeData(OFFB_CLS.FX_MANAGER, 0, OFFB_CMD.ffbstate, 0)
        
    def control_ffb_effect(self, type, value):
        self.writeData(OFFB_CLS.FX_MANAGER, 0, OFFB_CMD.state, adr=self.force_index(type), data=value)
        
    def request_ffb_type(self, type: OFFB_FORCE_TYPE):
        self.requested_ffb_type = type
        self.writeData(OFFB_CLS.FX_MANAGER, 0, OFFB_CMD.new, type)
        
    def close(self):
        self.disable_ffb()
        return super().close()    

    def __init__(self):
        super().__init__()
        if self.connected:
            self.registerReadCallback(self.readDataCB)
            self.reset_ffb()
            self.enable_ffb()
            self.request_ffb_type(OFFB_FORCE_TYPE.Constant)
            self.request_ffb_type(OFFB_FORCE_TYPE.Spring)
            
            for effect in self.ffb_effects:
                print(effect)
                self.writeData(OFFB_CLS.FX_MANAGER, 0, OFFB_CMD.state, data=1, adr=self.force_index(effect[0]))  #  Enable effect

    def thread_job_while_connected_task(self):
        self.parse_ffb_packet()
        return super().thread_job_while_connected_task()
    
    def force_index(self, type: OFFB_FORCE_TYPE):
        for effect in self.ffb_effects:
            if effect[0] == type:
                return effect[1]

    def parse_ffb_packet(self):
        g29_ffb_packet = None
        input_str = None
        try:
            input_str = self.rx_uart_queue.get_nowait()
            self.rx_uart_queue.task_done()
        except queue.Empty:
            pass
            return

        if input_str is None:
            return
        
        if len(input_str) != 9:
            return
            
        # This is weird, the header is split but the FFB packet inside look good to me
        if input_str[0] == SYNC[1] and input_str[8] == SYNC[0]:
            g29_ffb_packet = input_str[1:-1]
            # for x in input_str:
            #     print(f"{hex(x)},",end="")
            # print("\n")

        if g29_ffb_packet is None:
            return
    
        cmd = g29_ffb_packet[0] & 0b00001111
        force_slot = (g29_ffb_packet[0] & 0b11110000) >> 4

        match (G29_COMMAND(cmd)):
            case G29_COMMAND.Download_and_Play_Force:
                force_type = g29_ffb_packet[1]
                match (G29_FORCE_TYPE(force_type)):
                    case G29_FORCE_TYPE.Variable:
                        # print(force_slot)
                        # L1 and L2 look signed to me
                        L1 = g29_ffb_packet[2]
                        L2 = g29_ffb_packet[3]
                        T1 = (g29_ffb_packet[4] & 0b11110000) >> 4
                        S1 = g29_ffb_packet[4] & 0b00001111
                        T2 = (g29_ffb_packet[5] & 0b11110000) >> 4
                        S2 = g29_ffb_packet[5] & 0b00001111
                        D1 = g29_ffb_packet[6] & 0b00000001
                        D2 = g29_ffb_packet[6] & 0b00010000
                        L1 = unsigned_to_signed(L1, 8)
                        L2 = unsigned_to_signed(L2, 8)
                        
                        # print(f"L1 {L1} L2 {L2} T1 {T1} S1 {S1} D1 {D1}")
                        

                        if T1 != 0 or S1 != 0 or D1 != 0:
                            print(f"T1 {T1} S1 {S1} D1 {D1}")
                        
                        if T2 != 0:
                            print("T2")

                        ratio_to_max = abs(self.axis_pos) / (1 << 15)
                        ratio_to_max = 1
                        mag = map_num(L1, -(1 << 7), (1 << 7), -(1 << 15), (1 << 15))
                        
                        
                        clamped = clamp(L1, range_start, range_end)
                        ffb_range = range_end - range_start
                        
                        r = ( (ffb_range - (clamped - range_start)) * math.pi) / ffb_range
                        c = ( math.cos(r) + 1.0 ) * (100.0 - min_gain) / 2.0
                        gain = int(c + min_gain)
                        
                        
                        mag2 = apply_gain(mag, gain, -(1 << 15), (1 << 15))
                        # print(f"mag {mag} filtered {mag2}")
                        
                        self.writeData(
                            OFFB_CLS.FX_MANAGER,
                            0,
                            OFFB_CMD.mag,
                            data=int(((mag2) * MASTER_SCALE)),
                            adr=self.force_index(OFFB_FORCE_TYPE.Constant),
                        )
                    case G29_FORCE_TYPE.High_Resolution_Spring:
                        print(f"Got Force type {G29_FORCE_TYPE(force_type).name} slot {force_slot}")
                        D1 = g29_ffb_packet[2]
                        D2 = g29_ffb_packet[3]
                        K2 = (g29_ffb_packet[4] & 0b1111_0000) >> 4
                        K1 = g29_ffb_packet[4] & 0b0000_1111
                        S2 = (g29_ffb_packet[5] & 0b0001_0000) >> 4
                        S1 = g29_ffb_packet[5] & 0b0000_0001
                            
                        mag = map_num(D1, 0, (1 << 8), 0, (1 << 15))
                        # print(mag)
                            
                        self.writeData(
                            OFFB_CLS.FX_MANAGER,
                            0,
                            OFFB_CMD.coeff,
                            data=int(((mag) * MASTER_SCALE)),
                            adr=self.force_index(OFFB_FORCE_TYPE.Spring),
                        )
                        
                    case _:
                        print(f"got force type {G29_FORCE_TYPE(force_type).name}")


            case G29_COMMAND.Default_Spring_On:
                print(f"Got command {G29_COMMAND(cmd).name} force slot {force_slot}")
                
                self.control_ffb_effect(OFFB_FORCE_TYPE.Spring, True)
                
                if force_slot in [1, 2]:
                    print("SPRING X SELECTED")
                    
                if force_slot in [3, 4]:
                    print("SPRING Y SELECTED")
                    
            case G29_COMMAND.Default_Spring_Off:
                print(f"Got command {G29_COMMAND(cmd).name} force slot {force_slot}")
                self.control_ffb_effect(OFFB_FORCE_TYPE.Spring, False)
                
                if force_slot in [1, 2]:
                    print("SPRING X SELECTED")
                    
                if force_slot in [3, 4]:
                    print("SPRING Y SELECTED")
                    
            case G29_COMMAND.Set_Default_Spring:
                print(f"Got command {G29_COMMAND(cmd).name} force slot {force_slot}")
        
                if force_slot in [1, 2]:
                    print("SPRING X SELECTED")
                    
                if force_slot in [3, 4]:
                    print("SPRING Y SELECTED")
                    

            case G29_COMMAND.Stop_Force:
                print(f"Got command {G29_COMMAND(cmd).name} force slot {force_slot}")
                
                self.writeData(
                OFFB_CLS.FX_MANAGER,
                0,
                OFFB_CMD.mag,
                data=0,
                adr=self.force_index(OFFB_FORCE_TYPE.Constant),
                )
                
            case G29_COMMAND.Turn_on_Normal_Mode:
                if force_slot == 0b1111:
                    ext_cmd = g29_ffb_packet[1]
                    match ext_cmd:
                        case 0x1:
                            print("EXT Change Mode to Driving Force Pro")
                        case 0x2:
                            print("EXT Change Wheel Range to 200 Degrees")
                            self.writeData(
                                OFFB_CLS.AXIS, 0, cmd=AXIS_ROTATION_COMMAND, data=200
                            )


                        case 0x3:
                            print("EXT Change Wheel Range to 900 Degrees")
                            self.writeData(
                                OFFB_CLS.AXIS, 0, cmd=AXIS_ROTATION_COMMAND, data=900
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
                            # print("EXT Set RPM LEDs")
                            pass
                        case 0x81:
                            print("EXT Wheel Range Change")
                            target_range = (g29_ffb_packet[3] << 8) | g29_ffb_packet[2]
                            target_range = clamp(target_range, 40, 900)
                            print(f"New requested range {target_range}")
                            self.writeData(
                                OFFB_CLS.AXIS, 0, cmd=AXIS_ROTATION_COMMAND, data=target_range
                            )
            case _:
                print(f"Got not implemented command {G29_COMMAND(cmd).name}")
                print(f"cmd {hex(cmd)} fX {hex(force_slot)}")
                for x in g29_ffb_packet:
                    print(f"{hex(x)},", end="")
                print("\n")

        # for x in g29_ffb_packet:
        #     print(f"{hex(x)},",end="")
        # print("\n")


    def process_inputs(self, report):
        
        # Spin until we found hid report that we need
        # Begins with 0x1
        
        while True:
            self.mutex.acquire()
            device_hid_report = self.hid_device.read(25)
            self.mutex.release()
            
            if device_hid_report:                
                if device_hid_report[0] != 1:
                    continue
                self.latest_report = device_hid_report
                self.decode(device_hid_report, signed=True)
                axes = self.get_axis()
                self.axis_pos = clamp(axes[0], -(1 << 15), (1 << 15))
                report.wheel = int(map_num(self.axis_pos, -(1 << 15), (1 << 15), 0xFFFF, 0))
                break

    def readDataCB(self, cmdtype, cls, inst, cmd, val, addr):
        cmdtype = OFFB_CMDTYPE(cmdtype)
        cmd = OFFB_CMD(cmd)
        cls = OFFB_CLS(cls)
        if cls == OFFB_CLS.FX_MANAGER and cmd == OFFB_CMD.new:
            self.ffb_effects.append(
                (self.requested_ffb_type, val)
            )
            self.requested_ffb_type = None
            
            print("Got new effect at index", val)


        print(f"Type: {cmdtype.name}, Class: {cls.name}:{inst}: cmd: {cmd.name}, val: {val}, addr: {addr}")


    def sendCommand(self, cmdtype, cls, inst, cmd, data=0, adr=0, timeout=DEFAULT_FFBOARD_POLL_TIMEOUT):
        buffer = self.make_command(cmdtype, cls, inst, cmd, data, adr)
        self.mutex.acquire()
        self.hid_device.set_nonblocking(False)
        self.hid_device.write(buffer)  # Send raw packet
        self.mutex.release()
        og_timeout = timeout

        commands_that_need_reply = [OFFB_CMD.new,  OFFB_CMD.reset, OFFB_CMD.ffbstate]
        block = False
        if OFFB_CMD(cmd) in commands_that_need_reply:
            print("NEED REPLY")
            block = True

        if block:
            found = False
            while not found and timeout:  # Receive all reports until correct one is found.
                timeout -= 1
                self.mutex.acquire()
                reply = self.hid_device.read(25)
                self.mutex.release()
                # reply = self.latest_report
                if reply[0] == 0xA1:
                    print(f"attempts:{og_timeout - timeout}")
                    found = True
                    self.latest_report = [0]
                    repl = self.parse_command(reply)
                    if repl["cls"] == cls and repl["inst"] == inst and repl["cmd"] == cmd:
                        found = True
                        break
            if timeout == 0:
                print("timeout")

            if found:
                if self.callback:
                    self.callback(
                        repl["cmdtype"],
                        repl["cls"],
                        repl["inst"],
                        repl["cmd"],
                        repl["val"],
                        repl["addr"],
                    )
                if repl:
                    return repl

    def make_command(self, cmdtype, cls, inst, cmd, data=0, adr=0):
        """Generates a command packet"""
        buffer = bytearray()
        buffer += bytearray(struct.pack("B", 0xA1))  # HIDCMD
        buffer += bytearray(struct.pack("B", cmdtype))  # type. (0 = write, 1 = read)
        buffer += bytearray(struct.pack("<H", cls))
        buffer += bytearray(struct.pack("B", inst))
        buffer += bytearray(struct.pack("<L", cmd))
        buffer += bytearray(struct.pack("<q", data))
        buffer += bytearray(struct.pack("<q", adr if adr else 0))
        return buffer

    def readData(self, cls, inst, cmd: OFFB_CMD, adr=None, timeout=DEFAULT_FFBOARD_POLL_TIMEOUT):
        """Returns a value from the FFBoard.
        Returns int for single value replies or a tuple for cmd and addr replies"""
        reply = self.sendCommand(
            OFFB_CMDTYPE.READ.value if adr is None else OFFB_CMDTYPE.READADR.value,
            cls.value if isinstance(cls, Enum) else cls,
            inst,
            cmd.value if isinstance(cmd, Enum) else cmd,
            0,
            adr,
            timeout=timeout,
        )
        if reply:
            if reply["cmdtype"] == OFFB_CMDTYPE.READ.value:
                return reply["val"]
            elif reply["cmdtype"] == OFFB_CMDTYPE.READADR.value:
                return reply["val"], reply["addr"]
        
    def writeData(self, cls, inst, cmd: OFFB_CMD, data: OFFB_FORCE_TYPE, adr=None, timeout=DEFAULT_FFBOARD_POLL_TIMEOUT):
        """Sends data to the FFBoard. Returns True on success"""
        reply = self.sendCommand(
            OFFB_CMDTYPE.WRITE.value if adr is None else OFFB_CMDTYPE.WRITEADR.value,
            cls=cls.value if isinstance(cls, Enum) else cls,
            inst=inst,
            cmd=cmd.value if isinstance(cmd, Enum) else cmd,
            data=data.value if isinstance(data, Enum) else data,
            adr=adr,
            timeout=timeout,
        )
        # return reply["cmdtype"] != CMDTYPE_ERR

    def parse_command(self, data):
        """Returns a parsed packet as a dict
        Entries: "cmdtype":cmdtype,"cls":cls,"inst":instance,"cmd":cmd,"val":val,"addr":addr
        """
        cmdtype = int(data[1])
        cls = int(struct.unpack("<H", bytes(data[2:4]))[0])
        instance = int(data[4])
        cmd = int(struct.unpack("<L", bytes(data[5:9]))[0])
        val = int(struct.unpack("<q", bytes(data[9:17]))[0])
        addr = int(struct.unpack("<q", bytes(data[17:25]))[0])
        return {
            "cmdtype": cmdtype,
            "cls": cls,
            "inst": instance,
            "cmd": cmd,
            "val": val,
            "addr": addr,
        }

    def registerReadCallback(self, callback):
        """Register a callback to also call this function on every received reply"""
        self.callback = callback
