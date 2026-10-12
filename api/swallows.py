from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.models import SessionLocal, Swallow


router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def serialize_swallow(swallow):
    return {
        "id": swallow.id,
        "session_id": swallow.session_id,
        "swallow_number": swallow.swallow_number,
        "start_time": swallow.start_time,
        "end_time": swallow.end_time,
        "flagged": swallow.flagged,
    }


@router.get("/swallows")
def get_swallows(db: Session = Depends(get_db)):
    swallows = db.query(Swallow).all()
    return {"swallows": [serialize_swallow(swallow) for swallow in swallows]}


@router.get("/swallows/{swallow_id}")
def get_swallow(swallow_id: str, db: Session = Depends(get_db)):
    swallow = db.query(Swallow).filter_by(id=swallow_id).first()

    if not swallow:
        raise HTTPException(status_code=404, detail="Swallow not found")

    return serialize_swallow(swallow)


@router.get("/swallows/session/{session_id}")
def get_swallows_by_session(session_id: str, db: Session = Depends(get_db)):
    swallows = db.query(Swallow).filter_by(session_id=session_id).all()

    if not swallows:
        raise HTTPException(status_code=404, detail="Swallows not found for this session")

    swallows = sorted(swallows, key=lambda swallow: swallow.swallow_number)
    return {"swallows": [serialize_swallow(swallow) for swallow in swallows]}
