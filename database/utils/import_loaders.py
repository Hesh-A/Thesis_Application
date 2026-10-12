import pandas as pd

from database.models import Participant, Session, Swallow
from database.utils.import_parsing import parse_swallow_time, parse_time_value

# -----------------------------
# Load data into the database
# -----------------------------

def clean_text(value):
    return None if pd.isna(value) or not str(value).strip() else str(value).strip()


def load_participant(db, participant_id, dx=None, sex=None, age=None):
    participant = db.query(Participant).filter_by(id=participant_id).first()
    if participant is None:
        participant = Participant(id=participant_id)
        db.add(participant)

    dx = clean_text(dx)
    sex = clean_text(sex)
    if dx is not None:
        participant.dx = dx
    if sex is not None:
        participant.gender = sex
    if age is not None and not pd.isna(age):
        participant.age = int(age)


# -------------------------------------------
# Load swallow sessions based on the entry_id
# -------------------------------------------

def load_session(
    db,
    session_id,
    participant_id,
    aspirating,
    total_swallows,
    audio_start_time,
    method_of_drinking=None,
):
    session = db.query(Session).filter_by(id=session_id).first()
    if session is None:
        session = Session(
            id=session_id,
            participant_id=participant_id,
            audio_file_path=f"audio/{participant_id}.wav",
        )
        db.add(session)

    session.audio_start_time = audio_start_time
    session.aspirating = aspirating
    session.total_swallows = total_swallows
    method = clean_text(method_of_drinking)
    if method is not None:
        session.method_of_drinking = method
    return session


# -------------------------------------------------------
# Load swallows based on the partcipant_id and session_id
# -------------------------------------------------------

def load_swallows(db, df, row, excel_row, session_id, total_swallows, warnings):
    flagged_swallows = set()
    for i in range(1, total_swallows + 1):
        start_col = f"Swallow Number {i} Start"
        stop_col = f"Swallow Number {i} Stop"

        if start_col not in df.columns or stop_col not in df.columns:
            warnings.append(f"Row {excel_row}: swallow {i} skipped, missing column")
            continue

        start = row[start_col]
        stop = row[stop_col]

        # Empty pairs are allowed, but half-filled pairs are treated as invalid data.
        if pd.isna(start) and pd.isna(stop):
            continue

        if pd.isna(start) or pd.isna(stop):
            warnings.append(f"Row {excel_row}: swallow {i} skipped, start or stop is missing")
            continue

        try:
            start_time = parse_time_value(start)
            end_time, tagged_asp, end_note = parse_swallow_time(stop)
        except (TypeError, ValueError) as error:
            warnings.append(f"Row {excel_row}: swallow {i} skipped, {error}")
            continue

        if end_note:
            warnings.append(f"Row {excel_row}: swallow {i} note not imported: {end_note}")

        # A swallow cannot end before it starts.
        if end_time < start_time:
            warnings.append(f"Row {excel_row}: swallow {i} skipped, end before start")
            continue

        flagged = tagged_asp is True
        if flagged:
            flagged_swallows.add(i)
        swallow = db.query(Swallow).filter_by(
            session_id=session_id,
            swallow_number=i,
        ).first()
        if swallow is None:
            swallow = Swallow(
                session_id=session_id,
                swallow_number=i,
            )
            db.add(swallow)
        swallow.start_time = start_time
        swallow.end_time = end_time
        swallow.flagged = flagged
    return flagged_swallows