from .GameControllerInput import GameControllerInput
from utils import *

class PedalsController(GameControllerInput):
    product_string = "Pedals"
    vid = 0x1209
    pid = 0xA136
    button_index_start = -1
    button_index_len = -1
    axes_index_start = 5
    axes_index_len = 2 * 6  # 6 16bit axes
    report_length = 11

    def process_inputs(self, report):
        device_hid_report = self.hid_device.read(self.report_length)  
        if device_hid_report:
            self.decode(device_hid_report, signed=True)
            axes = self.get_axis()

            throt = axes[0]
            brake = axes[1]
            clutch = axes[2]
            report.throttle = int(map_num(throt, -(1 << 15), (1 << 15), 0xFFFF, 0))
            # report.brake = int(map_num(brake, -(1 << 15), (1 << 15), 0xFFFF, 0))
            # report.clutch = int(map_num(clutch, -(1 << 15), (1 << 15), 0xFFFF, 0))
            report.brake = int(map_num(clutch, -(1 << 15), (1 << 15), 0xFFFF, 0))
            
            # print(f"A: {report.throttle} B: {report.brake} C: {report.clutch}")

