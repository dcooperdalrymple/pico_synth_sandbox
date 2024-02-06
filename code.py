# pico_synth_sandbox-synthesizer
# 2024 Cooper Dalrymple - me@dcdalrymple.com
# GPL v3 License

import time
import pico_synth_sandbox.tasks
from pico_synth_sandbox.board import get_board
from pico_synth_sandbox.audio import get_audio_driver
from pico_synth_sandbox.display import Display
from pico_synth_sandbox.synth import Synth
from pico_synth_sandbox.voice.oscillator import Oscillator
from pico_synth_sandbox.keyboard import get_keyboard_driver
from pico_synth_sandbox.arpeggiator import Arpeggiator
from pico_synth_sandbox.midi import Midi
from pico_synth_sandbox.display import Display
from pico_synth_sandbox.encoder import Encoder
from pico_synth_sandbox.menu import Menu, MenuGroup, OscillatorMenuGroup, NumberMenuItem, BooleanMenuItem, IntMenuItem, BarMenuItem, ListMenuItem

# Constants
OSCILLATORS = 2
VOICES = 4
MAX_PATCHES = 16

VOICE_POLY = 0
VOICE_MONO = 1
VOICE_MONO_ALL = 2
voice_type = VOICE_POLY

# Initialize hardware components
board = get_board()

audio = get_audio_driver(board)
audio.mute()

display = Display(board)
display.clear()
display.hide_cursor()
display.write("PicoSynthSandbox", (0,0))
display.write("Loading...", (0,1))
display.force_update()

keyboard = get_keyboard_driver(board, max_voices=VOICES)
arpeggiator = Arpeggiator()
keyboard.set_arpeggiator(arpeggiator)

midi = Midi(board)

if board.num_encoders() == 1:
    encoders = (Encoder(board, 0),)
elif board.num_encoders() > 1:
    encoders = (Encoder(board, 0), Encoder(board, 1))

# Initialize Synthesizer
synth = Synth(audio)
oscillators = (tuple([Oscillator() for i in range(VOICES)]), tuple([Oscillator() for i in range(VOICES)]))
for i in range(VOICES):
    for j in range(OSCILLATORS):
        synth.add_voice(oscillators[j][i])

# Menu and Patch System
class PatchMenuItem(IntMenuItem):
    def __init__(self, maximum:int=16, update:function=None):
        IntMenuItem.__init__(self, "Patch", maximum=maximum, loop=True, update=update)
    def set(self, value:float, force:bool=False):
        if force:
            NumberMenuItem.set(self, value)
    def enable(self, display:Display):
        self._group = ""
        NumberMenuItem.enable(self, display)
patch_item = PatchMenuItem(MAX_PATCHES)

def set_voice_type(value):
    global voice_type
    voice_type = value
    if voice_type == VOICE_POLY:
        keyboard.set_max_voices(VOICES)
    else:
        keyboard.set_max_voices(1)

menu = Menu((
    patch_item,
    MenuGroup((
        IntMenuItem("Channel", maximum=16, update=lambda value : midi.set_channel(int(value))),
        BooleanMenuItem("Thru", update=midi.set_thru),
    ), "MIDI"),
    MenuGroup((
        BarMenuItem("Level", initial=1.0, update=audio.set_level),
    ), "Audio"),
    MenuGroup((
        ListMenuItem(("High", "Low", "Last"), "Priority", update=keyboard.set_mode),
        ListMenuItem(("Polyphonic", "Monophonic", "Monophonic x{:d}".format(VOICES)), "Voice", initial=voice_type, update=set_voice_type),
    ), "Keys"),
    MenuGroup((
        BooleanMenuItem("Enabled", update=arpeggiator.set_enabled),
        ListMenuItem(("Up", "Down", "Up Down", "Down Up", "Played", "Random"), "Mode", update=arpeggiator.set_mode),
        NumberMenuItem("Octaves", step=1, initial=0, minimum=-3, maximum=3, update=arpeggiator.set_octaves),
        NumberMenuItem("BPM", step=1, initial=120, minimum=60, maximum=240, update=arpeggiator.set_bpm),
        BarMenuItem("Gate", step=0.025, initial=0.3, update=arpeggiator.set_gate),
        ListMenuItem(("Whole", "Half", "Quarter", "Dotted Quarter", "Eighth", "Triplet", "Sixteenth", "Thirty-Second"), "Steps", initial=2, update=lambda value : arpeggiator.set_steps(Arpeggiator.STEPS[value])),
    ), "Arp"),
    OscillatorMenuGroup(oscillators[0], "Osc1"),
    OscillatorMenuGroup(oscillators[1], "Osc2"),
), "synthesizer")
default_patch = menu.get()

