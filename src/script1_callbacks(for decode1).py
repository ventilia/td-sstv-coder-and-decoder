import numpy as np

FREQ_SYNC = 1200.0
FREQ_BLACK = 1500.0
FREQ_WHITE = 2300.0
FREQ_THRESHOLD = 150.0

MODE_CONFIG = {
    'm1': {
        'label': 'Martin 1',
        'width': 320,
        'height': 256,
        'sync_dur': 0.004862,
        'sep_dur': 0.000572,
        'color_dur': 0.146432,
        'channel_map': [1, 2, 0],
    },
    'm2': {
        'label': 'Martin 2',
        'width': 320,
        'height': 256,
        'sync_dur': 0.004862,
        'sep_dur': 0.000572,
        'color_dur': 0.073216,
        'channel_map': [1, 2, 0],
    },
}


class SSTVDecoder:
    def __init__(self, sample_rate=44100, mode='m1'):
        self.sr = int(sample_rate)
        self.apply_mode(mode)
        self.reset()

    def apply_mode(self, mode):
        cfg = MODE_CONFIG.get(mode, MODE_CONFIG['m1'])
        self.mode_name = mode
        self.width = cfg['width']
        self.height = cfg['height']
        self.sync_dur = cfg['sync_dur']
        self.sep_dur = cfg['sep_dur']
        self.color_dur = cfg['color_dur']
        self.channel_map = cfg['channel_map']

        self.sync_len = int(self.sync_dur * self.sr)
        self.sep_len = int(self.sep_dur * self.sr)
        self.color_len = int(self.color_dur * self.sr)

        self.full_line_len = (
            self.sync_len +
            (4 * self.sep_len) +
            (3 * self.color_len)
        )

    def reset(self):
        self.audio = np.zeros(0, dtype=np.float32)
        self.line = 0
        self.image = np.zeros((self.height, self.width, 4), dtype=np.float32)
        self.image[:, :, 3] = 1.0
        self.is_syncing = True

    def _analytic(self, x):
        n = x.size
        X = np.fft.fft(x)
        h = np.zeros(n)

        if n > 0:
            h[0] = 1
            if n % 2 == 0:
                h[1:n // 2] = 2
                h[n // 2] = 1
            else:
                h[1:(n + 1) // 2] = 2

        return np.fft.ifft(X * h)

    def _get_freq(self, chunk):
        if chunk.size < 8:
            return 0.0

        analytic = self._analytic(chunk)
        phase = np.unwrap(np.angle(analytic))

        if phase.size < 2:
            return 0.0

        freq = np.diff(phase) * self.sr / (2.0 * np.pi)
        return float(np.median(freq))

    def _decode_color_segment(self, seg):
        if self.mode_name == 'm2':
            win_size = 32
            hop = 8
        else:
            win_size = 64
            hop = 16

        freqs = []
        for i in range(0, max(0, seg.size - win_size + 1), hop):
            f = self._get_freq(seg[i:i + win_size])
            freqs.append(f)

        if not freqs:
            return np.zeros(self.width, dtype=np.float32)

        bright = np.clip(
            (np.array(freqs, dtype=np.float32) - FREQ_BLACK) /
            (FREQ_WHITE - FREQ_BLACK),
            0.0,
            1.0
        )

        xp = np.linspace(0.0, 1.0, len(bright))
        xq = np.linspace(0.0, 1.0, self.width)
        return np.interp(xq, xp, bright).astype(np.float32)

    def feed(self, chunk):
        if chunk is None or chunk.size == 0:
            return

        if chunk.ndim > 1:
            chunk = np.mean(chunk, axis=0)

        self.audio = np.append(self.audio, chunk.flatten())

        limit = self.sr * 10
        if self.audio.size > limit:
            self.audio = self.audio[-limit:]

        self._process()

    def _process(self):
        while self.audio.size >= self.full_line_len:
            if self.is_syncing:
                found_sync = False

                search_end = self.audio.size - self.full_line_len + 1
                for i in range(0, search_end, 16):
                    test = self.audio[i:i + self.sync_len]
                    f = self._get_freq(test)

                    if abs(f - FREQ_SYNC) < FREQ_THRESHOLD:
                        self.audio = self.audio[i:]
                        self.is_syncing = False
                        found_sync = True
                        break

                if not found_sync:
                    self.audio = self.audio[-self.full_line_len:]
                    break

            if self.audio.size < self.full_line_len:
                break

            line_data = self.audio[:self.full_line_len]
            p = self.sync_len + self.sep_len

            for ch_idx in self.channel_map:
                seg = line_data[p:p + self.color_len]
                pixels = self._decode_color_segment(seg)

                if self.line < self.height:
                    self.image[self.line, :, ch_idx] = pixels

                p += self.color_len + self.sep_len

            self.line += 1
            if self.line >= self.height:
                self.line = 0

            self.audio = self.audio[self.full_line_len:]
            self.is_syncing = True

    def get_image(self):
        return self.image


def _get_par_eval(op_obj, par_name, default=None):
    par = getattr(op_obj.par, par_name, None)
    if par is None:
        return default
    try:
        return par.eval()
    except Exception:
        return default


def _make_state(sr, mode):
    return {
        'decoder': SSTVDecoder(sample_rate=sr, mode=mode),
        'mode': mode,
        'sr': sr,
        'reset_prev': False,
    }


def onCook(scriptOp):
    base = scriptOp.parent()


    current_mode = _get_par_eval(base, 'Mode', 'm1')

    input_chop = op('input1')
    sr = int(input_chop.rate) if input_chop else 44100

    state = scriptOp.storage.get('sstv_state')
    needs_recreate = (
        state is None
        or state.get('mode') != current_mode
        or state.get('sr') != sr
    )

    if needs_recreate:
        state = _make_state(sr, current_mode)
        scriptOp.storage['sstv_state'] = state

    decoder = state['decoder']

    reset_now = bool(_get_par_eval(base, 'Reset', 0))
    reset_prev = bool(state.get('reset_prev', False))

    if reset_now and not reset_prev:
        decoder.reset()
        state['reset_prev'] = reset_now
        scriptOp.copyNumpyArray(decoder.get_image())
        return

    state['reset_prev'] = reset_now

    if input_chop:
        audio_data = input_chop.numpyArray()
        decoder.feed(audio_data)

    img = decoder.get_image()
    scriptOp.copyNumpyArray(img)


def onGetCookLevel(scriptOp):
    return CookLevel.ALWAYS