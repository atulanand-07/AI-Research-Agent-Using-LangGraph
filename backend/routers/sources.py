"""Source upload, Wikipedia source, and source deletion endpoints."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, File, Header, UploadFile

from ..ingestion.source_processor import process_pdf_source, process_wikipedia_source
from ..retrieval.vector_store import vector_store
from ..session_store import session_store
from ..state import SourceStatus
from .schemas import SourceResponse, WikiRequest

router = APIRouter()
UPLOAD_DIR = Path(__file__).resolve().parents[1] / "data" / "uploads"


def _session_id(value: str | None) -> str:
    return value or "default"


@router.post("/upload", response_model=SourceResponse)
async def upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    x_session_id: str | None = Header(default=None),
):
    session_id = _session_id(x_session_id)
    source_id = uuid4().hex
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    target = UPLOAD_DIR / f"{source_id}_{file.filename}"
    target.write_bytes(await file.read())
    source = {
        "id": source_id,
        "filename": file.filename,
        "source_type": "pdf",
        "status": SourceStatus.PENDING,
        "vector_ref": None,
    }
    session = session_store.get(session_id)
    session["uploaded_sources"].append(source)
    session_store.update(session_id, uploaded_sources=session["uploaded_sources"])
    background_tasks.add_task(process_pdf_source, session_id, source_id, str(target))
    return {"source_id": source_id, "status": SourceStatus.PENDING}


@router.post("/wiki", response_model=SourceResponse)
def wiki(
    request: WikiRequest,
    background_tasks: BackgroundTasks,
    x_session_id: str | None = Header(default=None),
):
    session_id = _session_id(x_session_id)
    source_id = uuid4().hex
    source = {
        "id": source_id,
        "filename": request.url_or_topic,
        "source_type": "wikipedia",
        "status": SourceStatus.PENDING,
        "vector_ref": None,
    }
    session = session_store.get(session_id)
    session["uploaded_sources"].append(source)
    session_store.update(session_id, uploaded_sources=session["uploaded_sources"])
    background_tasks.add_task(process_wikipedia_source, session_id, source_id, request.url_or_topic)
    return {"source_id": source_id, "status": SourceStatus.PENDING}


@router.delete("/source/{source_id}")
def delete_source(source_id: str, x_session_id: str | None = Header(default=None)):
    session_id = _session_id(x_session_id)
    session = session_store.get(session_id)
    remaining = []
    deleted = None
    for source in session["uploaded_sources"]:
        if source["id"] == source_id:
            deleted = source
        else:
            remaining.append(source)
    if deleted:
        vector_store.delete_source(deleted.get("vector_ref"))
    session_store.update(session_id, uploaded_sources=remaining)
    return {"deleted": bool(deleted)}

