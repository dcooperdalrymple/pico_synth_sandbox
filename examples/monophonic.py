# pico_synth_sandbox - Monophonic Synth Example
# 2023 Cooper Dalrymple - me@dcdalrymple.com
# GPL v3 License

import pico_synth_sandbox.tasks
from pico_synth_sandbox.board import get_board
from pico_synth_sandbox.display import Display
from pico_synth_sandbox.encoder import Encoder
from pico_synth_sandbox.keyboard import get_keyboard_driver
from pico_synth_sandbox.audio import get_audio_driver
from pico_synth_sandbox.synth import Synth
from pico_synth_sandbox.voice.oscillator import Oscillator
import pico_synth_sandbox.waveform as waveform

board = get_board()

display = Display(board)
display.write("PicoSynthSandbox", (0,0))
display.write("Loading...", (0,1))
display.force_update()

note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

audio = get_audio_driver(board)
synth = Synth(audio)

osc1 = Oscillator()
osc1.set_glide(1.0)
osc1.set_waveform(waveform.get_sine())
osc1.set_pan_rate(0.5)
osc1.set_pan_depth(0.1)
osc1.set_vibrato_rate(4.0)
osc1.set_vibrato_depth(0.1)
osc1.set_envelope(
    attack_time=0.1,
    attack_level=1.0,
    decay_time=0.5,
    sustain_level=0.25,
    release_time=1.0
)
osc1.set_filter(
    frequency=0.1,
    resonance=0.5,
    envelope_attack_time=0.5,
    envelope_release_time=1.0,
    envelope_amount=0.25,
    lfo_rate=0.1,
    lfo_depth=0.25,
    synth=synth
)
osc1.set_coarse_tune(-1.0)
synth.add_voice(osc1)

osc2 = Oscillator()
osc2.set_glide(0.25)
osc2.set_waveform(waveform.get_sine())
osc2.set_pan_rate(2.0)
osc2.set_pan_depth(0.5)
osc2.set_vibrato_rate(1.0)
osc2.set_vibrato_depth(0.05)
osc2.set_envelope(
    attack_time=1.0,
    attack_level=1.0,
    decay_time=2.0,
    sustain_level=0.0,
    release_time=2.0
)
osc2.set_filter(
    frequency=0.5,
    resonance=0.1,
    envelope_attack_time=2.0,
    envelope_release_time=2.0,
    envelope_amount=0.15,
    synth=synth
)
osc2.set_coarse_tune(2.0)
osc2.set_level(0.5)
synth.add_voice(osc2)

keyboard = get_keyboard_driver(board, max_voices=1)

def press(voicenum, notenum, velocity, keynum=None):
    for voice in synth.voices:
        synth.press(voice, notenum, velocity)
    display.write("{:02d} {}".format(notenum, note_names[notenum % 12]), (0,1), 6)
keyboard.set_voice_press(press)

def release(voicenum, notenum, keynum=None):
    if not keyboard.has_notes():
        synth.release()
        display.write("", (0, 1), 6)
keyboard.set_voice_release(release)

tune = 0
encoder = Encoder(board)
def update_tuning():
    global tune
    osc1.set_coarse_tune(tune / 12.0)
    osc2.set_coarse_tune(tune / 12.0 + 2.0)
    display.write("{:02d}".format(tune), (6,1), 6, True)
def increment():
    global tune
    if tune < 48:
        tune += 1
    update_tuning()
def decrement():
    global tune
    if tune > -48:
        tune -= 1
    update_tuning()
encoder.set_increment(increment)
encoder.set_decrement(decrement)

display.write("", (0,1), 6)
update_tuning()

pico_synth_sandbox.tasks.run()
