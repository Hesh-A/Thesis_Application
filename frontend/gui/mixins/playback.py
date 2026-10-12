from pathlib import Path

from PyQt6.QtCore import QUrl
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer

from frontend.gui.constants import PROJECT_ROOT


class PlaybackMixin:
    def _setup_audio_player(self):
        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)
        self.set_volume(self.volumeSlider.value())
        self._update_play_button_text(self.player.playbackState())

    def load_audio_file(self, audio_file_path):
        path = Path(audio_file_path)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        if not path.is_file():
            print(f"Audio file not found: {path}")
            return
        self.current_audio_path = path
        self.selected_swallow_range = None
        self.selected_swallow_id = None
        self.selected_swallow_flagged = False
        self.annotationBox.setTitle("Annotation Panel")
        self.spectrogram_loading = False
        self.player.setSource(QUrl.fromLocalFile(str(path)))
        self._set_annotation_state("")
        self.load_waveform()
        self.load_spectrogram_overview()

    def toggle_playback(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            if self.selected_swallow_range is not None:
                start_time, end_time = self.selected_swallow_range
                playback_start = max(0.0, start_time - 2.0)
                playback_end = min(self.current_audio_duration, end_time + 2.0)
                position_seconds = self.player.position() / 1000.0
                if not playback_start <= position_seconds < playback_end:
                    self.player.setPosition(round(playback_start * 1000))
            self.player.play()

    def _stop_at_swallow_end(self, position_ms):
        if self.selected_swallow_range is None:
            return

        _, end_time = self.selected_swallow_range
        playback_end = min(self.current_audio_duration, end_time + 2.0)
        if position_ms >= round(playback_end * 1000):
            self.player.pause()

    def set_volume(self, slider_value):
        self.audio_output.setVolume(slider_value / 100.0)

    def _update_play_button_text(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.playButton.setText("⏸")
        else:
            self.playButton.setText("▶")

    def _update_playback_cursor(self, position_ms):
        if self.selected_swallow_range is None:
            return

        position_seconds = position_ms / 1000.0
        for cursor in (
            self.waveform_playback_cursor,
            self.spectrogram_playback_cursor,
        ):
            if cursor is not None:
                try:
                    cursor.setValue(position_seconds)
                except RuntimeError:
                    pass
