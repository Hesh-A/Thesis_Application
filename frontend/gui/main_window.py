from PyQt6 import uic
from PyQt6.QtWidgets import QMainWindow

from audio.utils.waveform_generator.read_audio import AUDIO_PATH
from frontend.gui.constants import UI_PATH
from frontend.gui.mixins.annotations import AnnotationMixin
from frontend.gui.mixins.data_loading import DataLoadingMixin
from frontend.gui.mixins.parameters import SpectrogramParametersMixin
from frontend.gui.mixins.playback import PlaybackMixin
from frontend.gui.mixins.spectrogram import SpectrogramMixin
from frontend.gui.mixins.timeline import TimelineMixin
from frontend.gui.mixins.waveform import WaveformMixin


class MainWindow(
    DataLoadingMixin,
    AnnotationMixin,
    PlaybackMixin,
    WaveformMixin,
    SpectrogramMixin,
    SpectrogramParametersMixin,
    TimelineMixin,
    QMainWindow,
):
    def __init__(self):
        super().__init__()
        uic.loadUi(UI_PATH, self)
        self._setup_parameter_controls()
        self.waveform_canvas = None
        self.spectrogram_canvas = None
        self.spectrogram_image = None
        self.spectrogram_maximum_db = None
        self.waveform_x_limits = None
        self.spectrogram_x_limits = None
        self.participant_records = {}
        self.session_records = {}
        self.swallow_records = {}
        self.selected_swallow_range = None
        self.waveform_swallow_region = None
        self.spectrogram_swallow_region = None
        self.waveform_playback_cursor = None
        self.spectrogram_playback_cursor = None
        self.current_audio_path = AUDIO_PATH
        self.current_audio_start_time = 0.0
        self.current_audio_duration = 0.0
        self.spectrogram_thread = None
        self.spectrogram_worker = None
        self.spectrogram_jobs = []
        self.spectrogram_loading = False
        self.pending_spectrogram_range = None
        self.selected_swallow_id = None
        self.selected_swallow_flagged = False

        self._setup_audio_player()
        self._connect_signals()
        self._load_initial_ui_state()

    def _connect_signals(self):
        self.playButton.clicked.connect(self.toggle_playback)
        self.volumeSlider.valueChanged.connect(self.set_volume)
        self.player.playbackStateChanged.connect(self._update_play_button_text)
        self.player.positionChanged.connect(self._update_playback_cursor)
        self.player.positionChanged.connect(self._stop_at_swallow_end)
        self.participantsSection.currentTextChanged.connect(self.load_sessions)
        self.sessionSection.currentTextChanged.connect(self.load_swallows)
        self.swallowSection.itemClicked.connect(self.jump_to_swallow)
        self.saveAnnotationsButton.clicked.connect(self.apply_spectrogram_parameters)
        self.resetSpectrogramParametersButton.clicked.connect(self.reset_spectrogram_parameters)
        self.saveAnnotationButton.clicked.connect(self.save_annotation)
        self.actionImport_Data.triggered.connect(self.import_data)
        self.actionExport_Data.triggered.connect(self.export_project)
        self.actionOpen_Project.triggered.connect(self.open_project)
        self.waveformZoomSlider.valueChanged.connect(self.zoom_timeline)
        self.spectrogramZoomSlider.valueChanged.connect(self.zoom_timeline)
        self.timeLineScrollBar.valueChanged.connect(self.scroll_timeline)
