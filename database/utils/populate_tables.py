from pathlib import Path

import pandas as pd
from sqlalchemy.exc import SQLAlchemyError

from database.models import SessionLocal, init_db
from database.utils.import_loaders import load_participant, load_session, load_swallows
from database.utils.import_parsing import (
    SpreadsheetImportError,
    get_row_data,
    validate_required_columns,
)


SPREADSHEET_PATH = Path(__file__).resolve().parents[2] / "Swallow Segmentations_VFSS_03JAN2024_with demographics.xlsx"


def normalize_template(df):
    """Map the worksheet's three header rows to the existing session/swallow columns."""
    if len(df) < 3 or df.shape[1] < 9 or df.iat[1, 1] != "Participant" or df.iat[1, 8] != "Total Swallows":
        return None

    columns = {
        0: "Entry Number",
        1: "Participant",
        2: "Method of drinking",
        3: "Dx",
        4: "Sex",
        5: "Age (mths)",
        6: "Final Audio start",
        8: "Total Swallows",
    }
    for start_col in range(9, df.shape[1] - 1, 2):
        number = df.iat[1, start_col]
        if (pd.isna(number) or str(df.iat[2, start_col]).strip().lower() != "start"
                or str(df.iat[2, start_col + 1]).strip().lower() != "stop"):
            continue
        columns[start_col] = f"Swallow Number {number} Start"
        columns[start_col + 1] = f"Swallow Number {number} Stop"

    data = df.iloc[3:, list(columns)].copy()
    data.columns = list(columns.values())
    return data


def read_spreadsheet(spreadsheet_path):
    try:
        raw = pd.read_excel(spreadsheet_path, header=None)
        template = normalize_template(raw)
        if template is None:
            raise SpreadsheetImportError("Unsupported spreadsheet layout: expected the three-row workbook template")
        return template
    except FileNotFoundError:
        raise SpreadsheetImportError(f"File not found: {spreadsheet_path}") from None
    except PermissionError:
        raise SpreadsheetImportError(
            f"Cannot open {spreadsheet_path}. Close it in Excel and try again."
        ) from None
    except (ValueError, OSError, ImportError) as error:
        raise SpreadsheetImportError(f"Could not read spreadsheet: {error}") from error


def import_spreadsheet(spreadsheet_path):
    """Import the spreadsheet. Returns (rows_processed, warnings); raises SpreadsheetImportError."""
    df = read_spreadsheet(spreadsheet_path)
    if df.empty:
        raise SpreadsheetImportError(f"Spreadsheet has no data rows: {spreadsheet_path}")
    try:
        validate_required_columns(df)
    except ValueError as error:
        raise SpreadsheetImportError(str(error)) from error

    warnings = []
    db = SessionLocal()
    try:
        init_db()
        for row_number, row in df.iterrows():
            excel_row = row_number + 1
            row_data = get_row_data(row, excel_row, warnings)
            if row_data is None:
                continue

            (participant_id, session_id, total_swallows, aspirating, audio_start_time,
             method_of_drinking, dx, sex, age_months) = row_data
            load_participant(db, participant_id, dx, sex, age_months)
            session = load_session(
                db,
                session_id,
                participant_id,
                aspirating,
                total_swallows,
                audio_start_time,
                method_of_drinking,
            )
            flagged_swallows = load_swallows(
                db, df, row, excel_row, session_id, total_swallows, warnings
            )
            session.which_swallows = ",".join(map(str, sorted(flagged_swallows))) or None

        db.commit()
        return len(df), warnings

    except SQLAlchemyError as error:
        db.rollback()
        raise SpreadsheetImportError(f"Database error, no changes were saved: {error}") from error
    except Exception as error:
        db.rollback()
        raise SpreadsheetImportError(f"Unexpected error, no changes were saved: {error!r}") from error
    finally:
        db.close()


def main():
    rows, warnings = import_spreadsheet(SPREADSHEET_PATH)
    for warning in warnings:
        print(warning)
    print(f"Import complete: {rows} row(s) processed")


if __name__ == "__main__":
    main()