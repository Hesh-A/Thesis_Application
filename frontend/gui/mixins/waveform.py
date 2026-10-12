from audio.utils.waveform_generator.display_waveform import build_pyqtgraph_waveform
from audio.utils.waveform_generator.read_audio import read_audio


class WaveformMixin:
    def load_waveform(self, start_time=0.0, end_time=0.0):
        sample_rate, audio_data = read_audio(self.current_audio_path)
        self.current_audio_duration = len(audio_data) / sample_rate
        waveform, time_limits = build_pyqtgraph_waveform(
            sample_rate,
            audio_data,
            start_time=start_time,
            end_time=end_time,
        )
        self._set_waveform_canvas(waveform, time_limits)

    def _set_waveform_canvas(self, waveform, time_limits):
        self.waveform_swallow_region = None
        self.waveform_playback_cursor = None
        self._replace_canvas("waveform_canvas", self.waveformLabel, waveform)
        self.waveform_canvas = waveform
        self.waveform_x_limits = time_limits
        self._highlight_selected_swallow()
