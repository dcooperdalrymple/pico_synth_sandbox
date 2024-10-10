# SPDX-FileCopyrightText: Copyright (c) 2024 Cooper Dalrymple
#
# SPDX-License-Identifier: Unlicense

import synthwaveform
import synthvoice.sample
import synthkeyboard

import audiomixer
import synthio

import synthmenu.character_lcd

import adafruit_midi
from adafruit_midi.note_on import NoteOn
from adafruit_midi.note_off import NoteOff
from adafruit_midi.control_change import ControlChange
from adafruit_midi.pitch_bend import PitchBend
from adafruit_midi.midi_message import MIDIMessage, MIDIUnknownEvent

import asyncio
import time
import os
import board
import gc

import hardware
import menu
import settings

VOICES = 12 if board.board_id == "raspberry_pi_pico2" else 6

DIR = "/sd/samples"
try:
    os.stat(DIR)
except OSError:
    DIR = "/samples"

hardware.init()

## Audio Output + Synthesizer

mixer = audiomixer.Mixer(
    voice_count=1,
    channel_count=hardware.CHANNELS,
    sample_rate=hardware.SAMPLE_RATE,
    buffer_size=hardware.BUFFER_SIZE,
    bits_per_sample=hardware.BITS,
    samples_signed=True,
)
hardware.audio.play(mixer)

synth = synthio.Synthesizer(
    sample_rate=hardware.SAMPLE_RATE,
    channel_count=hardware.CHANNELS,
)
mixer.voice[0].play(synth)

voices = tuple([synthvoice.sample.Sample(synth) for i in range(VOICES)])

async def voice_task() -> None:
    while True:
        for i in range(len(voices)):
            voices[i].update()
        await asyncio.sleep(hardware.TASK_SLEEP)

## Keyboard Manager

keyboard = synthkeyboard.Keyboard(
    max_voices=VOICES,
    root=48,
)

def voice_press(voice:synthvoice.Voice) -> None:
    voices[voice.index].press(
        notenum=voice.note.notenum,
        velocity=voice.note.velocity,
    )
    hardware.led.value = True
keyboard.on_voice_press = voice_press

def voice_release(voice:synthvoice.Voice) -> None:
    voices[voice.index].release()
    hardware.led.value = False
keyboard.on_voice_release = voice_release

keyboard.arpeggiator = synthkeyboard.Arpeggiator(
    steps=synthkeyboard.TimerStep.QUARTER,
    mode=synthkeyboard.ArpeggiatorMode.UP,
)

## USB & Hardware MIDI

def midi_process_message(msg:MIDIMessage) -> None:
    if settings.midi_thru and not isinstance(msg, MIDIUnknownEvent):
        hardware.midi_usb.send(msg)
        hardware.midi_uart.send(msg)

    if settings.midi_channel is not None and msg.channel != settings.midi_channel:
        return
    
    if isinstance(msg, NoteOn):
        if msg.velocity > 0.0:
            keyboard.append(msg.note, msg.velocity)
        else:
            keyboard.remove(msg.note)

    elif isinstance(msg, NoteOff):
        keyboard.remove(msg.note)

    elif isinstance(msg, ControlChange):
        if msg.control == 7: # Volume
            mixer.voice[0].level = msg.value / 127
        elif msg.control == 10: # Pan
            menu.set_attribute(voices, 'pan', msg.value / 64 - 1)
        elif msg.control == 11: # Expression
            menu.set_attribute(voices, 'velocity_amount', msg.value / 127)
        elif msg.control == 64: # Sustain
            keyboard.sustain = msg.value >= 64

    elif isinstance(msg, PitchBend):
        menu.set_attribute(voices, 'bend', (msg.pitch_bend - 8192) / 8192)
    
def midi_process_messages(midi:adafruit_midi.MIDI, limit:int = 32) -> None:
    while limit:
        if not (msg := midi.receive()):
            break
        midi_process_message(msg)
        limit -= 1

async def midi_task() -> None:
    while True:
        midi_process_messages(hardware.midi_usb)
        midi_process_messages(hardware.midi_uart)
        await asyncio.sleep(hardware.TASK_SLEEP)

## Touch Keyboard Interface

def ttp_press(i:int) -> None:
    notenum = keyboard.root + i
    if settings.keyboard_touch:
        keyboard.append(notenum)
    if settings.midi_touch_out:
        msg = NoteOn(notenum)
        hardware.midi_uart.send(msg)
        hardware.midi_usb.send(msg)
hardware.ttp.on_press = ttp_press

