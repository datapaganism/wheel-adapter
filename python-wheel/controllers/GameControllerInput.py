import time
import hid
from g29report import G29Report


class GameControllerInput:
    manufacturer_string = ""
    product_string = ""
    running = True
    connected = False
    hid_device = None
    buttons = []
    axes = []
    vid = 0
    pid = 0

    report_length = 64
    button_index_start = 0
    button_index_len = 0
    axes_index_start = 0
    axes_index_len = 0
    g29report = G29Report().get()

    def process_inputs(self, report):
        pass

    def __init__(self):
        self.connect()

    def connect(self):
        try:
            self.hid_device = hid.device()
            self.hid_device.open(self.vid, self.pid)
            self.connected = True
        except Exception as e:
            print(f"Failed to open hid device {self.product_string} due to: {e}")
            self.connected = False

        # try:
        #     # self.manufacturer_string = self.hid_device.get_manufacturer_string()
        #     self.product_string = self.hid_device.get_product_string()
        if self.connected:
            print(f"Connected to {self.product_string}")
        # except Exception as e:
        #     print(e)
        #     print("Failed to get hid device details")
        #     self.connected = False

    def close(self):
        self.hid_device.close()
        self.connected = False

    def __repr__(self):
        return f"Buttons: {self.buttons}, Axes: {self.axes}"

    def get_buttons(self):
        return self.buttons

    def get_axis(self):
        return self.axes

    # def stop(self):
    #     self.running = False
    
    def get_g29report(self):
        temp = self.g29report.pack()
        return temp
    
    def thread_job_while_connected_task(self):
        try:
            self.process_inputs(self.g29report)
        except:
            pass
        
    def thread_job(self, stop_event):
        while self.connected and not stop_event.is_set():
            # if not self.connected:
            #     print("trying reconnect")
            #     self.connect()
            try:
                if self.connected:
                    self.thread_job_while_connected_task()
                    time.sleep(1 / 300)
                    
            except:
                print(f"{self.product_string} FAILED to process inputs")
                raise
        print(f"Thread exit -  {self.product_string}")
        self.close()

    def decode(self, report, axis_width=16, signed=False):

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
            
            if axis_width > 8:
                # Convert axis values (assuming they are 16-bit signed integers)
                AXIS_WIDTH = int(axis_width / 8)  # 16bit
                self.axes = [
                    int.from_bytes(
                        raw_axes[i : i + AXIS_WIDTH], byteorder="little", signed=signed
                    )
                    for i in range(0, len(raw_axes), AXIS_WIDTH)
                ]
            else:
                self.axes = raw_axes
            # for x in self.axes:
            #     x &= (1 < 10)
            # print(self.axes)
