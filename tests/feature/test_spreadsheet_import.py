from types import SimpleNamespace

import pandas as pd
import pytest

from database.utils.import_parsing import (
    get_row_data,
    validate_required_columns,
)
from database.utils.populate_tables import read_spreadsheet


def make_template(records, swallow_count):
    rows = [[None] * (9 + 2 * swallow_count) for _ in range(3 + len(records))]
    rows[1][1] = "Participant"
    rows[1][8] = "Total Swallows"
    rows[2][2:6] = ["Method of drinking", "Dx", "Sex", "Age (mths)"]
    for number in range(1, swallow_count + 1):
        start_column = 9 + (number - 1) * 2
        rows[1][start_column] = number
        rows[2][start_column:start_column + 2] = ["Start", "Stop"]

    columns = {
        "Entry Number": 0,
        "Participant": 1,
        "Method of drinking": 2,
        "Dx": 3,
        "Sex": 4,
        "Age (mths)": 5,
        "Final Audio start": 6,
        "Total Swallows": 8,
    }
    for row_number, record in enumerate(records, start=3):
        for name, column in columns.items():
            rows[row_number][column] = record.get(name)
        for number in range(1, swallow_count + 1):
            start_column = 9 + (number - 1) * 2
            rows[row_number][start_column] = record.get(f"Swallow Number {number} Start")
            rows[row_number][start_column + 1] = record.get(f"Swallow Number {number} Stop")
    return pd.DataFrame(rows)


def write_template(path, records, swallow_count):
    make_template(records, swallow_count).to_excel(path, header=False, index=False)


@pytest.mark.feature
def test_read_spreadsheet_normalizes_three_row_template(tmp_path):
    path = tmp_path / "template.xlsx"
    write_template(path, [{
        "Entry Number": "S01", "Participant": "P01 (asp)", "Total Swallows": 2,
        "Final Audio start": "00.12.500", "Swallow Number 1 Start": "00.13.000",
        "Swallow Number 1 Stop": "00.14.000", "Swallow Number 2 Start": "00.15.000",
        "Swallow Number 2 Stop": "00.16.000",
    }], 2)

    data = read_spreadsheet(path)
    validate_required_columns(data)
    warnings = []
    row_data = get_row_data(data.iloc[0], 4, warnings)
    assert row_data[:5] == ("P01", "S01", 2, True, 12.5)
    assert all(pd.isna(value) for value in row_data[5:8])
    assert row_data[8] is None
    assert "Aspirating" not in data.columns
    assert "Which Swallows" not in data.columns
    assert data.iloc[0]["Swallow Number 2 Stop"] == "00.16.000"
    assert warnings == []