def ttp_release(i:int) -> None:
    notenum = keyboard.root + i
    if settings.keyboard_touch:
        keyboard.remove(notenum)
    if settings.midi_touch_out:
        msg = NoteOff(notenum)
        hardware.midi_uart.send(msg)
        hardware.midi_usb.send(msg)
hardware.ttp.on_release = ttp_release

async def touch_task() -> None:
    while True:
        hardware.ttp.update()
        await asyncio.sleep(hardware.TASK_SLEEP)

## Character LCD Menu

sample_files = list(filter(lambda filename: filename.endswith(".wav"), os.listdir(DIR)))
if not sample_files:
    hardware.lcd.cursor_position(0, 1)
    hardware.lcd.message = "No samples!"
    time.sleep(2)
    # Reset back to launcher
    menu.load_launcher()

def load_sample(index:int) -> None:
    for voice in voices:
        voice.waveform = None
    gc.collect()
    path = DIR + "/" + sample_files[index % len(sample_files)]
    waveform, sample_rate = synthwaveform.from_wav(path)
    for voice in voices:
        voice.waveform = waveform
        voice.sample_rate = sample_rate

lcd_menu = synthmenu.character_lcd.Menu(hardware.lcd, hardware.COLUMNS, hardware.ROWS, "Menu", (
    synthmenu.Group("Patch", (
        patch := synthmenu.Number(
            title="Index",
            default=0,
            step=1,
            minimum=0,
            maximum=15,
            loop=True,
            decimals=0,
            on_update=lambda value, item: menu.load_patch(lcd_menu, item, value, 'sampler'),
        ),
        synthmenu.String("Name"),
        synthmenu.Action("Save", lambda: menu.save_patch(lcd_menu, patch.value, 'sampler')),
    )),
    synthmenu.Group("Audio", (
        synthmenu.Percentage(
            title="Level",
            default=1.0,
            on_update=lambda value, item: menu.set_attribute(mixer.voice, 'level', value),
        ),
    )),
    synthmenu.Group("Keys", (
        synthmenu.List(
            title="Priority",
            items=("High", "Low", "Last"),
            on_update=lambda value, item: menu.set_attribute(keyboard, 'mode', value),
        ),
        synthmenu.Bool(
            title="Monophonic",
            on_update=lambda value, item: menu.set_attribute(keyboard, 'max_voices', 1 if value else VOICES),
        ),
        menu.get_arpeggiator_group(keyboard.arpeggiator),
    )),
    synthmenu.Group("Voice", (
        synthmenu.Waveform(
            title="Sample",
            items=tuple([
                (menu.format_name(filename[:-4]), lambda filename=filename: synthwaveform.from_wav(DIR + "/" + filename)[0])
                for filename in sample_files
            ]),
            on_waveform_update=lambda value, item: load_sample(value),
            on_loop_start_update=lambda value, item: menu.set_attribute(voices, 'waveform_loop', (value, voices[0].waveform_loop[1])),
            on_loop_end_update=lambda value, item: menu.set_attribute(voices, 'waveform_loop', (voices[0].waveform_loop[0], value)),
        ),
        synthmenu.Bool(
            title="Looping",
            default=True,
            on_update=lambda value, item: menu.set_attribute(voices, 'looping', value),
        ),
        synthmenu.Mix(
            title="Mix",
            on_level_update=lambda value, item: menu.set_attribute(voices, 'amplitude', value),
            on_pan_update=lambda value, item: menu.set_attribute(voices, 'pan', value),
        ),
        synthmenu.Tune(
            title="Tuning",
            on_coarse_update=lambda value, item: menu.set_attribute(voices, 'coarse_tune', value),
            on_fine_update=lambda value, item: menu.set_attribute(voices, 'fine_tune', value),
            on_glide_update=lambda value, item: menu.set_attribute(voices, 'glide', value),
            on_bend_update=lambda value, item: menu.set_attribute(voices, 'bend_amount', value),
            on_slew_update=lambda value, item: menu.set_attribute(voices, 'pitch_slew', value),
            on_slew_time_update=lambda value, item: menu.set_attribute(voices, 'pitch_slew_time', value),
        ),
        synthmenu.ADSREnvelope(
            title="Envelope",
            on_attack_time_update=lambda value, item: menu.set_attribute(voices, 'attack_time', value),
            on_attack_level_update=lambda value, item: menu.set_attribute(voices, 'attack_level', value),
            on_decay_time_update=lambda value, item: menu.set_attribute(voices, 'decay_time', value),
            on_sustain_level_update=lambda value, item: menu.set_attribute(voices, 'sustain_level', value),
            on_release_time_update=lambda value, item: menu.set_attribute(voices, 'release_time', value),
        ),
        synthmenu.Number(
            title="Velocity",
            on_update=lambda value, item: menu.set_attribute(voices, 'velocity_amount', value),
        ),
        synthmenu.Group("Filter", (
            synthmenu.List(
                title="Type",
                items=("Low Pass", "High Pass", "Band Pass"),
                on_update=lambda value, item: menu.set_attribute(voices, 'filter_type', value),
            ),
            synthmenu.Number(
                title="Frequency",
                default=1.0,
                step=0.01,
                minimum=0,
                maximum=min(20000, hardware.SAMPLE_RATE / 2),
                smoothing=3.0,
                decimals=0,
                append="hz",
                on_update=lambda value, item: menu.set_attribute(voices, 'filter_frequency', value),
            ),
            synthmenu.Number(
                title="Resonance",
                default=0.0,
                step=0.01,
                minimum=0.7071067811865475,
                maximum=2.0,
                smoothing=2.0,
                decimals=3,
                on_update=lambda value, item: menu.set_attribute(voices, 'filter_resonance', value),
            ),
            synthmenu.Group("Envelope", (
                synthmenu.Time(
                    title="Attack",
                    on_update=lambda value, item: menu.set_attribute(voices, 'filter_attack_time', value),
                ),
                synthmenu.Number(
                    title="Amount",
                    default=0,
                    step=10,
                    minimum=min(20000, hardware.SAMPLE_RATE / 2) / -2,
                    maximum=min(20000, hardware.SAMPLE_RATE / 2) / 2,
                    append="hz",
                    on_update=lambda value, item: menu.set_attribute(voices, 'filter_amount', value),
                ),
                synthmenu.Time(
                    title="Release",
                    on_update=lambda value, item: menu.set_attribute(voices, 'filter_release_time', value),
                ),
            )),
            synthmenu.Group("LFO", (
                synthmenu.Number(
                    "Depth",
                    default=0.0,
                    step=0.01,
                    minimum=0,
                    maximum=min(20000, hardware.SAMPLE_RATE / 2) / 2,
                    smoothing=3.0,
                    decimals=0,
                    append="hz",
                    on_update=lambda value, item: menu.set_attribute(voices, 'filter_depth', value),
                ),
                synthmenu.Number(
                    "Rate",
                    step=0.01,
                    maximum=32.0,
                    smoothing=2.0,
                    append="hz",
                    on_update=lambda value, item: menu.set_attribute(voices, 'filter_rate', value),
                ),
            )),
        )),
        synthmenu.Group("Mod", (
            synthmenu.Group("Tremolo", (
                synthmenu.Percentage(
                    title="Depth",
                    on_update=lambda value, item: menu.set_attribute(voices, 'tremolo_depth', value / 2),
                ),
                synthmenu.Number(
                    title="Rate",
                    step=0.01,
                    maximum=32.0,
                    smoothing=2.0,
                    append="hz",
                    on_update=lambda value, item: menu.set_attribute(voices, 'tremolo_rate', value),
                ),
            )),
            synthmenu.Group("Vibrato", (
                synthmenu.Number(
                    title="Depth",
                    default=0,
                    step=10,
                    minimum=0,
                    maximum=600,
                    decimals=0,
                    append=" cents",
                    on_update=lambda value, item: menu.set_attribute(voices, 'vibrato_depth', value / 1200),
                ),
                synthmenu.Number(
                    title="Rate",
                    step=0.01,
                    maximum=32.0,
                    smoothing=2.0,
                    append="hz",
                    on_update=lambda value, item: menu.set_attribute(voices, 'vibrato_rate', value),
                ),
            )),
            synthmenu.Group("Pan", (
                synthmenu.Percentage(
                    title="Depth",
                    on_update=lambda value, item: menu.set_attribute(voices, 'pan_depth', value),
                ),
                synthmenu.Number(
                    title="Rate",
                    step=0.01,
                    maximum=32.0,
                    smoothing=2.0,
                    append="hz",
                    on_update=lambda value, item: menu.set_attribute(voices, 'pan_rate', value),
                ),
            )),
        )),
    )),
    synthmenu.Action("Exit", menu.load_launcher),
))

# Perform a full update which will synchronize oscillator properties

lcd_menu.do_update()

## Controls

async def controls_task():
    while True:
        menu.handle_controls(lcd_menu)
        await asyncio.sleep(hardware.TASK_SLEEP)

## Asyncio loop

async def main():
    await asyncio.gather(
        asyncio.create_task(keyboard.arpeggiator.update()),
        asyncio.create_task(voice_task()),
        asyncio.create_task(touch_task()),
        asyncio.create_task(midi_task()),
        asyncio.create_task(controls_task()),
    )

asyncio.run(main())
