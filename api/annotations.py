from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database.models import Annotation, SessionLocal, Swallow


router = APIRouter()


class AnnotationPayload(BaseModel):
    text: str = ""


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/annotations/swallow/{swallow_id}")
def get_annotation(swallow_id: int, db: Session = Depends(get_db)):
    annotation = db.query(Annotation).filter_by(swallow_id=swallow_id).first()
    if not annotation:
        return {"swallow_id": swallow_id, "text": ""}

    return {
        "swallow_id": swallow_id,
        "text": annotation.text or "",
    }


@router.put("/annotations/swallow/{swallow_id}")
def save_annotation(swallow_id: int, payload: AnnotationPayload, db: Session = Depends(get_db)):
    swallow = db.query(Swallow).filter_by(id=swallow_id).first()
    if not swallow:
        raise HTTPException(status_code=404, detail="Swallow not found")

    annotation = db.query(Annotation).filter_by(swallow_id=swallow_id).first()
    if not annotation:
        annotation = Annotation(swallow_id=swallow_id)
        db.add(annotation)

    annotation.text = payload.text
    db.commit()
    db.refresh(annotation)

    return {
        "swallow_id": swallow_id,
        "text": annotation.text or "",
    }