@pytest.mark.feature
def test_import_template_derives_session_and_swallow_aspiration(tmp_path, monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from database.models import Base, Participant, Session, Swallow
    from database.utils import populate_tables

    path = tmp_path / "tagged.xlsx"
    records = [
        {
            "Entry Number": "S01", "Participant": "P64 (asp)", "Total Swallows": 2,
            "Final Audio start": "00.12.500", "Swallow Number 1 Start": "7.45.169",
            "Swallow Number 1 Stop": "7.45.829 (asp)", "Swallow Number 2 Start": "7.47.116",
            "Swallow Number 2 Stop": "7.47.938 (no asp)",
        },
        {
            "Entry Number": "S02", "Participant": "P65 (no asp)", "Total Swallows": 1,
            "Final Audio start": "00.12.500", "Swallow Number 1 Start": "7.45.169",
            "Swallow Number 1 Stop": "7.45.829 (no asp)",
        },
    ]
    write_template(path, records, 2)

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db_factory = sessionmaker(bind=engine, autoflush=False)
    monkeypatch.setattr(populate_tables, "SessionLocal", db_factory)
    monkeypatch.setattr(populate_tables, "init_db", lambda: None)

    assert populate_tables.import_spreadsheet(path) == (2, [])
    with db_factory() as db:
        assert {participant.id for participant in db.query(Participant)} == {"P64", "P65"}
        sessions = {session.id: session for session in db.query(Session)}
        assert sessions["S01"].aspirating is True
        assert sessions["S01"].which_swallows == "1"
        assert sessions["S02"].aspirating is False
        assert sessions["S02"].which_swallows is None
        swallows = {(swallow.session_id, swallow.swallow_number): swallow for swallow in db.query(Swallow)}
        assert swallows["S01", 1].flagged is True
        assert swallows["S01", 1].end_time == pytest.approx(465.829)
        assert swallows["S01", 2].flagged is False
        assert swallows["S02", 1].flagged is False

    records[0]["Participant"] = "P64 (no asp)"
    records[0]["Swallow Number 1 Stop"] = "7.45.829 (no asp)"
    write_template(path, records, 2)
    assert populate_tables.import_spreadsheet(path) == (2, [])
    with db_factory() as db:
        assert db.query(Session).filter_by(id="S01").one().aspirating is False
        assert db.query(Session).filter_by(id="S01").one().which_swallows is None
        assert db.query(Swallow).filter_by(session_id="S01", swallow_number=1).one().flagged is False


@pytest.mark.feature
def test_read_spreadsheet_rejects_flat_headers(tmp_path):
    path = tmp_path / "flat.xlsx"
    pd.DataFrame([{"Participant": "P01 (asp)", "Entry Number": "S01",
                   "Total Swallows": 0, "Final Audio start": 0}]).to_excel(path, index=False)

    from database.utils.import_parsing import SpreadsheetImportError

    with pytest.raises(SpreadsheetImportError, match="Unsupported spreadsheet layout"):
        read_spreadsheet(path)


@pytest.mark.parametrize(
    ("error", "message"),
    [(FileNotFoundError(), "File not found"), (PermissionError(), "Close it in Excel"),
     (ValueError("bad workbook"), "Could not read spreadsheet")],
)
@pytest.mark.feature
def test_read_spreadsheet_reports_file_errors(monkeypatch, error, message):
    from database.utils import populate_tables
    from database.utils.import_parsing import SpreadsheetImportError

    def fail_read(*args, **kwargs):
        raise error

    monkeypatch.setattr(populate_tables.pd, "read_excel", fail_read)
    with pytest.raises(SpreadsheetImportError, match=message):
        populate_tables.read_spreadsheet("missing.xlsx")


@pytest.mark.feature
def test_import_spreadsheet_rejects_missing_columns_before_opening_database(monkeypatch):
    from database.utils import populate_tables
    from database.utils.import_parsing import SpreadsheetImportError

    monkeypatch.setattr(populate_tables, "read_spreadsheet", lambda path: pd.DataFrame({"Participant": ["P01"]}))
    monkeypatch.setattr(populate_tables, "SessionLocal", lambda: pytest.fail("Database opened"))
    with pytest.raises(SpreadsheetImportError, match="Missing required columns"):
        populate_tables.import_spreadsheet("missing-columns.xlsx")


@pytest.mark.feature
def test_import_warns_about_invalid_age_and_skips_incomplete_row(monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from database.models import Base, Participant
    from database.utils import populate_tables

    frame = pd.DataFrame([
        {"Participant": "P01 (asp)", "Entry Number": "S01",
         "Total Swallows": 0, "Final Audio start": 0, "Age (mths)": "unknown",
         "Method of drinking": None, "Dx": None, "Sex": None},
        {"Participant": None, "Entry Number": "S02",
         "Total Swallows": 0, "Final Audio start": 0},
    ], index=[3, 4])
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db_factory = sessionmaker(bind=engine)
    monkeypatch.setattr(populate_tables, "read_spreadsheet", lambda path: frame)
    monkeypatch.setattr(populate_tables, "SessionLocal", db_factory)
    monkeypatch.setattr(populate_tables, "init_db", lambda: None)

    rows, warnings = populate_tables.import_spreadsheet("synthetic.xlsx")
    assert rows == 2
    assert any("age omitted" in warning for warning in warnings)
    assert any("Row 5: skipped" in warning for warning in warnings)
    with db_factory() as db:
        assert db.query(Participant).one().age is None


@pytest.mark.parametrize(
    ("error", "message"),
    [("database", "Database error"), ("unexpected", "Unexpected error")],
)
@pytest.mark.feature
def test_import_rolls_back_and_closes_after_unexpected_failure(monkeypatch, error, message):
    from sqlalchemy.exc import SQLAlchemyError

    from database.utils import populate_tables
    from database.utils.import_parsing import SpreadsheetImportError

    actions = []
    db = SimpleNamespace(rollback=lambda: actions.append("rollback"),
                         close=lambda: actions.append("close"))
    frame = pd.DataFrame([{"Participant": "P01", "Entry Number": "S01",
                           "Total Swallows": 0}])
    monkeypatch.setattr(populate_tables, "read_spreadsheet", lambda path: frame)
    monkeypatch.setattr(populate_tables, "SessionLocal", lambda: db)

    def fail_init():
        if error == "database":
            raise SQLAlchemyError("broken")
        raise RuntimeError("broken")

    monkeypatch.setattr(populate_tables, "init_db", fail_init)
    with pytest.raises(SpreadsheetImportError, match=message):
        populate_tables.import_spreadsheet("synthetic.xlsx")
    assert actions == ["rollback", "close"]


@pytest.mark.feature
def test_template_metadata_is_saved_to_participant_and_session(tmp_path, monkeypatch):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from database.models import Base, Participant, Session
    from database.utils import populate_tables

    path = tmp_path / "metadata.xlsx"
    records = [{
        "Entry Number": "S01", "Participant": "P64 (asp)", "Method of drinking": "cup",
        "Dx": "anemia", "Sex": "F", "Age (mths)": 18, "Total Swallows": 1,
        "Final Audio start": "00.12.500", "Swallow Number 1 Start": "7.45.169",
        "Swallow Number 1 Stop": "7.45.829 (asp)",
    }]
    write_template(path, records, 1)

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db_factory = sessionmaker(bind=engine, autoflush=False)
    monkeypatch.setattr(populate_tables, "SessionLocal", db_factory)
    monkeypatch.setattr(populate_tables, "init_db", lambda: None)

    assert populate_tables.import_spreadsheet(path) == (1, [])
    with db_factory() as db:
        participant = db.query(Participant).one()
        assert (participant.id, participant.dx, participant.gender, participant.age) == (
            "P64", "anemia", "F", 18
        )
        assert db.query(Session).one().method_of_drinking == "cup"

    records[0].update({"Method of drinking": "spoon", "Dx": None, "Sex": None, "Age (mths)": None})
    write_template(path, records, 1)
    assert populate_tables.import_spreadsheet(path) == (1, [])
    with db_factory() as db:
        participant = db.query(Participant).one()
        assert (participant.dx, participant.gender, participant.age) == ("anemia", "F", 18)
        assert db.query(Session).one().method_of_drinking == "spoon"


@pytest.mark.feature
def test_swallow_loader_warns_for_incomplete_and_invalid_pairs():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from database.models import Base, Swallow
    from database.utils.import_loaders import load_swallows

    row = pd.Series({
        "Swallow Number 1 Start": "1.00.000",
        "Swallow Number 1 Stop": "1.00.500 (asp) cough",
        "Swallow Number 2 Start": "1.00.000", "Swallow Number 2 Stop": "1.00.500",
        "Swallow Number 3 Start": "1.00.000", "Swallow Number 3 Stop": None,
        "Swallow Number 4 Start": "invalid", "Swallow Number 4 Stop": "1.00.500",
        "Swallow Number 5 Start": "1.00.000",
        "Swallow Number 5 Stop": "1.00.500 (no asp)",
        "Swallow Number 6 Start": "1.00.500", "Swallow Number 6 Stop": "1.00.000",
    })
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    warnings = []
    with sessionmaker(bind=engine)() as db:
        flagged = load_swallows(db, row.to_frame().T, row, 4, "S01", 7, warnings)
        assert flagged == {1}
        assert [(item.swallow_number, item.flagged) for item in db.query(Swallow)] == [
            (1, True), (2, False), (5, False)
        ]

    assert any("note not imported: cough" in warning for warning in warnings)
    assert any("swallow 3 skipped, start or stop is missing" in warning for warning in warnings)
    assert any("swallow 4 skipped, invalid time" in warning for warning in warnings)
    assert any("swallow 6 skipped, end before start" in warning for warning in warnings)
    assert any("swallow 7 skipped, missing column" in warning for warning in warnings)


@pytest.mark.feature
def test_empty_template_does_not_touch_database(tmp_path, monkeypatch):
    from database.utils import populate_tables
    from database.utils.import_parsing import SpreadsheetImportError

    path = tmp_path / "empty.xlsx"
    rows = [[None] * 11 for _ in range(3)]
    rows[1][1] = "Participant"
    rows[1][8] = "Total Swallows"
    rows[1][9] = 1
    rows[2][9:11] = ["Start", "Stop"]
    pd.DataFrame(rows).to_excel(path, header=False, index=False)
    monkeypatch.setattr(populate_tables, "SessionLocal", lambda: pytest.fail("Database opened"))

    with pytest.raises(SpreadsheetImportError, match="no data rows"):
        populate_tables.import_spreadsheet(path)