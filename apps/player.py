# SPDX-FileCopyrightText: Copyright (c) 2024 Cooper Dalrymple
#
# SPDX-License-Identifier: Unlicense

import audiomixer

import synthmenu.character_lcd

import asyncio

from adafruit_midi.note_on import NoteOn
from adafruit_midi.note_off import NoteOff
from adafruit_midi.control_change import ControlChange
from adafruit_midi.pitch_bend import PitchBend
from adafruit_midi.program_change import ProgramChange
from adafruit_midi.channel_pressure import ChannelPressure
from adafruit_midi.polyphonic_key_pressure import PolyphonicKeyPressure
from adafruit_midi.midi_message import MIDIMessage

import umidiparser
import audiocore
import time

import hardware
import menu
import os

DIR = "/sd/songs"
try:
    os.stat(DIR)
except OSError:
    DIR = "/songs"

## Audio Output + Synthesizer

hardware.audio.stop()

## Get list of songs

songs = list(filter(lambda filename: filename.endswith(".wav") or filename.endswith(".mid"), os.listdir(DIR)))

# Remove extensions
for i in range(len(songs)):
    songs[i] = songs[i][:songs[i].rfind('.')]

# Remove duplicates and sort alphabetically
songs = list(sorted(set(songs)))

if not songs:
    menu.write_message("No songs!", True)
    menu.load_launcher()

## Playback Controller

class Player():
    def __init__(self):
        self._midi_file = None
        self._midi_track = None
        self._wav_file = None
        self._mixer = None
        self._level = 1.0
        self._start_time = None
        self._midi_playing = False

    def load(self, index:int) -> None:
        global songs
        name = songs[index % len(songs)]

        # Stop any currently playing tracks
        self.stop()

        # Load Midi
        try:
            midi_file = "{:s}/{:s}.mid".format(DIR, name)
            os.stat(midi_file)
        except OSError:
            midi_file = None
        else:
            self._midi_file = umidiparser.MidiFile(midi_file)

        # Load Audio
        try:
            audio_file = "{:s}/{:s}.wav".format(DIR, name)
            os.stat(audio_file)
        except OSError:
            audio_file = None
        else:
            self._wav_file = audiocore.WaveFile(audio_file)
            self._mixer = audiomixer.Mixer(
                voice_count=1,
                channel_count=self._wav_file.channel_count,
                sample_rate=self._wav_file.sample_rate,
                buffer_size=hardware.BUFFER_SIZE,
                bits_per_sample=self._wav_file.bits_per_sample,
                samples_signed=True,
            )
            self._mixer.voice[0].level = self.level
            hardware.audio.play(self._mixer)

    def play(self) -> None:
        if self._mixer:
            self._mixer.voice[0].play(self._wav_file)

        if self._midi_file:
            self._midi_track = self._midi_file.play(sleep=False)

        self._start_time = time.monotonic_ns() // 1000

    def stop(self) -> None:
        hardware.audio.stop()
        self._start_time = None

        if self._wav_file:
            self._wav_file.deinit()
            self._wav_file = None
        
        if self._mixer:
            self._mixer.deinit()
            self._mixer = None
        
        self._midi_playing = False

    def toggle(self) -> None:
        if self.playing:
            self.stop()
        else:
            self.play()

    @property
    def level(self) -> float:
        return self._level

    @level.setter
    def level(self, value:float) -> None:
        self._level = value
        if self._mixer:
            self._mixer.voice[0].level = value

    @property
    def playing(self) -> bool:
        return self._start_time and ((self._mixer and self._mixer.voice[0].playing) or self._midi_playing)

    def _send(self, msg:MIDIMessage) -> None:
        hardware.midi_usb.send(msg)
        hardware.midi_uart.send(msg)
        
    async def update(self) -> None:
        while True:
            if self._start_time and self._midi_track:
                midi_time = 0
                for event in self._midi_track:
                    midi_time += event.delta_us
                    current_time = time.monotonic_ns() // 1000 - self._start_time
                    delay = midi_time - current_time
                    if delay > 0:
                        await asyncio.sleep(delay / 1000000)
                    
                    if not self._midi_playing:
                        break
                    
                    if event.status == umidiparser.NOTE_ON:
                        self._send(NoteOn(event.note, event.velocity, event.channel))
                    elif event.status == umidiparser.NOTE_OFF:
                        self._send(NoteOff(event.note, 0, event.channel))
                    elif event.status == umidiparser.POLYTOUCH:
                        self._send(PolyphonicKeyPressure(event.note, event.value, event.channel))
                    elif event.status == umidiparser.CONTROL_CHANGE:
                        self._send(ControlChange(event.control, event.value, event.channel))
                    elif event.status == umidiparser.PROGRAM_CHANGE:
                        self._send(ProgramChange(event.program, event.channel))
                    elif event.status == umidiparser.AFTERTOUCH:
                        self._send(ChannelPressure(event.value, event.channel))
                    elif event.state == umidiparser.PITCHWHEEL:
                        self._send(PitchBend(event.pitch, event.channel))
                    # Ignore unrecognized events

                self._midi_playing = False

            if self._start_time and self._mixer and not self._mixer.voice[0].playing:
                self.stop()
            
            await asyncio.sleep(hardware.TASK_SLEEP)

player = Player()

## Character LCD Menu

lcd_menu = synthmenu.character_lcd.Menu(hardware.lcd, hardware.COLUMNS, hardware.ROWS, "Menu", (
    synthmenu.Percentage(
        title="Volume",
        default=1.0,
        on_update=lambda value, item: menu.set_attribute(player, 'level', value),
    ),
    synthmenu.List(
        title="Song",
        items=tuple([menu.format_name(song) for song in songs]),
        on_update=lambda value, item: player.load(value),
    ),
    synthmenu.Action(lambda item: "Stop" if player.playing else "Play", player.toggle),
    synthmenu.Action("Exit", menu.load_launcher)
))

# Load first song
player.load(0)

## Controls

async def controls_task():
    while True:
        menu.handle_controls(lcd_menu)
        await asyncio.sleep(hardware.TASK_SLEEP)

## Asyncio loop

async def main():
    await asyncio.gather(
        asyncio.create_task(player.update()),
        asyncio.create_task(controls_task()),
    )

asyncio.run(main())
