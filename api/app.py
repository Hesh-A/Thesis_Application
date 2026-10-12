from fastapi import FastAPI

from api.annotations import router as annotations_router
from api.participants import router as participants_router
from api.sessions import router as session_router
from api.swallows import router as swallows_router
from database.models import init_db

app = FastAPI()
init_db()

app.include_router(participants_router, prefix="/api")
app.include_router(session_router, prefix="/api")
app.include_router(swallows_router, prefix="/api")
app.include_router(annotations_router, prefix="/api")


@app.get("/")
def home():
    return {"message": "Backend is running!"}
