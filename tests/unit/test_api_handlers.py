import importlib
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from api.participants import get_participant, get_participants
from api.sessions import get_session, get_sessions
from api.swallows import get_swallow, get_swallows, get_swallows_by_session

pytestmark = pytest.mark.unit


def test_app_registers_routes_without_initializing_live_database(monkeypatch):
    from database import models

    monkeypatch.setattr(models, "init_db", lambda: None)
    app_module = importlib.import_module("api.app")

    paths = set(app_module.app.openapi()["paths"])
    assert {"/", "/api/participants", "/api/sessions", "/api/swallows"} <= paths
    assert "/api/annotations/swallow/{swallow_id}" in paths
    assert app_module.home() == {"message": "Backend is running!"}


@pytest.mark.parametrize("module_name", ["participants", "sessions", "swallows", "annotations"])
def test_api_database_dependency_closes_session(module_name, monkeypatch):
    module = importlib.import_module(f"api.{module_name}")
    closed = []
    db = SimpleNamespace(close=lambda: closed.append(True))
    monkeypatch.setattr(module, "SessionLocal", lambda: db)

    dependency = module.get_db()
    assert next(dependency) is db
    dependency.close()
    assert closed == [True]


def test_participant_handlers_return_serialized_records_and_404(fake_db_factory):
    from database.models import Participant

    participant = SimpleNamespace(id="P01", age=42, gender="F", dx="anemia")
    db = fake_db_factory({Participant: [participant]})

    assert get_participants(db) == {"participants": [{"id": "P01", "age": 42, "gender": "F", "dx": "anemia"}]}
    assert get_participant("P01", db) == {"id": "P01", "age": 42, "gender": "F", "dx": "anemia"}

    with pytest.raises(HTTPException) as error:
        get_participant("missing", db)
    assert error.value.status_code == 404


def test_session_handlers_support_participant_filter(fake_db_factory):
    from database.models import Session

    sessions = [
        SimpleNamespace(
            id="S01",
            participant_id="P01",
            audio_file_path="audio/P01.wav",
            audio_start_time=1.5,
            aspirating=False,
            total_swallows=2,
            which_swallows="2",
            method_of_drinking="cup",
        ),
        SimpleNamespace(
            id="S02",
            participant_id="P02",
            audio_file_path="audio/P02.wav",
            audio_start_time=0.0,
            aspirating=True,
            total_swallows=1,
            which_swallows=None,
            method_of_drinking=None,
        ),
    ]
    db = fake_db_factory({Session: sessions})

    result = get_sessions(participant_id="P01", db=db)

    assert [session["id"] for session in result["sessions"]] == ["S01"]
    assert result["sessions"][0]["method_of_drinking"] == "cup"
    assert get_session("S01", db)["method_of_drinking"] == "cup"


def test_swallow_handlers_return_session_swallow_data_and_404(fake_db_factory):
    from database.models import Swallow

    swallow = SimpleNamespace(
        id=1, session_id="S01", swallow_number=1, start_time=2.0, end_time=2.5, flagged=True
    )
    db = fake_db_factory({Swallow: [swallow]})

    assert get_swallows(db) == {
        "swallows": [
            {
                "id": 1,
                "session_id": "S01",
                "swallow_number": 1,
                "start_time": 2.0,
                "end_time": 2.5,
                "flagged": True,
            }
        ]
    }
    assert get_swallow(1, db)["session_id"] == "S01"
    assert get_swallows_by_session("S01", db)["swallows"][0]["id"] == 1

    with pytest.raises(HTTPException) as error:
        get_swallows_by_session("missing", db)
    assert error.value.status_code == 404

    with pytest.raises(HTTPException) as error:
        get_swallow("missing", db)
    assert error.value.status_code == 404


def test_session_handler_raises_404_for_missing_session(fake_db_factory):
    with pytest.raises(HTTPException) as error:
        get_session("missing", fake_db_factory())
    assert error.value.status_code == 404