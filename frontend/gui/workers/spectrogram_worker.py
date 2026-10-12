from PyQt6.QtCore import QObject, pyqtSignal

from audio.utils.spectrogram_generator.spectrogram_generator import (
    calculate_spectrogram,
)
from audio.utils.waveform_generator.read_audio import read_audio


class SpectrogramWorker(QObject):
    calculated = pyqtSignal(object, object, object, object)
    failed = pyqtSignal(str)

    def __init__(
        self,
        audio_path,
        start_time: float = 0.0,
        end_time: float = 0.0,
        window_length_ms: float = 30.0,
        hop_ms: float = 2.0,
        fft_multiplier: int = 16,
        window_type: str = "hamming",
    ):
        super().__init__()
        self.audio_path = audio_path
        self.start_time = start_time
        self.end_time = end_time
        self.window_length_ms = window_length_ms
        self.hop_ms = hop_ms
        self.fft_multiplier = fft_multiplier
        self.window_type = window_type

    def run(self):
        try:
            sample_rate, audio_data = read_audio(self.audio_path)
            if self.end_time > 0:
                start_index = int(self.start_time * sample_rate)
                end_index = int(self.end_time * sample_rate)
                audio_data = audio_data[start_index:end_index]

            times, frequencies, spectrogram_db = calculate_spectrogram(
                sample_rate,
                audio_data,
                window_length_ms=self.window_length_ms,
                hop_ms=self.hop_ms,
                fft_multiplier=self.fft_multiplier,
                window_type=self.window_type,
            )
            times = times + self.start_time
            self.calculated.emit(
                self.audio_path,
                times,
                frequencies,
                spectrogram_db,
            )
        except Exception as error:
            self.failed.emit(str(error))