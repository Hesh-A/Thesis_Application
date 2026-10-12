from PyQt6.QtCore import QSignalBlocker, Qt
import pyqtgraph as pg


class TimelineMixin:
    def jump_to_swallow(self, item):
        swallow_number = item.data(Qt.ItemDataRole.UserRole)
        swallow = self.swallow_records.get(swallow_number)
        if swallow is None:
            return

        start_time = float(swallow["start_time"]) - self.current_audio_start_time
        end_time = float(swallow["end_time"]) - self.current_audio_start_time
        if end_time <= start_time:
            self.statusBar().showMessage("Invalid swallow time range", 3000)
            return
        if start_time < 0:
            self.statusBar().showMessage("Swallow occurs before this audio recording", 3000)
            return
        if start_time >= self.current_audio_duration:
            self.statusBar().showMessage("Swallow occurs after this audio recording", 3000)
            return

        end_time = min(end_time, self.current_audio_duration)
        self.selected_swallow_range = (start_time, end_time)
        self.selected_swallow_id = swallow["id"]
        self.selected_swallow_flagged = bool(swallow.get("flagged"))
        flag_text = " (Flagged)" if self.selected_swallow_flagged else ""
        self.annotationBox.setTitle(f"Annotation Panel - Swallow {swallow_number}{flag_text}")
        self.load_annotation(self.selected_swallow_id)
        view_start = max(0.0, start_time - 2.0)
        view_end = min(self.current_audio_duration, end_time + 2.0)

        with (
            QSignalBlocker(self.waveformZoomSlider),
            QSignalBlocker(self.spectrogramZoomSlider),
            QSignalBlocker(self.timeLineScrollBar),
        ):
            self.waveformZoomSlider.setValue(self.waveformZoomSlider.minimum())
            self.spectrogramZoomSlider.setValue(self.spectrogramZoomSlider.minimum())
            self.timeLineScrollBar.setValue(self.timeLineScrollBar.minimum())

        self.player.setPosition(round(view_start * 1000))
        self.load_waveform(view_start, view_end)
        self.load_spectrogram(view_start, view_end)
        self.statusBar().showMessage(
            f"Swallow {swallow_number}{flag_text}: {start_time:.3f}s - {end_time:.3f}s",
            3000,
        )

    def _highlight_selected_swallow(self):
        if self.selected_swallow_range is None:
            return

        start_time, end_time = self.selected_swallow_range
        for canvas, region in (
            (self.waveform_canvas, self.waveform_swallow_region),
            (self.spectrogram_canvas, self.spectrogram_swallow_region),
        ):
            if isinstance(canvas, pg.PlotWidget) and region is not None:
                try:
                    if region.scene() is not None:
                        canvas.removeItem(region)
                except RuntimeError:
                    pass

        cursor_position = self.player.position() / 1000.0
        for canvas, cursor in (
            (self.waveform_canvas, self.waveform_playback_cursor),
            (self.spectrogram_canvas, self.spectrogram_playback_cursor),
        ):
            if isinstance(canvas, pg.PlotWidget) and cursor is not None:
                try:
                    if cursor.scene() is not None:
                        canvas.removeItem(cursor)
                except RuntimeError:
                    pass

        if self.selected_swallow_flagged:
            brush, pen = pg.mkBrush(244, 67, 54, 70), pg.mkPen("#b71c1c", width=1.5)
        else:
            brush, pen = pg.mkBrush(33, 150, 243, 60), pg.mkPen("#0d47a1", width=1.5)
        region_style = {
            "values": (start_time, end_time),
            "movable": False,
            "brush": brush,
            "pen": pen,
        }

        if isinstance(self.waveform_canvas, pg.PlotWidget):
            self.waveform_swallow_region = pg.LinearRegionItem(**region_style)
            self.waveform_swallow_region.setZValue(10)
            self.waveform_canvas.addItem(self.waveform_swallow_region)

        if isinstance(self.spectrogram_canvas, pg.PlotWidget):
            self.spectrogram_swallow_region = pg.LinearRegionItem(**region_style)
            self.spectrogram_swallow_region.setZValue(10)
            self.spectrogram_canvas.addItem(self.spectrogram_swallow_region)



        cursor_pen = pg.mkPen("#FFE100", width=1.5)
        if isinstance(self.waveform_canvas, pg.PlotWidget):
            self.waveform_playback_cursor = pg.InfiniteLine(
                pos=cursor_position,
                angle=90,
                movable=False,
                pen=cursor_pen,
            )
            self.waveform_playback_cursor.setZValue(20)
            self.waveform_canvas.addItem(self.waveform_playback_cursor)

        if isinstance(self.spectrogram_canvas, pg.PlotWidget):
            self.spectrogram_playback_cursor = pg.InfiniteLine(
                pos=cursor_position,
                angle=90,
                movable=False,
                pen=cursor_pen,
            )
            self.spectrogram_playback_cursor.setZValue(20)
            self.spectrogram_canvas.addItem(self.spectrogram_playback_cursor)

    def _replace_canvas(self, name, placeholder, new_canvas):
        current = getattr(self, name)
        if current is None:
            layout = placeholder.parentWidget().layout()
            layout.replaceWidget(placeholder, new_canvas)
            placeholder.hide()
        else:
            layout = current.parentWidget().layout()
            layout.replaceWidget(current, new_canvas)
            current.deleteLater()

    def zoom_timeline(self, value):
        with QSignalBlocker(self.waveformZoomSlider), QSignalBlocker(self.spectrogramZoomSlider):
            self.waveformZoomSlider.setValue(value)
            self.spectrogramZoomSlider.setValue(value)
        self._update_timeline_view()

    def scroll_timeline(self, value):
        with QSignalBlocker(self.timeLineScrollBar):
            self.timeLineScrollBar.setValue(value)
        self._update_timeline_view()

    def _update_timeline_view(self):
        limits = self.waveform_x_limits or self.spectrogram_x_limits
        if limits is None:
            return
        full_start, full_end = limits
        zoom_factor = 1 + (self.waveformZoomSlider.value() - 1) / 11
        visible_duration = (full_end - full_start) / zoom_factor
        available_distance = full_end - full_start - visible_duration
        fraction = self.timeLineScrollBar.value() / max(1, self.timeLineScrollBar.maximum())
        start = full_start + available_distance * fraction
        end = start + visible_duration
        for canvas in (self.waveform_canvas, self.spectrogram_canvas):
            if canvas is not None:
                canvas.setXRange(start, end, padding=0)
