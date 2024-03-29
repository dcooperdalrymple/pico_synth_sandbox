# pico_synth_sandbox/voice/sample.py
# 2023 Cooper Dalrymple - me@dcdalrymple.com
# GPL v3 License

import os
from pico_synth_sandbox import fftfreq, LOG_2, clamp
from pico_synth_sandbox.voice import Voice
from pico_synth_sandbox.voice.oscillator import Oscillator
import pico_synth_sandbox.waveform as waveform
import math, time

class Sample(Oscillator):
    def __init__(self, loop=True, filepath=""):
        Oscillator.__init__(self)

        self._loop = loop

        self._sample_rate = os.getenv("AUDIO_RATE", 22050)
        self._wave_rate = self._sample_rate
        self._sample_tune = 0.0
        self._loop_tune = 0.0
        self._start = None
        self._desired_frequency = self._root

        if filepath:
            self.load_from_file(filepath)

    def load(self, data, sample_rate, root=None):
        self._wave_rate = sample_rate
        self.set_waveform(data)
        if root is None:
            self._root = fftfreq(
                data=self._note.waveform,
                sample_rate=self._wave_rate
            )
        self._wave_duration = 1.0 / self._root
        self._sample_duration = len(self._note.waveform) / self._wave_rate
        self._sample_tune = math.log(self._wave_duration / self._sample_duration) / LOG_2
        self.set_loop() # calls self._update_root
    def load_from_file(self, filepath, max_samples=4096):
        data, sample_rate = waveform.load_from_file(filepath, max_samples)
        self.load(data, sample_rate)

    def unload(self):
        self._wave_rate = self._sample_rate
        self.set_waveform(None)
        self._root = self._desired_frequency
        self._wave_duration = 1.0 / self._root
        self._sample_duration = 0.0
        self._sample_tune = 0.0
        self._update_root()

    def press(self, notenum, velocity):
        if self._note.waveform is None:
            return False
        if not Oscillator.press(self, notenum, velocity):
            return False
        if not self._loop:
            self._start = time.monotonic()
        return True

    def get_duration(self):
        return self._sample_duration * self._root / pow(2,self._note.bend.value) / self._desired_frequency

    def set_loop(self, start=0.0, end=1.0):
        Oscillator.set_loop(self, start, end)

        length = self._note.waveform_loop_end - self._note.waveform_loop_start
        if length < 2:
            return

        sample_length = len(self._note.waveform)
        self._loop_tune = math.log(sample_length / length) / LOG_2 if length != sample_length else 0.0
        self._update_root()

    def _update_root(self):
        Oscillator._update_root(self)
        self._note.frequency = self._note.frequency * pow(2,self._sample_tune) * pow(2,self._loop_tune)

    async def update(self, synth):
        await Voice.update(self, synth)
        if not self._loop and not self._start is None and time.monotonic() - self._start >= self.get_duration():
            synth.release(self)
            self._start = None
