from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.models import SessionLocal, Session as SwallowSession


router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/sessions")
def get_sessions(participant_id: str | None = None, db: Session = Depends(get_db)):

    query = db.query(SwallowSession)

    if participant_id is not None:
        query = query.filter_by(participant_id=participant_id)

    sessions = query.all()
    return {
        "sessions": [
            {
                "id": session.id,
                "participant_id": session.participant_id,
                "audio_file_path": session.audio_file_path,
                "audio_start_time": session.audio_start_time,
                "aspirating": session.aspirating,
                "total_swallows": session.total_swallows,
                "which_swallows": session.which_swallows,
                "method_of_drinking": session.method_of_drinking,
            }
            for session in sessions
        ]
    }

@router.get("/sessions/{session_id}")
def get_session(session_id: str, db: Session = Depends(get_db)):
    session = db.query(SwallowSession).filter_by(id=session_id).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "id": session.id,
        "participant_id": session.participant_id,
        "audio_file_path": session.audio_file_path,
        "audio_start_time": session.audio_start_time,
        "aspirating": session.aspirating,
        "total_swallows": session.total_swallows,
        "which_swallows": session.which_swallows,
        "method_of_drinking": session.method_of_drinking,
    }