from audio.utils.spectrogram_generator.spectrogram_generator import get_pyqtgraph_colormap_lut


class SpectrogramParametersMixin:
    def _setup_parameter_controls(self):
        self.colormapBox.addItems(["magma", "viridis", "plasma", "inferno", "gray"])
        self.colormapBox.setCurrentText("magma")
        self.frequencyRangeMinBox.setRange(0, 8000)
        self.frequencyRangeMinBox.setValue(0)
        self.frequencyRangeMaxBox.setRange(0, 8000)
        self.frequencyRangeMaxBox.setValue(8000)
        self.windowLengthBox.setRange(1, 200)
        self.windowLengthBox.setValue(30)
        self.hopsizeBox.setRange(1, 100)
        self.hopsizeBox.setValue(5)
        self.windowTypeBox.addItems(["hamming", "hann", "blackman", "boxcar"])
        self.windowTypeBox.setCurrentText("hamming")
        for multiplier in (1, 2, 4, 8, 16, 32):
            self.fftsizeBox.addItem(f"{multiplier}x", multiplier)
        self.fftsizeBox.setCurrentIndex(2)

    def reset_spectrogram_parameters(self):
        self.windowLengthBox.setValue(30)
        self.hopsizeBox.setValue(5)
        self.windowTypeBox.setCurrentText("hamming")
        self.fftsizeBox.setCurrentIndex(self.fftsizeBox.findData(4))
        self.frequencyRangeMinBox.setValue(0)
        self.frequencyRangeMaxBox.setValue(8000)
        self.drSlider.setValue(80)
        self.colormapBox.setCurrentText("magma")
        if self.selected_swallow_range is None:
            self.load_spectrogram_overview()
        else:
            self.apply_spectrogram_parameters()

    def apply_spectrogram_parameters(self):
        if self.selected_swallow_range is None:
            self.statusBar().showMessage(
                "Select a swallow before applying spectrogram parameters",
                3000,
            )
            return

        start_time, end_time = self.selected_swallow_range
        view_start = max(0.0, start_time - 2.0)
        view_end = min(self.current_audio_duration, end_time + 2.0)
        self.load_spectrogram(view_start, view_end)

    def change_dynamic_range(self, dynamic_range_db):
        if self.spectrogram_image is None:
            return
        self.spectrogram_image.setLevels(
            [
                self.spectrogram_maximum_db - dynamic_range_db,
                self.spectrogram_maximum_db,
            ]
        )
        self.spectrogram_canvas.repaint()

    def change_colormap(self, colormap):
        if self.spectrogram_image is None or not colormap:
            return
        self.spectrogram_image.setLookupTable(
            get_pyqtgraph_colormap_lut(colormap)
        )
        self.spectrogram_canvas.repaint()

    def change_frequency_range(self):
        if self.spectrogram_canvas is None:
            return
        minimum = self.frequencyRangeMinBox.value()
        maximum = self.frequencyRangeMaxBox.value()
        if minimum >= maximum:
            return
        self.spectrogram_canvas.setYRange(minimum, maximum, padding=0)
