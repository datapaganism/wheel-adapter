import pygame
import threading
import queue
import serial
from g29report import G29Report


def read_uart(inputQueue):
    while (True):
        if (ser.inWaiting() > 0):
            x = ser.read(ser.inWaiting())
            inputQueue.put(x)


def parse_ffb_packet(inputQueue):
    if (inputQueue.qsize() > 0):
        input_str = inputQueue.get()
        if (len(input_str) == 9):
        # This is weird, the header is split but the FFB packet inside look good to me
            if (input_str[0] == SYNC[1] and input_str[8] == SYNC[0]):
                input_str = input_str[1:-1]
                for x in input_str:
                    print(f"{hex(x)},",end="")
                print("\n")


def send_uart_packet():
    packed = report.pack()
    packed = SYNC + packed
    x = ser.write(packed)

def num_to_range(num, inMin, inMax, outMin, outMax):
  return outMin + (float(num - inMin) / float(inMax - inMin) * (outMax
                  - outMin))



pygame.init()

BAUDRATE = 921600
BAUDRATE = 115200

ser = serial.Serial('/dev/ttyUSB0',baudrate=BAUDRATE)  # open serial port
report = G29Report().get()

# Reverse byte order
# 161 54
SYNC = bytearray([0xA1, 0x36])

# This is a simple class that will help us print to the screen.
# It has nothing to do with the joysticks, just outputting the
# information.
class TextPrint:
    def __init__(self):
        self.reset()
        self.font = pygame.font.Font(None, 25)

    def tprint(self, screen, text):
        text_bitmap = self.font.render(text, True, (0, 0, 0))
        screen.blit(text_bitmap, (self.x, self.y))
        self.y += self.line_height

    def reset(self):
        self.x = 10
        self.y = 10
        self.line_height = 15

    def indent(self):
        self.x += 10

    def unindent(self):
        self.x -= 10


