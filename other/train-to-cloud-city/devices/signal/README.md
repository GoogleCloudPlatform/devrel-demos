This is the code which runs on each of the physical signal lights. 

For the demo, they were build out of lego and an Adafruit [QT Py RP2040](https://www.adafruit.com/product/4900) and two [NeoPixel RGBW Mini Button](https://www.adafruit.com/product/4776)s.  

It's possible to test without the extra NeoPixels, the code will also update the NeoPixel on the QT Py board. 

## Installation

Download stable version 9 of the CircuitPython runtime:
https://circuitpython.org/board/adafruit_qtpy_rp2040/

and the libraries bundle version 9: 
https://circuitpython.org/libraries

then install via boot mode:
https://learn.adafruit.com/welcome-to-circuitpython/installing-circuitpython


## Installation steps

* Copy the *.uf2 file to the RPI-RP2 volume. It will then reboot into a volume nameed `CIRCUITPY`.
* Then copy all files in the `CIRCUITPY` directory onto the new USB media volume which should be named `CIRCUITPY`.
* Then set the ID for this device by editing `id.txt`.
* Copy needed library modules from the libraries bundle to the `lib` directory on the USB volume: `neopixel_spi.mpy`, `neopixel.mpy`,	`adafruit_ticks.mpy` and the `asyncio` folder.
* Then eject and reconnect. Should be able to connect with a serial terminal program at 9600 baud. (CoolTerm works well on MacOS)


## Protocol

The signal is lit yellow at startup and on errors, green for CLEAR and red for STOP. 

Each signal exposes a USB serial port and accepts commands via a text protocol. 

```plain
Valid commands:
OFF    Turn off signal light.
STOP   Set signal light to red.
CLEAR  Set signal light to green.
HELP   This text.
(follow each command with a newline character)
```
And it responds with its' own signal ID and the executed command, or error text:
```plain
SIGNAL_A:HEARTBEAT
SIGNAL_A:CLEAR
SIGNAL_A:STOP
SIGNAL_A:CLEAR
SIGNAL_A:STOP
SIGNAL_A:ERROR: Unknown command: ABC (Enter HELP for command list.)
```

It also sends `SIGNAL_A:HEARTBEAT` approximately once a minute. 
