# SPDX-FileCopyrightText: Copyright (c) 2024 Cooper Dalrymple
#
# SPDX-License-Identifier: Unlicense

import audiomixer
import synthio
import asyncio

from adafruit_midi.note_on import NoteOn
from adafruit_midi.note_off import NoteOff

import synthkeyboard
import synthvoice.percussive

import hardware
import menu

hardware.init()

hardware.lcd.clear()
hardware.lcd.cursor = True
hardware.lcd.blink = False
hardware.lcd.home()

## Audio

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
mixer.voice[0].level = 0.05 # Fix clipping on amp

## Global parameters
voice=0
bpm=120
alt_enc=False
alt_key=False

## Voices

voices = [
    synthvoice.percussive.Kick(synth),
    synthvoice.percussive.Snare(synth),
    synthvoice.percussive.ClosedHat(synth),
    synthvoice.percussive.OpenHat(synth),
    synthvoice.percussive.FloorTom(synth),
    synthvoice.percussive.MidTom(synth),
    synthvoice.percussive.HighTom(synth),
    synthvoice.percussive.Ride(synth),
]

# No update task required

## Sequencer

sequencer = synthkeyboard.Sequencer(
    length=16,
    tracks=len(voices),
    bpm=120
)

sequencer.on_step = lambda pos: hardware.lcd.cursor_position(pos, 1)

def sequencer_press(notenum:int, velocity:float) -> None:
    voices[(notenum - 1) % len(voices)].press(velocity)

    msg = NoteOn(notenum)
    hardware.midi_uart.send(msg)
    hardware.midi_usb.send(msg)
sequencer.on_press = sequencer_press

def sequencer_release(notenum):
    if (notenum - 1) % len(voices) == 3: # Closed Hat
        voices[4].release() # Force release Open Hat
    synth.release((notenum - 1) % len(voices))

    # Send midi note off
    msg = NoteOff(notenum)
    hardware.midi_uart.send(msg)
    hardware.midi_usb.send(msg)
sequencer.on_release = sequencer_release

def update_display():
    hardware.lcd.cursor_position(0, 0)
    hardware.lcd.message = "{:<11s}{:s} {:>3d}".format(
        voices[voice].__qualname__[:11],
        ">" if alt_enc else "<",
        bpm
    )
    hardware.lcd.cursor_position(0, 1)
    hardware.lcd.message = "".join(["*" if sequencer.has_note(i, voice) else " " for i in range(sequencer.length)])

## Touch

def ttp_press(position:int) -> None:
    global voice

    position = position % sequencer.length
    hardware.lcd.cursor_position(position, 1)
    if not sequencer.has_note(
        position=position,
        track=voice,
    ):
        sequencer.set_note(
            position=position,
            notenum=voice+1,
            velocity=1.0,
            track=voice,
        )
        hardware.lcd.message = "*"
    else:
        sequencer.remove_note(
            position=position,
            track=voice
        )
        hardware.lcd.message = " "
hardware.ttp.on_press = ttp_press

async def touch_task() -> None:
    while True:
        hardware.ttp.update()
        await asyncio.sleep(hardware.TASK_SLEEP)

## Controls

def update_bpm():
    global bpm
    sequencer.bpm = bpm
    hardware.lcd.cursor_position(13, 0)
    hardware.lcd.message = "{:>3d}".format(bpm)
def update_selected():
    global alt_enc
    hardware.lcd.cursor_position(11, 0)
    hardware.lcd.message = ">" if alt_enc else "<"
def increment_voice():
    global voice, alt_enc
    if alt_enc:
        alt_enc = False
        update_selected()
    voice = (voice + 1) % sequencer.tracks
    update_display()
def decrement_voice():
    global voice, alt_enc
    if alt_enc:
        alt_enc = False
        update_selected()
    voice = (voice - 1) % sequencer.tracks
    update_display()
def increment_bpm():
    global bpm, alt_enc
    if not alt_enc:
        alt_enc = True
        update_selected()
    if bpm < 200:
        bpm += 1
        update_bpm()
def decrement_bpm():
    global bpm, alt_enc
    if not alt_enc:
        alt_enc = True
        update_selected()
    if bpm > 50:
        bpm -= 1
        update_bpm()
def toggle_sequencer():
    sequencer.active = not sequencer.active
def clear_track():
    for i in range(sequencer.length):
        sequencer.remove_note(
            position=i,
            track=voice,
        )
    update_display()

update_display()

async def update_controls() -> None:
    encoder_position = [encoder.position for encoder in hardware.encoders]
    while True:
        for i, encoder in enumerate(hardware.encoders):
            position = encoder.position
            if position > encoder_position[i]:
                for j in range(position - encoder_position[i]):
                    increment_voice() if not i else increment_bpm()
            elif position < encoder_position[i]:
                for j in range(encoder_position[i] - position):
                    decrement_voice() if not i else decrement_bpm()
            encoder_position[i] = position

            hardware.buttons[i].update()

            if hardware.buttons[i].rose and hardware.buttons[i].last_duration < 0.5: # short press
                if i:
                    toggle_sequencer()
            elif hardware.buttons[i].rose: # long press
                if not i:
                    clear_track()
                else:
                    menu.load_launcher()

        await asyncio.sleep(hardware.TASK_SLEEP)

async def main():
    await asyncio.gather(
        asyncio.create_task(sequencer.update()),
        asyncio.create_task(touch_task()),
        asyncio.create_task(update_controls()),
    )

asyncio.run(main())
