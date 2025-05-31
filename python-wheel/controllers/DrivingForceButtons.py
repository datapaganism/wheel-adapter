from .GameControllerInput import GameControllerInput
from utils import *


class DrivingForceButtons(GameControllerInput):
    product_string = "Driving Force Buttons"
    vid = 0x1B4F
    pid = 0x9206
    button_index_start = 1
    button_index_len = 1 * 3
    axes_index_start = -1
    axes_index_len = -1
    report_length = 5

    def process_inputs(self, report):
        device_hid_report = self.hid_device.read(self.report_length)  
        if device_hid_report:
            self.decode(device_hid_report,axis_width=8)
            buttons = self.get_buttons()
            report.cross = buttons[11]
            report.circle = buttons[9]
            report.triangle = buttons[8]
            report.square = buttons[10]

            report.PS = buttons[6]
            report.startOptions = buttons[3]
            report.selectShare = buttons[7]
            report.plus = buttons[4]
            report.minus = buttons[5]
            report.enter = buttons[0]
            report.dial_cw = buttons[2]
            report.dial_ccw = buttons[1]
            report.L2=buttons[18]
            report.R2=buttons[13]
            report.L3=buttons[17]
            report.R3=buttons[14]
                        
            dpad = buttons[20 : 20 + 4]
            ddown = dpad[2]
            dup = dpad[3]
            dleft = dpad[1]
            dright = dpad[0]
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

