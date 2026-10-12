from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from api.annotations import AnnotationPayload, get_annotation, save_annotation
from database.models import Annotation, Swallow

pytestmark = pytest.mark.unit


def test_get_annotation_returns_default_when_none_saved(fake_db_factory):
    db = fake_db_factory({Swallow: [SimpleNamespace(id=1, session_id="S01", start_time=0.0, end_time=1.0)]})

    assert get_annotation(1, db) == {"swallow_id": 1, "text": ""}


def test_get_annotation_returns_saved_text(fake_db_factory):
    annotation = SimpleNamespace(swallow_id=1, text="clinician note")
    db = fake_db_factory({Annotation: [annotation]})

    assert get_annotation(1, db) == {"swallow_id": 1, "text": "clinician note"}


def test_save_annotation_creates_new_record_for_existing_swallow(fake_db_factory):
    swallow = SimpleNamespace(id=1, session_id="S01", start_time=0.0, end_time=1.0)
    db = fake_db_factory({Swallow: [swallow]})

    result = save_annotation(1, AnnotationPayload(text="new note"), db)

    assert result == {"swallow_id": 1, "text": "new note"}
    assert len(db.added) == 1
    assert db.added[0].swallow_id == 1


def test_save_annotation_updates_existing_record(fake_db_factory):
    swallow = SimpleNamespace(id=1, session_id="S01", start_time=0.0, end_time=1.0)
    annotation = Annotation(swallow_id=1, text="old note")
    db = fake_db_factory({Swallow: [swallow], Annotation: [annotation]})

    result = save_annotation(1, AnnotationPayload(text="updated note"), db)

    assert result == {"swallow_id": 1, "text": "updated note"}
    assert db.added == []


def test_save_annotation_raises_404_for_missing_swallow(fake_db_factory):
    db = fake_db_factory()

    with pytest.raises(HTTPException) as error:
        save_annotation(999, AnnotationPayload(text="note"), db)
    assert error.value.status_code == 404
