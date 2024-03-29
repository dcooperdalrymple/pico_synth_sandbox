# pico_synth_sandbox - Drum Sequencer Example
# 2023 Cooper Dalrymple - me@dcdalrymple.com
# GPL v3 License

import pico_synth_sandbox.tasks
from pico_synth_sandbox.board import get_board
from pico_synth_sandbox.display import Display
from pico_synth_sandbox.encoder import Encoder
from pico_synth_sandbox.keyboard import get_keyboard_driver
from pico_synth_sandbox.sequencer import Sequencer
from pico_synth_sandbox.audio import get_audio_driver
from pico_synth_sandbox.synth import Synth
from pico_synth_sandbox.voice.drum import Kick, Snare, ClosedHat, OpenHat

board = get_board()

display = Display(board)
display.write("PicoSynthSandbox", (0,0))
display.write("Loading...", (0,1))
display.force_update()
display.set_cursor_enabled(True)
display.set_cursor_blink(False)

# Local parameters
voice=0
bpm=120
alt_enc=False
alt_key=False

audio = get_audio_driver(board)
synth = Synth(audio)
synth.add_voices([
    Kick(),
    Snare(),
    ClosedHat(),
    OpenHat()
])

sequencer = Sequencer(
    tracks=4,
    bpm=120
)
def seq_step(position):
    display.set_cursor_position(position, 1)
def seq_press(notenum, velocity):
    synth.press((notenum - 1) % len(synth.voices))
def seq_release(notenum):
    if (notenum - 1) % len(synth.voices) == 2: # Closed Hat
        synth.release(3, True) # Force release Open Hat
    synth.release((notenum - 1) % len(synth.voices))
sequencer.set_step(seq_step)
sequencer.set_press(seq_press)
sequencer.set_release(seq_release)

def update_display():
    display.write(synth.voices[voice].__qualname__, (0, 0), 11)
    display.write(">" if alt_enc else "<", (11,0), 1)
    display.write(("^" if alt_key else "-") if len(keyboard.keys) < 16 else " ", (12,0), 1)
    display.write(str(bpm), (13,0), 3, True)
    line = ""
    for i in range(sequencer.get_length()):
        line += "*" if sequencer.has_note(i, voice) else "_"
    display.write(line, (0,1))

keyboard = get_keyboard_driver(board, max_voices=0)
def key_press(keynum, notenum, velocity):
    global sequencer
    
    position = keynum
    if len(keyboard.keys) < 16:
        global alt_key
        if keynum == 11:
            alt_key = not alt_key
            display.write("^" if alt_key else "-", (12,0), 1)
            return
        elif keynum < 8:
            position = keynum + (8 if alt_key else 0)

    position = position % sequencer.get_length()
    if not sequencer.has_note(
        position=position,
        track=voice
    ):
        sequencer.set_note(
            position=position,
            notenum=voice+1,
            velocity=1.0,
            track=voice
        )
        display.write("*", (position,1), 1)
    else:
        sequencer.remove_note(
            position=position,
            track=voice
        )
        display.write("_", (position,1), 1)
keyboard.set_key_press(key_press)

def update_alt_enc():
    global alt_enc
    display.write(">" if alt_enc else "<", (11,0), 1)

def update_bpm():
    global bpm
    sequencer.set_bpm(bpm)
    display.write(str(bpm), (13,0), 3, True)

def increment_track():
    global alt_enc, voice
    if alt_enc:
        alt_enc = False
        update_alt_enc()
    voice = (voice + 1) % sequencer.get_tracks()
    update_display()
def decrement_track():
    global alt_enc, voice
    if alt_enc:
        alt_enc = False
        update_alt_enc()
    voice = (voice - 1) % sequencer.get_tracks()
    update_display()

def increment_bpm():
    global alt_enc, bpm
    if not alt_enc:
        alt_enc = True
        update_alt_enc()
    if bpm < 200:
        bpm += 1
    update_bpm()
def decrement_bpm():
    global alt_enc, bpm
    if not alt_enc:
        alt_enc = True
        update_alt_enc()
    if bpm > 50:
        bpm -= 1
    update_bpm()

if board.num_encoders() == 1:

    encoder = Encoder(board)

    def increment():
        global alt_enc
        if not alt_enc:
            increment_track()
        else:
            increment_bpm()
    encoder.set_increment(increment)

    def decrement():
        global alt_enc
        if not alt_enc:
            decrement_track()
        else:
            decrement_bpm()
    encoder.set_decrement(decrement)

    def click():
        global alt_enc
        alt_enc = not alt_enc
        update_alt_enc()
    encoder.set_click(click)

elif board.num_encoders() > 1:

    encoder1 = Encoder(board, 0)
    encoder1.set_increment(increment_track)
    encoder1.set_decrement(decrement_track)

    encoder2 = Encoder(board, 1)
    encoder2.set_increment(increment_bpm)
    encoder2.set_decrement(decrement_bpm)

update_display()
sequencer.enable()

pico_synth_sandbox.tasks.run()
