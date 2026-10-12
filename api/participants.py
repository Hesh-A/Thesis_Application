from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.models import Participant, SessionLocal


router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/participants")
def get_participants(db: Session = Depends(get_db)):
    participants = db.query(Participant).all()
    return {
        "participants": [
            {
                "id": participant.id,
                "age": participant.age,
                "gender": participant.gender,
                "dx": participant.dx,
            }
            for participant in participants
        ]
    }


@router.get("/participants/{participant_id}")
def get_participant(participant_id: str, db: Session = Depends(get_db)):
    participant = db.query(Participant).filter_by(id=participant_id).first()

    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    return {
        "id": participant.id,
        "age": participant.age,
        "gender": participant.gender,
        "dx": participant.dx,
    }