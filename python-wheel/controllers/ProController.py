from .GameControllerInput import GameControllerInput


class ProController(GameControllerInput):
    product_string = "Pro Controller"
    vid = 0x057E
    pid = 0x2009
    button_index_start = 3
    button_index_len = 3
    axes_index_start = 7
    axes_index_len = 4

    def process_inputs(self, report):
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
            # report.throttle = int(num_to_range(buttons[7], 0, 1, 0xFFFF, 0))
            # report.brake = int(num_to_range(buttons[23], 0, 1, 0xFFFF, 0))

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