def main():

    rx_uart_queue = queue.Queue()
    read_uart_ffb_thread = threading.Thread(target=read_uart, args=(rx_uart_queue,), daemon=True)
    read_uart_ffb_thread.start()

    # Set the width and height of the screen (width, height), and name the window.
    screen = pygame.display.set_mode((500, 1000))
    pygame.display.set_caption("Joystick example")

    # Used to manage how fast the screen updates.
    clock = pygame.time.Clock()

    # Get ready to print.
    text_print = TextPrint()

    # This dict can be left as-is, since pygame will generate a
    # pygame.JOYDEVICEADDED event for every joystick connected
    # at the start of the program.
    joysticks = {}

    done = False
    while not done:

        parse_ffb_packet(rx_uart_queue)

        # Event processing step.
        # Possible joystick events: JOYAXISMOTION, JOYBALLMOTION, JOYBUTTONDOWN,
        # JOYBUTTONUP, JOYHATMOTION, JOYDEVICEADDED, JOYDEVICEREMOVED
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                done = True  # Flag that we are done so we exit this loop.

            if event.type == pygame.JOYBUTTONDOWN:
                pass
                # print("Joystick button pressed.")
                # if event.button == 0:
                #     joystick = joysticks[event.instance_id]
                #     if joystick.rumble(0, 0.7, 500):
                #         print(f"Rumble effect played on joystick {event.instance_id}")

            if event.type == pygame.JOYBUTTONUP:
                pass

            # Handle hotplugging
            if event.type == pygame.JOYDEVICEADDED:
                # This event will be generated when the program starts for every
                # joystick, filling up the list without needing to create them manually.
                joy = pygame.joystick.Joystick(event.device_index)
                joysticks[joy.get_instance_id()] = joy
                print(f"Joystick {joy.get_instance_id()} connencted {joy.get_name()}")

            if event.type == pygame.JOYDEVICEREMOVED:
                del joysticks[event.instance_id]
                print(f"Joystick {event.instance_id} disconnected")


        # Drawing step
        # First, clear the screen to white. Don't put other drawing commands
        # above this, or they will be erased with this command.
        screen.fill((255, 255, 255))
        text_print.reset()

        report.wheel = 0xFFFF   
        report.throttle = 0xFFFF
        report.brake = 0xFFFF
        report.clutch = 0xFFFF

        # For each joystick:
        for joystick in joysticks.values():
            j = joystick

            if (j.get_name() == "datapaganism Racing Pedals"):
                throt = j.get_axis(2)
                throt = num_to_range(throt,-1, 1, 0xFFFF, 0)
                report.throttle = int(throt)

                brake = j.get_axis(5)
                brake = num_to_range(brake,-1, 1, 0xFFFF, 0)
                report.brake = int(brake)

                # clutch = j.get_axis(5)
                # clutch = num_to_range(clutch,-1, 1, 0xFFFF, 0)
                # report.clutch = int(clutch)

            if (j.get_name() == "Open FFBoard FFBoard"):
                axis0 = j.get_axis(0)
                axis0 = num_to_range(axis0,-1, 1, 0xFFFF, 0)
                report.wheel = int(axis0)
                pass
                # continue

            if (j.get_name() == "Nintendo Co., Ltd. Pro Controller"):
                report.cross = j.get_button(0)
                report.circle = j.get_button(1)
                report.triangle = j.get_button(2)
                report.square = j.get_button(3)
                report.PS = j.get_button(11)
                report.start = j.get_button(10)

                throt = j.get_button(8)
                throt = num_to_range(throt,0, 1, 0xFFFF, 0)
                report.throttle = int(throt)

                brake = int(j.get_button(7))
                brake = num_to_range(brake, 0, 1, 0xFFFF, 0)
                report.brake = int(brake)

                axis0 = j.get_axis(0)
                axis0 = num_to_range(axis0,-1, 1, 0, 0xFFFF)
                report.wheel = int(axis0)
         

                # stick_left_right = j.get_axis(0) # 1 is full left, -1 full right
                # axis0 = j.get_axis(0)
                # axis0 = num_to_range(axis0,-1,1, 0, 0xFFFF)
                # report.wheel = int(axis0)

                # axis1 = j.get_axis(1)
                # axis1 = num_to_range(axis1,-1,1, 0, 0xFFFF)
                # report.throttle = int(axis1)




                dpad = j.get_hat(0)
                # report.dpad = 0b0001 # (1,  1)
                # report.dpad = 0b0010 # (1, 0)
                # report.dpad = 0b0011 # (1, -1)
                # report.dpad = 0b0100 # (0, -1)
                # report.dpad = 0b0101 # (-1, -1)
                # report.dpad = 0b0110 # (-1, 0)
                # report.dpad = 0b0111 # (-1, 1)

                if (dpad[1] == 0 and dpad[0] == 0):
                    report.dpad = 0b1000 # (0,0)

                if (dpad[1] == -1 and dpad[0] == -1): # diag bottom left
                    report.dpad = 0b0011 # (-1, -1) 

                if (dpad[0] == 1 and dpad[1] == 0): # Right
                    report.dpad = 0b0010

                if (dpad[0] == -1 and dpad[1] == 0): # Left
                    report.dpad = 0b0110

                if (dpad[0] == 0 and dpad[1] == -1): # Down
                    report.dpad = 0b0100

                if (dpad[0] == 0 and dpad[1] == 1): # Up
                    report.dpad = 0b0000

                # report.dpad = 0b1001 # (, )
                # report.dpad = 0b1010 # (, )
                # report.dpad = 0b1011 # (, )
                # report.dpad = 0b1100 # (0, 1)?
                # report.dpad = 0b1101 # (0, 1)
                # report.dpad = 0b1110 # (0, 0)
                # report.dpad = 0b1111 # (0, 0)
                

               
                



                pass
            jid = joystick.get_instance_id()

            text_print.tprint(screen, f"Joystick {jid}")
            text_print.indent()

            # Get the name from the OS for the controller/joystick.
            name = joystick.get_name()
            text_print.tprint(screen, f"Joystick name: {name}")

            guid = joystick.get_guid()
            text_print.tprint(screen, f"GUID: {guid}")

            # power_level = joystick.get_power_level()
            # text_print.tprint(screen, f"Joystick's power level: {power_level}")

            # Usually axis run in pairs, up/down for one, and left/right for
            # the other. Triggers count as axes.
            axes = joystick.get_numaxes()
            text_print.tprint(screen, f"Number of axes: {axes}")
            text_print.indent()

            for i in range(axes):
                axis = joystick.get_axis(i)
                text_print.tprint(screen, f"Axis {i} value: {axis:>6.3f}")
            text_print.unindent()

            buttons = joystick.get_numbuttons()
            text_print.tprint(screen, f"Number of buttons: {buttons}")
            text_print.indent()

            for i in range(buttons):
                button = joystick.get_button(i)
                text_print.tprint(screen, f"Button {i:>2} value: {button}")
            text_print.unindent()

            hats = joystick.get_numhats()
            text_print.tprint(screen, f"Number of hats: {hats}")
            text_print.indent()

            # Hat position. All or nothing for direction, not a float like
            # get_axis(). Position is a tuple of int values (x, y).
            for i in range(hats):
                hat = joystick.get_hat(i)
                text_print.tprint(screen, f"Hat {i} value: {str(hat)}")
            text_print.unindent()

            text_print.unindent()

        send_uart_packet()

        # Go ahead and update the screen with what we've drawn.
        pygame.display.flip()

        # Limit to 30 frames per second.
        clock.tick(30)


if __name__ == "__main__":
    main()
    # If you forget this line, the program will 'hang'
    # on exit if running from IDLE.
    pygame.quit()