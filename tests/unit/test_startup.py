import sys
from types import SimpleNamespace

import pytest

import main


def test_startup_selection_rejects_missing_project(tmp_path, monkeypatch):
    monkeypatch.delenv("SWALLOW_PROJECT_ROOT", raising=False)
    missing = tmp_path / "missing"

    with pytest.raises(FileNotFoundError, match="Project database not found"):
        main.select_project(["--project", str(missing)])


@pytest.mark.parametrize("stale_selection", [False, True])
def test_startup_creates_default_user_project_folders(tmp_path, monkeypatch, stale_selection):
    removed = []

    class EmptySettings:
        def value(self, key):
            return str(tmp_path / "deleted-project") if stale_selection else None

        def remove(self, key):
            removed.append(key)

    root = tmp_path / "Documents" / "Swallow Audio Annotation"
    monkeypatch.setattr(main, "DEFAULT_PROJECT_ROOT", root)
    monkeypatch.setattr(main, "QSettings", lambda *args: EmptySettings())
    monkeypatch.delenv("SWALLOW_PROJECT_ROOT", raising=False)

    assert main.select_project([]) == []
    assert (root / "database").is_dir()
    assert (root / "audio").is_dir()
    assert __import__("os").environ["SWALLOW_PROJECT_ROOT"] == str(root)
    assert removed == (["project_root"] if stale_selection else [])


def test_backend_configures_without_console_streams(monkeypatch):
    class StartedServer:
        started = True

        def __init__(self, config):
            self.config = config

        def run(self):
            pass

    monkeypatch.setitem(sys.modules, "api.app", SimpleNamespace(app=object()))
    monkeypatch.setattr(main.uvicorn, "Server", StartedServer)
    with monkeypatch.context() as streams:
        streams.setattr(sys, "stdout", None)
        streams.setattr(sys, "stderr", None)
        server, thread = main.start_backend()
        thread.join()

    assert server.config.use_colors is False


def test_startup_refuses_another_server_instead_of_using_wrong_project(monkeypatch):
    class StoppedServer:
        started = False

        def __init__(self, config):
            self.should_exit = False

        def run(self):
            pass

    monkeypatch.setitem(sys.modules, "api.app", SimpleNamespace(app=object()))
    monkeypatch.setattr(main.uvicorn, "Config", lambda *args, **kwargs: None)
    monkeypatch.setattr(main.uvicorn, "Server", StoppedServer)

    with pytest.raises(RuntimeError, match="Close the other app instance"):
        main.start_backend()
