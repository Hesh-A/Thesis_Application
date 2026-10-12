import sqlite3
import wave
from zipfile import ZipFile

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import Annotation, Base, Participant, Session, Swallow
from database.utils.project_archive import export_project, import_project


def make_project(tmp_path):
    project = tmp_path / "source"
    (project / "database").mkdir(parents=True)
    (project / "audio").mkdir()
    audio_path = project / "audio" / "P01.wav"
    with wave.open(str(audio_path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(8000)
        audio.writeframes(b"\x00\x00" * 16)

    engine = create_engine(f"sqlite:///{(project / 'database' / 'swallow.db').as_posix()}")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as db:
        db.add(Participant(id="P01"))
        db.add(Session(id="S01", participant_id="P01", audio_file_path="audio/P01.wav"))
        swallow = Swallow(session_id="S01", swallow_number=1, start_time=0.0, end_time=0.1)
        db.add(swallow)
        db.flush()
        db.add(Annotation(swallow_id=swallow.id, text="reviewed"))
        db.commit()
    engine.dispose()
    return project


@pytest.fixture
def project(tmp_path):
    return make_project(tmp_path)


@pytest.mark.feature
def test_export_project_contains_database_audio_and_annotations(tmp_path, project):
    archive_path = tmp_path / "review.swallowproj"

    export_project(project, archive_path)

    with ZipFile(archive_path) as archive:
        assert set(archive.namelist()) == {"database/swallow.db", "audio/P01.wav"}
        assert archive.read("audio/P01.wav") == (project / "audio" / "P01.wav").read_bytes()
        extracted_db = tmp_path / "snapshot.db"
        extracted_db.write_bytes(archive.read("database/swallow.db"))
    with sqlite3.connect(extracted_db) as db:
        assert db.execute("SELECT audio_file_path FROM sessions").fetchone() == ("audio/P01.wav",)
        assert db.execute("SELECT text FROM annotations").fetchone() == ("reviewed",)
    assert (project / "database" / "swallow.db").exists()


@pytest.mark.feature
def test_export_project_rejects_missing_audio_without_creating_archive(tmp_path, project):
    (project / "audio" / "P01.wav").unlink()
    archive_path = tmp_path / "incomplete.swallowproj"

    with pytest.raises(ValueError, match="Missing audio"):
        export_project(project, archive_path)
    assert not archive_path.exists()


@pytest.mark.feature
def test_test_export_skips_missing_audio_only_in_archive_snapshot(tmp_path, project):
    (project / "audio" / "P01.wav").unlink()
    archive_path = tmp_path / "test-only.swallowproj"

    missing = export_project(project, archive_path, skip_missing_audio=True)

    assert missing == ["audio/P01.wav"]
    with ZipFile(archive_path) as archive:
        assert archive.namelist() == ["database/swallow.db"]
    opened = tmp_path / "opened"
    import_project(archive_path, opened)
    with sqlite3.connect(opened / "database" / "swallow.db") as copy:
        assert copy.execute("SELECT audio_file_path FROM sessions").fetchone() == (None,)
        assert copy.execute("SELECT text FROM annotations").fetchone() == ("reviewed",)
    with sqlite3.connect(project / "database" / "swallow.db") as original:
        assert original.execute("SELECT audio_file_path FROM sessions").fetchone() == ("audio/P01.wav",)


@pytest.mark.feature
def test_export_project_does_not_replace_an_existing_archive(tmp_path, project):
    archive_path = tmp_path / "existing.swallowproj"
    archive_path.write_bytes(b"existing backup")

    with pytest.raises(FileExistsError):
        export_project(project, archive_path)
    assert archive_path.read_bytes() == b"existing backup"


@pytest.mark.feature
def test_import_project_opens_isolated_copy_with_relative_audio(tmp_path, project):
    archive_path = tmp_path / "review.swallowproj"
    export_project(project, archive_path)
    destination = tmp_path / "opened"

    import_project(archive_path, destination)

    with sqlite3.connect(destination / "database" / "swallow.db") as db:
        audio_path = db.execute("SELECT audio_file_path FROM sessions").fetchone()[0]
        assert db.execute("SELECT text FROM annotations").fetchone() == ("reviewed",)
    assert (destination / audio_path).read_bytes() == (project / audio_path).read_bytes()
    assert (project / "database" / "swallow.db").exists()

    with pytest.raises(FileExistsError):
        import_project(archive_path, destination)


@pytest.mark.feature
def test_import_project_rejects_unsafe_archive_without_extraction(tmp_path):
    archive_path = tmp_path / "unsafe.swallowproj"
    with ZipFile(archive_path, "w") as archive:
        archive.writestr("database/swallow.db", b"not a database")
        archive.writestr("../outside.wav", b"data")

    with pytest.raises(ValueError, match="Unsafe archive entry"):
        import_project(archive_path, tmp_path / "opened")
    assert not (tmp_path / "opened").exists()
    assert not (tmp_path / "outside.wav").exists()


@pytest.mark.feature
def test_import_project_rejects_missing_audio_and_invalid_database(tmp_path, project):
    archive_path = tmp_path / "incomplete.swallowproj"
    with ZipFile(archive_path, "w") as archive:
        archive.write(project / "database" / "swallow.db", "database/swallow.db")
    with pytest.raises(ValueError, match="Missing audio in archive"):
        import_project(archive_path, tmp_path / "opened")
    assert not (tmp_path / "opened").exists()

    damaged = tmp_path / "damaged.swallowproj"
    with ZipFile(damaged, "w") as archive:
        archive.writestr("database/swallow.db", b"not a database")
    with pytest.raises(ValueError, match="Invalid project database"):
        import_project(damaged, tmp_path / "opened")
    assert not (tmp_path / "opened").exists()


@pytest.mark.feature
def test_startup_selection_accepts_extracted_project(project, monkeypatch):
    from main import select_project

    monkeypatch.delenv("SWALLOW_PROJECT_ROOT", raising=False)
    assert select_project(["--project", str(project)]) == []
    assert __import__("os").environ["SWALLOW_PROJECT_ROOT"] == str(project)






