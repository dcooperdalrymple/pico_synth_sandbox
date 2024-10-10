# SPDX-FileCopyrightText: Copyright (c) 2024 Cooper Dalrymple
#
# SPDX-License-Identifier: Unlicense

import board
import digitalio
import rotaryio
import adafruit_debouncer
import adafruit_character_lcd.character_lcd as character_lcd
import audiobusio
import ttp229
import busio
import adafruit_midi
import usb_midi
import microcontroller
import sdcardio
import storage

CHANNELS = 2
BITS = 16
SAMPLE_RATE = 44100
BUFFER_SIZE = 8192
TASK_SLEEP = 0.001

COLUMNS = 16
ROWS = 2

led_pin = board.LED
button_pins = (board.GP13, board.GP18)
i2s_bclk, i2s_lclk, i2s_data = board.GP19, board.GP20, board.GP21
uart_tx, uart_rx = board.GP4, board.GP5
ttp_sdo, ttp_scl = board.GP14, board.GP15
lcd_pins = (board.GP7, board.GP6, board.GP22, board.GP26, board.GP27, board.GP28)
encoder_pins = (
    (board.GP12, board.GP11),
    (board.GP17, board.GP16),
)
spi_clock, spi_mosi, spi_miso, spi_cs = board.GP2, board.GP3, board.GP0, board.GP1

if board.board_id == "raspberry_pi_pico":
    microcontroller.cpu.frequency = 250000000
elif board.board_id == "raspberry_pi_pico2":
    SAMPLE_RATE = 48000
    microcontroller.cpu.frequency = 300000000

led = None
audio = None
midi_usb = None
uart = None
midi_uart = None
ttp = None
lcd_gpio = None
lcd = None
button_gpio = None
buttons = None
encoders = None
spi = None
sdcard = None
sdvfs = None

def init() -> None:
    global led, audio, midi_usb, uart, midi_uart, ttp, lcd, lcd_gpio, buttons, button_gpio, encoders, spi, sdcard, sdvfs

    # Status LED
    led = digitalio.DigitalInOut(led_pin)
    led.direction = digitalio.Direction.OUTPUT

    # I2S Audio Output
    audio = audiobusio.I2SOut(
        bit_clock=i2s_bclk,
        word_select=i2s_lclk,
        data=i2s_data,
    )

    # USB MIDI
    if usb_midi.ports:
        midi_usb = adafruit_midi.MIDI(
            midi_in=usb_midi.ports[0],
            in_channel=0,
            midi_out=usb_midi.ports[1],
            out_channel=0,
            debug=False,
        )

    # UART MIDI
    uart = busio.UART(
        tx=uart_tx,
        rx=uart_rx,
        baudrate=31250,
        timeout=0.001,
    )
    midi_uart = adafruit_midi.MIDI(
        midi_in=uart,
        in_channel=0,
        midi_out=uart,
        out_channel=0,
        debug=False,
    )

    # Touch Keyboard Interface
    ttp = ttp229.TTP229(
        sdo=ttp_sdo,
        scl=ttp_scl,
        mode=ttp229.Mode.KEY_16,
        invert_clk=True,
    )

    # Character LCD Menu
    lcd_gpio = tuple([digitalio.DigitalInOut(pin) for pin in lcd_pins])
    lcd = character_lcd.Character_LCD_Mono(
        rs = lcd_gpio[0],
        en = lcd_gpio[1],
        db4 = lcd_gpio[2],
        db5 = lcd_gpio[3],
        db6 = lcd_gpio[4],
        db7 = lcd_gpio[5],
        columns=COLUMNS,
        lines=ROWS,
    )

    # Controls
    button_gpio = []
    for pin in button_pins:
        gpio = digitalio.DigitalInOut(pin)
        gpio.direction = digitalio.Direction.INPUT
        gpio.pull = digitalio.Pull.UP
        button_gpio.append(gpio)
    button_gpio = tuple(button_gpio)
    buttons = tuple([adafruit_debouncer.Debouncer(gpio) for gpio in button_gpio])
    encoders = tuple([rotaryio.IncrementalEncoder(pins[0], pins[1]) for pins in encoder_pins])

    # SD Card SPI & Storage
    spi = busio.SPI(
        clock=spi_clock,
        MOSI=spi_mosi,
        MISO=spi_miso
    )
    sdcard = sdcardio.SDCard(spi, spi_cs)
    sdvfs = storage.VfsFat(sdcard)
    storage.mount(sdvfs, "/sd")


def deinit() -> None:
    global led, audio, midi_usb, uart, midi_uart, ttp, lcd, lcd_gpio, buttons, button_gpio, encoders, spi, sdcard, sdvfs

    if led is not None:
        led.deinit()
        led = None

    if audio is not None:
        audio.deinit()
        audio = None
    
    if midi_usb is not None:
        midi_usb = None
    
    if midi_uart is not None:
        midi_uart = None
        uart.deinit()
        uart = None
    
    if ttp is not None:
        ttp.deinit()
        ttp = None
    
    if lcd is not None:
        lcd = None
        for gpio in lcd_gpio:
            gpio.deinit()
        lcd_gpio = None

    if buttons is not None:
        buttons = None
        for gpio in button_gpio:
            gpio.deinit()
        button_gpio = None
    
    if encoders is not None:
        for encoder in encoders:
            encoder.deinit()
        encoders = None

    if sdvfs is not None:
        storage.umount(sdvfs)
        sdvfs = None

    if sdcard is not None:
        sdcard.deinit()
        sdcard = None
    
    if spi is not None:
        spi.deinit()
        spi = None
