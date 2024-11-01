# PicoSynth Sandbox
Firmware running on CircuitPython for pico_synth_sandbox device capable of dynamically loading multiple applications to act as a synthesizer, drum machine, sampler, and more.

## Hardware

This project is designed for the pico_synth_sandbox Rev2 hardware out of the box, but the `/hardware.py` file can be modified to support other platforms.

The Raspberry Pi Pico (RP2040) and Raspberry Pi Pico 2 (RP2350) microcontrollers are currently supported, but certain properties of each application will be modified for performance considerations.

See the hardware repository for schematics and gerber files: https://github.com/dcooperdalrymple/pico_synth_sandbox-hardware.

## Apps

Applications are stored in `/apps` within the device's flash storage as a stand-alone python script which uses shared top-level script assets to interface with the hardware.

### synthesizer.py

- 6 voices with 2 independent oscillators each (when using RP2350)
- Monophonic mode with x12 operation
- Amplitude and filter envelopes
- Modulation LFOs for amplitude (tremolo), filter, pitch (vibrato), and stereo panning
- Delay and chorus effects (RP2350 with CircuitPython 9.2.0+)
- Arpeggiator

### sampler.py

- Automatic pitch detection and multiple tuning options
- Polyphonic up to 12 keys (when using RP2350)
- Amplitude and filter envelopes
- Modulation LFOs for amplitude (tremolo), filter, pitch (vibrato), and stereo panning
- Arpeggiator
- WAV playback (16-bit signed)

### drum_machine.py

- Dynamically generated drum sounds using synthio
- 8 different voices: Kick, Snare, Closed and Open Hat, Floor, Mid and Rack Tom, and Ride

### player.py

- Load WAV and MID (type 0) files from SD card associated by name
- Multiple supported sample and bit rates

## Examples

Creating your own app for the pico_synth_sandbox platform is easy! Some of the apps are provided as demonstrations of how to set up your own custom programs.

### simple.py

A basic synthesizer example using a simple menu system and touch keyboard input.
