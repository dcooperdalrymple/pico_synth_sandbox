# pico_synth_sandbox/voice/drum.py
# 2023 Cooper Dalrymple - me@dcdalrymple.com
# GPL v3 License

# Inspired by https://gist.github.com/gamblor21/15a430929abf0e10eeaba8a45b01f5a8

from pico_synth_sandbox import clamp, map_value, calculate_filter_frequency_value
from pico_synth_sandbox.voice import Voice
from pico_synth_sandbox.synth import Synth
import pico_synth_sandbox.waveform as waveform
import synthio

class Drum(Voice):
    def __init__(self, count=3, filter_type=Synth.FILTER_LPF, filter_frequency=0, frequencies=[], times=[], waveforms=[]):
        Voice.__init__(self)

        if not frequencies:
            frequencies = [440.0]
        if not times:
            times = [1.0]

        self._times = times
        self._attack_level = 1.0

        self._lfo = synthio.LFO(
            waveform=waveform.get_saw(),
            rate=20,
            scale=0.3,
            offset=0.33,
            once=True
        )

        self._notes = []
        for i in range(count):
            self._notes.append(synthio.Note(
                frequency=frequencies[i % len(frequencies)],
                bend=self._lfo
            ))

        self.set_times(times)
        self.set_waveforms(waveforms)

        self.set_filter(
            type=filter_type,
            frequency=calculate_filter_frequency_value(filter_frequency),
            resonance=0.0
        )

    def get_notes(self):
        return self._notes
    def get_blocks(self):
        return [self._lfo]

    def set_frequencies(self, values):
        if isinstance(values, int): values = [values]
        if not values: return
        for i, note in enumerate(self.get_notes()):
            note.frequency = values[i % len(values)]

    def set_times(self, values, velocity=None):
        if isinstance(values, int): values = [values]
        if not values: return
        self._times = values
        self._update_envelope()

    def set_waveforms(self, values):
        if not values: return
        for i, note in enumerate(self.get_notes()):
            note.waveform = values[i % len(values)]

    def press(self, notenum, velocity=1.0):
        if not Voice.press(self, notenum, velocity):
            return False
        self._lfo.retrigger()
        return True
    def release(self):
        Voice.release(self)
        return False

    def set_level(self, value):
        for note in self.get_notes():
            note.amplitude = value

    def _update_envelope(self):
        mod = self._get_velocity_mod()
        for i, note in enumerate(self.get_notes()):
            note.envelope = synthio.Envelope(
                attack_time=0.0,
                decay_time=self._times[i % len(self._times)],
                release_time=0.0,
                attack_level=mod*self._attack_level,
                sustain_level=0.0
            )

    def set_envelope_attack_level(self, value, update=True):
        self._attack_level = value
        if update: self._update_envelope()

class Kick(Drum):
    def __init__(self):
        Drum.__init__(self,
            count=3,
            filter_frequency=2000,
            frequencies=[53, 72, 41],
            times=[0.075, 0.055, 0.095],
            waveforms=[waveform.get_offset_sine(), waveform.get_sine(), waveform.get_offset_sine()]
        )

class Snare(Drum):
    def __init__(self):
        Drum.__init__(self,
            count=3,
            filter_frequency=9500,
            frequencies=[90, 135, 165],
            times=[0.115, 0.095, 0.115],
            waveforms=[waveform.get_sine_noise(), waveform.get_offset_sine_noise(), waveform.get_offset_sine_noise()]
        )

class Hat(Drum):
    def __init__(self, min_time, max_time):
        Drum.__init__(self,
            count=3,
            filter_type=Synth.FILTER_HPF,
            filter_frequency=9500,
            frequencies=[90, 135, 165],
            waveforms=[waveform.get_noise()]
        )
        self._min_time = max(min_time, 0.0)
        self._max_time = max(max_time, self._min_time)
        self.set_time()

    def set_time(self, value=0.5):
        value = map_value(value, self._min_time, self._max_time)
        self.set_times([
            value,
            clamp(value-0.02),
            value
        ])

class ClosedHat(Hat):
    def __init__(self):
        Hat.__init__(self, 0.025, 0.2)

class OpenHat(Hat):
    def __init__(self):
        Hat.__init__(self, 0.25, 1.0)
