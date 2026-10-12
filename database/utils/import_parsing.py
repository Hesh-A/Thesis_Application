import re
from numbers import Real

import pandas as pd
from datetime import time


REQUIRED_COLUMNS = ["Participant", "Entry Number", "Total Swallows"]


class SpreadsheetImportError(Exception):
    """Import failed and nothing was written to the database."""


def parse_participant(value):
    text = str(value).strip()
    # Check whether the participant string contains an aspiration tag.
    match = re.fullmatch(r"(.+?)\s*\(\s*(no\s+asp|asp)\s*\)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip(), match.group(2).lower() == "asp"
    # Without a tag, the session's aspiration status is unknown.
    return text, None


def parse_age_months(value):
    if pd.isna(value):
        return None
    try:
        age = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"invalid Age (mths) value: {value}") from None
    if not age.is_integer() or age < 0:
        raise ValueError(f"invalid Age (mths) value: {value}")
    return int(age)


# -----------------------------------------------------
# Validate the TT.TT.TTT format and convert to seconds.
# -----------------------------------------------------

def parse_time_value(value):
    if isinstance(value, time):
        return value.hour * 60 + value.minute + value.second / 1000 + value.microsecond / 1_000_000

    text = str(value).strip()

    try:
        return float(text)
    except ValueError:
        pass

    parts = text.split(".")
    if len(parts) != 3 or not all(part.isdigit() for part in parts):
        raise ValueError(f"invalid time value: {value}")

    first, second, third = (int(part) for part in parts)

    if second >= 60:
        raise ValueError(f"invalid time value: {value}")

    return first * 60 + second + third / 1000


def parse_swallow_time(value):
    if isinstance(value, str):
        time_text, opening, remainder = value.strip().partition("(")
        if opening:
            tag_text, closing, note_text = remainder.partition(")")
            if closing and tag_text.strip() and (not note_text or note_text[0].isspace()):
                tag = tag_text.strip().lower()
                aspiration = True if tag == "asp" else False if tag == "no asp" else None
                notes = [part for part in (tag_text.strip() if aspiration is None else "",
                                           note_text.strip()) if part]
                return parse_time_value(time_text), aspiration, " ".join(notes) or None
    return parse_time_value(value), None, None


def validate_required_columns(df):
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")



# -----------------------------
# Extract and validate row data
# -----------------------------


def get_row_data(row, excel_row, warnings):
    if pd.isna(row["Participant"]) or pd.isna(row["Entry Number"]) or pd.isna(row["Total Swallows"]):
        warnings.append(f"Row {excel_row}: skipped, missing required data")
        return None

    participant_id, aspirating = parse_participant(row["Participant"])
    entry_number = row["Entry Number"]
    session_id = (str(int(entry_number)) if isinstance(entry_number, Real) and
                  float(entry_number).is_integer() else str(entry_number).strip())

    if not participant_id or not session_id:
        warnings.append(f"Row {excel_row}: skipped, empty participant or session id")
        return None

    try:
        total_swallows = int(row["Total Swallows"])
        audio_start_time = parse_time_value(row["Final Audio start"])
    except (TypeError, ValueError) as error:
        warnings.append(f"Row {excel_row}: skipped, {error}")
        return None

    if total_swallows < 0:
        warnings.append(f"Row {excel_row}: skipped, Total Swallows cannot be negative")
        return None

    try:
        age_months = parse_age_months(row["Age (mths)"])
    except ValueError as error:
        warnings.append(f"Row {excel_row}: {error}, age omitted")
        age_months = None

    return (participant_id, session_id, total_swallows, aspirating, audio_start_time,
            row["Method of drinking"], row["Dx"], row["Sex"], age_months)