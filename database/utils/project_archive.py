from contextlib import closing
from pathlib import Path, PurePosixPath
import shutil
import sqlite3
import stat
from tempfile import TemporaryDirectory
from zipfile import ZIP_DEFLATED, ZipFile


def _audio_member(value):
    if not isinstance(value, str):
        raise ValueError(f"Unsupported audio path: {value}")
    name = PurePosixPath(value)
    if (name.is_absolute() or ".." in name.parts or len(name.parts) < 2
            or name.parts[0] != "audio" or "\\" in value or name.as_posix() != value):
        raise ValueError(f"Unsupported audio path: {value}")
    return name.as_posix()


def _audio_paths(db):
    rows = db.execute("SELECT audio_file_path FROM sessions WHERE audio_file_path IS NOT NULL")
    return {row[0] for row in rows}


def export_project(project_root, archive_path, *, skip_missing_audio=False):
    root = Path(project_root).resolve()
    database_path = root / "database" / "swallow.db"
    destination = Path(archive_path)
    if not database_path.is_file():
        raise FileNotFoundError(f"Project database not found: {database_path}")

    with TemporaryDirectory() as temporary:
        snapshot = Path(temporary) / "swallow.db"
        with closing(sqlite3.connect(database_path)) as source, closing(sqlite3.connect(snapshot)) as target:
            source.backup(target)

        with closing(sqlite3.connect(snapshot)) as db:
            audio_paths = _audio_paths(db)

        recordings = {}
        missing = []
        for value in audio_paths:
            name = _audio_member(value)
            audio_path = (root / name).resolve()
            if not audio_path.is_relative_to(root / "audio"):
                raise ValueError(f"Unsupported audio path: {value}")
            if not audio_path.is_file():
                if not skip_missing_audio:
                    raise ValueError(f"Missing audio: {value}")
                missing.append(value)
                continue
            recordings[name] = audio_path

        if missing:
            with closing(sqlite3.connect(snapshot)) as db:
                for value in missing:
                    db.execute(
                        "UPDATE sessions SET audio_file_path = NULL WHERE audio_file_path = :path",
                        {"path": value},
                    )
                db.commit()

        try:
            with ZipFile(destination, "x", compression=ZIP_DEFLATED, allowZip64=True) as archive:
                archive.write(snapshot, "database/swallow.db")
                for name, path in sorted(recordings.items()):
                    archive.write(path, name)
        except FileExistsError:
            raise
        except Exception:
            destination.unlink(missing_ok=True)
            raise
    return sorted(missing)


def import_project(archive_path, destination_path):
    destination = Path(destination_path)
    if destination.exists():
        raise FileExistsError(f"Project folder already exists: {destination}")

    with ZipFile(archive_path) as archive:
        entries = {}
        for info in archive.infolist():
            name = info.filename
            if info.is_dir() or name in entries or stat.S_ISLNK(info.external_attr >> 16):
                raise ValueError(f"Unsafe archive entry: {name}")
            if name != "database/swallow.db":
                try:
                    _audio_member(name)
                except ValueError:
                    raise ValueError(f"Unsafe archive entry: {name}") from None
            entries[name] = info
        if "database/swallow.db" not in entries:
            raise ValueError("Archive has no project database")

        with TemporaryDirectory(dir=destination.parent) as temporary:
            project = Path(temporary) / "project"
            project.mkdir()
            for name, info in entries.items():
                target = project / name
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as source, target.open("xb") as output:
                    shutil.copyfileobj(source, output)

            try:
                with closing(sqlite3.connect((project / "database" / "swallow.db").as_uri() + "?mode=ro", uri=True)) as db:
                    if db.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                        raise ValueError("Invalid project database")
                    audio_paths = _audio_paths(db)
            except sqlite3.DatabaseError as error:
                raise ValueError("Invalid project database") from error
            for value in audio_paths:
                name = _audio_member(value)
                if name not in entries:
                    raise ValueError(f"Missing audio in archive: {value}")
            project.rename(destination)
    return destination