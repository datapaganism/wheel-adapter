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
        device_hid_report = self.hid_device.read(64)  # Read 64 bytes
        if device_hid_report:
            self.decode(device_hid_report, signed=False)
            buttons = self.get_buttons()

            report.R1 = buttons[7]
            report.L1 = buttons[6]
