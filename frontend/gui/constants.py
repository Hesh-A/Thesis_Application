import os
from pathlib import Path

from PyQt6.QtGui import QColor

UI_PATH = Path(__file__).resolve().parent.parent / "main_window.ui"
PROJECT_ROOT = Path(os.environ.get("SWALLOW_PROJECT_ROOT") or Path(__file__).resolve().parents[2]).resolve()
API_BASE_URL = "http://127.0.0.1:8000/api"
ASPIRATING_SESSION_COLOR = QColor(211, 47, 47)