def get_patch_file(value=None):
    if value is None:
        value = patch_item.get()
    return "{:s}-{:d}".format(menu.get_group(), int(value))

def read_patch(value=None):
    if not menu.read(get_patch_file(value)):
        menu.set(default_patch)
patch_item.set_update(read_patch)

def write_patch():
    audio.mute()
    pico_synth_sandbox.tasks.pause()
    display.clear()
    display.write("Saving...")
    display.force_update()
    menu.write(get_patch_file())
    display.clear()
    display.write("Complete!")
    display.force_update()
    time.sleep(0.5)
    pico_synth_sandbox.tasks.resume()
    menu.draw(display)
    menu.enable(display)
    audio.unmute()

selected = False
def update_cursor_position(value=None):
    global selected
    if not value is None:
        if value == selected:
            return
        selected = value
    if not selected:
        display.set_cursor_position(0,0)
    else:
        display.set_cursor_position(menu.get_cursor_position())

def menu_reset():
    update_cursor_position(True)
    if menu.reset():
        menu.draw(display)

def menu_next_group():
    update_cursor_position(False)
    menu.next(display, force=True)

def menu_increment_value():
    update_cursor_position(True)
    if menu.increment():
        menu.draw(display)
def menu_decrement_value():
    update_cursor_position(True)
    if menu.decrement():
        menu.draw(display)

def menu_increment_item():
    update_cursor_position(False)
    menu.next(display)
def menu_decrement_item():
    update_cursor_position(False)
    menu.previous(display)

if len(encoders) == 1:

    def encoder_toggle():
        global selected
        selected = not selected
        update_cursor_position()
    encoders[0].set_click(encoder_toggle)

    def encoder_double_click():
        global selected
        if selected:
            menu_reset()
        else:
            menu_next_group()
    encoders[0].set_double_click(encoder_double_click)

    def encoder_increment():
        global selected
        if selected:
            menu_increment_value()
        else:
            menu_increment_item()
    encoders[0].set_increment(encoder_increment)

    def encoder_decrement():
        global selected
        if selected:
            menu_decrement_value()
        else:
            menu_decrement_item()
    encoders[0].set_decrement(encoder_decrement)
    
    encoders[0].set_long_press(write_patch)

else:

    encoders[0].set_double_click(menu_next_group)
    encoders[0].set_long_press(write_patch)
    encoders[0].set_increment(menu_increment_item)
    encoders[0].set_decrement(menu_decrement_item)

    encoders[1].set_long_press(menu_reset)
    encoders[1].set_increment(menu_increment_value)
    encoders[1].set_decrement(menu_decrement_value)

# Keyboard Setup
def voice_press(index, notenum, velocity, keynum=None):
    global voice_type
    if voice_type == VOICE_MONO:
        for i in range(OSCILLATORS):
            synth.press(i, notenum, velocity)
    elif voice_type == VOICE_MONO_ALL:
        for voice in synth.voices:
            synth.press(voice, notenum, velocity)
    else: # voice_type == VOICE_POLY:
        for i in range(OSCILLATORS):
            synth.press(index + i, notenum, velocity)
keyboard.set_voice_press(voice_press)

def voice_release(index, notenum, keynum=None):
    if (voice_type == VOICE_MONO or voice_type == VOICE_MONO_ALL) and not keyboard.has_notes():
        synth.release()
    else: # voice_type == VOICE_POLY:
        for i in range(OSCILLATORS):
            synth.release(index + i)
keyboard.set_voice_release(voice_release)

def key_press(keynum, notenum, velocity):
    midi.send_note_on(notenum, velocity)
keyboard.set_key_press(key_press)

def key_release(keynum, notenum):
    midi.send_note_off(notenum)
keyboard.set_key_release(key_release)

# Midi Implementation
def control_change(control, value):
    if control == 64: # Sustain
        keyboard.set_sustain(value)
midi.set_control_change(control_change)

def pitch_bend(value):
    for voice in synth.voices:
        voice.set_pitch_bend(value)
midi.set_pitch_bend(pitch_bend)

def note_on(notenum, velocity):
    # Add to keyboard for processing
    keyboard.append(notenum, velocity)
midi.set_note_on(note_on)

def note_off(notenum):
    keyboard.remove(notenum)
midi.set_note_off(note_off)

def program_change(patch):
    patch_item.set(patch, True)
midi.set_program_change(program_change)

# Load Patch 0
read_patch()

display.clear()
display.set_cursor_blink(True)
update_cursor_position()
menu.draw(display)
menu.enable(display)

audio.unmute()

pico_synth_sandbox.tasks.run()
