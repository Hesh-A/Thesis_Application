from PyQt6.QtCore import QThread

# Legacy Matplotlib preview import, preserved for rollback:
# from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from audio.utils.spectrogram_generator.spectrogram_generator import (
    build_pyqtgraph_spectrogram,
)
from frontend.gui.workers.spectrogram_worker import SpectrogramWorker


class SpectrogramMixin:
    def load_spectrogram(self, start_time=0.0, end_time=0.0):
        # Keep only the latest requested range while a calculation is running.
        if self.spectrogram_loading:
            self.pending_spectrogram_range = (start_time, end_time)
            return
        self.spectrogram_loading = True
        self.spectrogramBox.setTitle("Spectrogram (Loading...)")
        self.statusBar().showMessage("Loading detailed spectrogram...")
        self.start_spectrogram_calculation(
            self.current_audio_path,
            start_time,
            end_time,
        )

    def load_spectrogram_overview(self):
        if self.spectrogram_loading:
            return
        self.spectrogram_loading = True
        self.spectrogramBox.setTitle("Spectrogram (Loading overview...)")
        self.statusBar().showMessage("Loading low-resolution overview...")
        self.start_spectrogram_calculation(
            self.current_audio_path,
            0.0,
            0.0,
            window_length_ms=30.0,
            hop_ms=50.0,
            fft_multiplier=1,
        )

    def start_spectrogram_calculation(
        self,
        audio_path,
        start_time,
        end_time,
        window_length_ms=None,
        hop_ms=None,
        fft_multiplier=None,
    ):
        thread = QThread(self)
        worker = SpectrogramWorker(
            audio_path,
            start_time,
            end_time,
            window_length_ms=(
                self.windowLengthBox.value()
                if window_length_ms is None
                else window_length_ms
            ),
            hop_ms=self.hopsizeBox.value() if hop_ms is None else hop_ms,
            fft_multiplier=(
                self.fftsizeBox.currentData()
                if fft_multiplier is None
                else fft_multiplier
            ),
            window_type=self.windowTypeBox.currentText(),
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.calculated.connect(self.on_spectrogram_calculated)
        worker.calculated.connect(thread.quit)
        worker.failed.connect(self.on_spectrogram_failed)
        worker.failed.connect(thread.quit)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self.spectrogram_jobs.remove((thread, worker)))
        self.spectrogram_jobs.append((thread, worker))
        thread.start()

    def on_spectrogram_calculated(self, audio_path, times, frequencies, spectrogram_db):
        # A result for a recording that is no longer selected 
        # should not replace the current view.
        if audio_path != self.current_audio_path:
            return
        self.spectrogram_loading = False
        spectrogram, image, maximum_db = build_pyqtgraph_spectrogram(
            times,
            frequencies,
            spectrogram_db,
            dynamic_range_db=self.drSlider.value(),
            colormap=self.colormapBox.currentText(),
        )
        self._set_pyqtgraph_spectrogram_canvas(
            spectrogram,
            image,
            maximum_db,
            times,
            frequencies,
        )
        self.change_frequency_range()
        self._update_timeline_view()
        self.spectrogramBox.setTitle("Spectrogram")
        self.statusBar().showMessage("Spectrogram ready", 2000)
        # Clear the queued range before launching its calculation.
        if self.pending_spectrogram_range is not None:
            start_time, end_time = self.pending_spectrogram_range
            self.pending_spectrogram_range = None
            self.load_spectrogram(start_time, end_time)

    def on_spectrogram_failed(self, error_message):
        self.spectrogram_loading = False
        self.spectrogramBox.setTitle("Spectrogram (Failed)")
        self.statusBar().showMessage(f"Spectrogram failed: {error_message}", 5000)

    # Legacy Matplotlib canvas path preserved for rollback:
    # def _set_spectrogram_canvas(self, figure, image):
    #     canvas = FigureCanvas(figure)
    #     self._replace_canvas("spectrogram_canvas", self.spectroGramLabel, canvas)
    #     self.spectrogram_canvas = canvas
    #     self.spectrogram_image = image
    #     self.spectrogram_x_limits = figure.axes[0].get_xlim()

    def _set_pyqtgraph_spectrogram_canvas(self, plot, image, maximum_db, times, frequencies):
        self.spectrogram_swallow_region = None
        self.spectrogram_playback_cursor = None
        self._replace_canvas("spectrogram_canvas", self.spectroGramLabel, plot)
        self.spectrogram_canvas = plot
        self.spectrogram_image = image
        self.spectrogram_maximum_db = maximum_db
        self.spectrogram_x_limits = (float(times[0]), float(times[-1]))
        self._highlight_selected_swallow()
