import argparse
import os
from pathlib import Path
import sys
import threading
import time

import uvicorn
from PyQt6.QtCore import QSettings, QStandardPaths
from PyQt6.QtWidgets import QApplication

API_HOST = "127.0.0.1"
API_PORT = 8000
DEFAULT_PROJECT_ROOT = (
    Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation))
    / "Swallow Audio Annotation"
)

def select_project(arguments):
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path)
    options, qt_arguments = parser.parse_known_args(arguments)
    settings = QSettings("Thesis", "Swallow Audio Annotation")
    explicit_project = options.project or os.environ.get("SWALLOW_PROJECT_ROOT")
    saved_project = settings.value("project_root")
    root = Path(explicit_project or saved_project or DEFAULT_PROJECT_ROOT).resolve()
    if not explicit_project and saved_project and not (root / "database" / "swallow.db").is_file():
        settings.remove("project_root")
        root = DEFAULT_PROJECT_ROOT.resolve()
    if root != DEFAULT_PROJECT_ROOT.resolve() and not (root / "database" / "swallow.db").is_file():
        raise FileNotFoundError(f"Project database not found: {root}")
    if root == DEFAULT_PROJECT_ROOT.resolve():
        (root / "database").mkdir(parents=True, exist_ok=True)
        (root / "audio").mkdir(exist_ok=True)
    os.environ["SWALLOW_PROJECT_ROOT"] = str(root)
    return qt_arguments


def start_backend():
    from api.app import app

    server = uvicorn.Server(
        uvicorn.Config(app, host=API_HOST, port=API_PORT, log_level="warning", use_colors=False)
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started and thread.is_alive() and time.monotonic() < deadline:
        time.sleep(0.05)
    if not server.started:
        server.should_exit = True
        thread.join(timeout=5)
        raise RuntimeError(
            f"Local API could not start on {API_HOST}:{API_PORT}. "
            "Close the other app instance before opening this project."
        )
    return server, thread


def main():
    qt_arguments = select_project(sys.argv[1:])
    from frontend.gui.main_window import MainWindow

    server, thread = start_backend()
    qt_app = QApplication([sys.argv[0], *qt_arguments])
    window = MainWindow()
    window.show()
    exit_code = qt_app.exec()
    server.should_exit = True
    thread.join(timeout=5)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())




