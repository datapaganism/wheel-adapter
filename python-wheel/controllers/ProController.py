from .GameControllerInput import GameControllerInput
from utils import *


class ProController(GameControllerInput):
    product_string = "Pro Controller"
    vid = 0x057E
    pid = 0x2009
    button_index_start = 3
    button_index_len = 3
    axes_index_start = 7
    axes_index_len = 4
    rep = 0
    #                             lx    ly        rx  ry                                        
    # 30, 37, 81, 00, 80, 00, 1e, 18, 7c, 81, a7, 79,
    def process_inputs(self, report):
        device_hid_report = self.hid_device.read(64)  # Read 64 bytes
        if device_hid_report:
            self.decode(device_hid_report,axis_width=8)
            buttons = self.get_buttons()
            axis = self.get_axis()
            # print(axis)
            # print(buttons)
            report.cross = buttons[2]
            report.circle = buttons[3]
            report.triangle = buttons[1]
            report.square = buttons[0]

            report.PS = buttons[12]
            report.startOptions = buttons[9]
            report.selectShare = buttons[8]
            report.counter = buttons[13]
            if buttons[13] == 1:
                self.rep += 1
                print(self.rep)
                report.counter = self.rep
                
                
            
            # report.throttle = int(map_num(buttons[7], 0, 1, 0xFFFF, 0))
            # report.brake = int(map_num(buttons[23], 0, 1, 0xFFFF, 0))
            # report.wheel = int(map_num(axis[1], 0, 0xFF, 0xFFFF, 0))
            # print(report.wheel)
            
            report.L1Paddle=buttons[4]
            report.R1Paddle=buttons[5]
            report.L2=buttons[22]
            report.R2=buttons[6]
            report.L3=buttons[11]
            report.LR=buttons[10]
            
            
            

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

