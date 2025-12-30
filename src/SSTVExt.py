"""
Extension classes enhance TouchDesigner components with python. An
extension is accessed via ext.ExtensionClassName from any operator
within the extended component. If the extension is promoted via its
Promote Extension parameter, all its attributes with capitalized names
can be accessed externally, e.g. op('yourComp').PromotedFunction().

Help: search "Extensions" in wiki
"""

from TDStoreTools import StorageManager
import TDFunctions as TDF
import numpy as np

from enum import StrEnum

class State(StrEnum):
	READY = 'READY'
	GENERATING = 'GENERATING'


class State(StrEnum):
	READY = 'READY'
	PREFIX = 'PREFIX'
	HEADER = 'HEADER'
	SCANLINES = 'SCANLINES'


class Mode:
	pass


class MartinM1(Mode):
	vis_code = 44
	
	sync_pulse_freq = 1200
	sync_interval = .004862
	blanking_pulse_freq = 1500
	scanline_length = .146432
	blanking_interval = .000572
	low_freq = 1500
	hi_freq = 2300


class MartinM2(Mode):
	vis_code = 40

	sync_pulse_freq = 1200
	sync_interval = .004862
	blanking_pulse_freq = 1500
	scanline_length = .073216
	blanking_interval = .000572
	low_freq = 1500
	hi_freq = 2300	


class SSTVGenerator:

	def __init__(self, mode: Mode, sample_rate: int):
		self._mode = mode
		self._sample_rate = sample_rate

		self._state = State.READY
		self._init()

	def _init(self):
		self._buffer = np.array([])
		self._current_line = 0
		self._last_phase = 0

	def start(self):
		self._state = State.PREFIX
		self._init()

	def stop(self):
		self._state = State.READY

	def generateTone(self, freq: float, duration: float):
		t = np.arange(int(duration * self._sample_rate)) / self._sample_rate
		phase = 2 * np.pi * freq * t + self._last_phase
		self._last_phase = phase[-1] + (phase[-1] - phase[-2])
		return np.cos(phase)
		
	def generatePrefix(self):
		return np.concatenate([
			self.generateTone(1900, .100),
			self.generateTone(1500, .100),
			self.generateTone(1900, .100),
			self.generateTone(1500, .100),
			self.generateTone(2300, .100),
			self.generateTone(1500, .100),
			self.generateTone(2300, .100),
			self.generateTone(1500, .100),
		])

	def generateHeader(self):
		vis_code = list(map(int, reversed(f'{self._mode.vis_code:06b}')))
		parity_bit = sum(vis_code) % 2
		
		return np.concatenate([
			self.generateTone(1900, .300),  # leader_tone, 
			self.generateTone(1200, .01),  # break_segment, 
			self.generateTone(1900, .300),  # leader_tone, 
			self.generateTone(1200, .03), # vis_delimiter,
			np.concatenate([
				self.generateTone(1100, .03) if vis_bit == 1 else self.generateTone(1300, .03) 
				for vis_bit in vis_code
			]), # vis_signal,
			self.generateTone(1300, .03) if parity_bit else self.generateTone(1100, .03),  # parity_tone,
			self.generateTone(1200, .03), # vis_delimiter,
		])
	
	def generateNextChunk(self):
		match self._state:
			case State.READY:
				raise ValueError('Cant get chunk when not generating signal')
			case State.PREFIX:
				self._state = State.HEADER
				return self.generatePrefix()
			case State.HEADER:
				self._state = State.SCANLINES
				return self.generateHeader()
			case State.SCANLINES:
				buffer = self.generateLine(self._current_line)
				self._current_line += 1
				if self._current_line == 256:
					self._state = State.READY					
				return buffer

	def getSamples(self, buffer_size:int):
		if self._buffer.size < buffer_size:
			new_buffer = self.generateNextChunk()
			self._buffer = np.concatenate([self._buffer, new_buffer])

		return_buffer = self._buffer[:buffer_size]
		self._buffer = self._buffer[buffer_size:]
		return return_buffer

	def generateColorLine(self, color_values):
		num_samples = int(self._mode.scanline_length * self._sample_rate) + 1
		interp_line = np.interp(
			np.linspace(0, 1, num_samples),
			np.linspace(0, 1, color_values.size), 
			color_values
		)
		carrier_frequency = (self._mode.hi_freq + self._mode.low_freq) / 2
		modulation_frequency = (self._mode.hi_freq - self._mode.low_freq) * (interp_line-.5)

		time = np.arange(num_samples) / self._sample_rate
		phase = 2 * np.pi * (carrier_frequency * time + np.cumsum(modulation_frequency) / self._sample_rate)
		line_signal = np.cos(phase + self._last_phase)
		self._last_phase = phase[-1] + (phase[-1] - phase[-2])
		separator_pulse = self.generateTone(self._mode.blanking_pulse_freq, self._mode.blanking_interval)
		return np.concatenate([line_signal, separator_pulse])

	def generateLine(self, line_number):
		separator_pulse = self.generateTone(self._mode.blanking_pulse_freq, self._mode.blanking_interval)
		sync_pulse = self.generateTone(self._mode.sync_pulse_freq, self._mode.sync_interval)

		signal = np.concatenate([sync_pulse, separator_pulse])
		for color in ['g', 'b', 'r']:
			color_line = self._image_chop[f'{color}{line_number}'].numpyArray()
			signal = np.append(signal, self.generateColorLine(color_line))

		return signal


class SSTVExt:
	"""
	SSTVExt description
	"""
	def __init__(self, ownerComp):
		sample_rate = 44100
		self.ownerComp = ownerComp
		
		# properties
		TDF.createProperty(self, 'SampleRate', value=sample_rate, dependable=True,
						   readOnly=False)
		TDF.createProperty(self, 'CurrentLine', value=0, dependable=True,
						   readOnly=False)

		self._generator = SSTVGenerator(MartinM1(), self.SampleRate)
		self._generator.start()

		self._cache = op('cache1')
		self._switch = op('switch1')


	def GetSamples(self, chop, buffer_size):
		self.CurrentLine = self._generator._current_line
		self._generator._image_chop = chop
		return self._generator.getSamples(buffer_size)

	def Reset(self):
		self._cache.par.activepulse.pulse()
		self._switch.par.index = 0
		self._generator.start()

	def Stop(self):
		self._switch.par.index = 1
		self._generator.stop()
