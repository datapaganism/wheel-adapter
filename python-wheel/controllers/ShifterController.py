from .GameControllerInput import GameControllerInput
from utils import *

class Shifter(GameControllerInput):
    product_string = "Shifter"
    vid = 0x0079
    pid = 0x0006
    button_index_start = 5
    button_index_len = 1 * 2
    axes_index_start = -1
    axes_index_len = -1

    def process_inputs(self, report):
        device_hid_report = self.hid_device.read(self.report_length)  
        if device_hid_report:
            self.decode(device_hid_report, signed=False)
            buttons = self.get_buttons()
            buttons = buttons[4:]

            
            
            report.gear1 = buttons[0]
            report.gear2 = buttons[1]
            report.gear3 = buttons[2]
            report.gear4 = buttons[3]
            report.gear5 = buttons[4]
            report.gear6 = buttons[5]
            report.gear7 = buttons[6]         
            report.gearR = buttons[7]
            
            report.R1Paddle = buttons[2]
            report.L1Paddle = buttons[4]
            
            
            
            
            
