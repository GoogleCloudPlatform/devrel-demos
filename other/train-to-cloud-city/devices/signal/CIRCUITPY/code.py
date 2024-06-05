# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Requirements
#
# Download stable version 9 of the CircuitPython runtime:
# https://circuitpython.org/board/adafruit_qtpy_rp2040/
# then install via boot mode:
# https://learn.adafruit.com/welcome-to-circuitpython/installing-circuitpython

print("Hello Trains!")

import board
import time
import neopixel
import usb_cdc
import asyncio

VERSION = '3'


# Colors are (Red, Green, Blue) on a 0-255 scale.
OFF =    ((0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0))
ORANGE = ((25, 15, 0, 0), (250, 150, 0, 0), (250, 150, 0, 0))
STOP =   ((25, 0, 0, 0), (250, 0, 0, 0), (250, 0, 0, 0))
CLEAR =  ((0, 25, 0, 0), (0, 250, 0, 0), (0, 250, 0, 0))

HELP = b"""HELP
Valid commands:
OFF    Turn off signal light.
STOP   Set signal light to red.
CLEAR  Set signal light to green.
HELP   This text.
(follow each command with a newline character)"""

BRIGHTNESS = 0.9
onboard_pixel = neopixel.NeoPixel(board.NEOPIXEL, 1,
    brightness=BRIGHTNESS)

pixel_pin = board.A0
num_pixels = 2
pixels = neopixel.NeoPixel(pixel_pin, num_pixels,
    brightness=BRIGHTNESS, auto_write=False, pixel_order=(1, 0, 2, 3),)

# This signal's ID. Write some short string to "id.txt"
try:
    ID = open("id.txt").read().strip().encode("UTF-8")
except BaseException:
    ID = b"UNKNOWN"

board.BUTTON
from digitalio import DigitalInOut, Direction, Pull

btn = DigitalInOut(board.BUTTON)
btn.direction = Direction.INPUT
btn.pull = Pull.UP


def init():
    set_pixels(ORANGE)
    print(f'my id is: {ID}')
    usb_cdc.data.write(ID + b':INIT\n')
    usb_cdc.data.write(ID + b':VERSION ' + VERSION.encode('UTF-8') + '\n')

def set_pixels(color_rgb):
    onboard_pixel[0] = color_rgb[0][:3]
    pixels[0] = color_rgb[1]
    pixels[1] = color_rgb[2]
    pixels.show()

def serial_response(result):
    usb_cdc.data.write(ID)
    usb_cdc.data.write(b':')
    usb_cdc.data.write(result)
    usb_cdc.data.write(b'\n')

def parse_and_run_command(input):
    input = input.strip().upper()
    if input == b'HELP':
        set_pixels(ORANGE)
        return HELP
    elif input == b'OFF' or input == b'O':
        set_pixels(OFF)
        return input
    elif input == b'STOP' or input == b'S':
        set_pixels(STOP)
        return input
    elif input == b'CLEAR' or input == b'C':
        set_pixels(CLEAR)
        return input
    else:
        set_pixels(ORANGE)
        return b'ERROR: Unknown command: ' + input + b' (Enter HELP for command list.)'

async def usb_client():
    usb_cdc.data.timeout = 0
    s = asyncio.StreamReader(usb_cdc.data)
    while True:
        data = await s.readline()
        print("input: ", data)
        try:
            result = parse_and_run_command(data)
        except Exception as err:
            result = 'ERROR: ' + str(type(err)) + str(err)
            result.encode("UTF-8")
        serial_response(result)

# Press "BOOT" button to cycle between states.
async def button():
    prev_state = btn.value
    states = [(STOP, b'STOP'), (CLEAR, b'CLEAR'), (OFF, b'OFF'), (ORANGE, b'ERROR')]
    index = 0

    while True:
        cur_state = btn.value
        if cur_state != prev_state:
            if not cur_state:
                # print("BUTTON is down")
                pass
            else:
                # print("BUTTON is up")
                color, result = states[index % 4]
                set_pixels(color)
                serial_response(result)
                index += 1
        prev_state = cur_state
        await asyncio.sleep(0.2)

async def counter():
    i = 0
    while True:
        usb_cdc.data.write(ID)
        usb_cdc.data.write(b':HEARTBEAT\n')
        await asyncio.sleep(60)

async def main():
    init()
    clients = [asyncio.create_task(counter())]
    clients.append(asyncio.create_task(usb_client()))
    clients.append(asyncio.create_task(button()))
    await asyncio.gather(*clients)

asyncio.run(main())
