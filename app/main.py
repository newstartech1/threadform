"""FastAPI application. Serve the UX and a guarded YouCam REST proxy."""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
import os
import re

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.design import Design, parse_edit, render_design
from app.youcam import YouCamError, create_tryon, poll_tryon, MAX_IMAGE_BYTES

app = FastAPI(title='Threadform Design Studio', version='0.1.0')
ROOT = Path(__file__).resolve().parent
app.mount('/static', StaticFiles(directory=ROOT / 'static'), name='static')


class DesignRequest(BaseModel):
    design: dict = Field(default_factory=dict)


class EditRequest(BaseModel):
    design: dict = Field(default_factory=dict)
    instruction: str = Field(min_length=1, max_length=600)


@app.get('/')
def index():
    return FileResponse(ROOT / 'static' / 'index.html')


@app.get('/api/health')
def health():
    return {'status': 'ok', 'youcam_configured': bool(os.getenv('YOUCAM_API_KEY')),
            'preview_engine': 'deterministic-image-edit', 'youcam_engine': 'cloth-v4'}


@app.post('/api/preview')
def preview(data: DesignRequest):
    try:
        design = Design.from_payload(data.design)
    except (ValueError, TypeError) as exc:
        raise HTTPException(422, detail=str(exc)) from exc
    return Response(content=render_design(design), media_type='image/jpeg',
                    headers={'Cache-Control': 'no-store'})


@app.post('/api/edit')
def edit(data: EditRequest):
    try:
        design = Design.from_payload(data.design)
        updated, changes, message = parse_edit(data.instruction, design)
    except (ValueError, TypeError) as exc:
        raise HTTPException(422, detail=str(exc)) from exc
    return {'design': updated.asdict(), 'changed': changes, 'message': message}


@app.post('/api/tryon')
async def tryon(person: UploadFile = File(...), garment: UploadFile | None = File(None),
                design_json: str = Form('{}')):
    # A server-side API key is mandatory. No fake success behavior.
    if not os.getenv('YOUCAM_API_KEY'):
        raise HTTPException(503, detail='YouCam API is not configured. Set YOUCAM_API_KEY on the server.')
    import json
    try:
        design = Design.from_payload(json.loads(design_json))
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(422, detail=f'Invalid design: {exc}') from exc
    try:
        person_bytes = await person.read(MAX_IMAGE_BYTES + 1)
        if garment is None:
            garment_bytes, garment_name = render_design(design), 'threadform-preview.jpg'
        else:
            garment_bytes, garment_name = await garment.read(MAX_IMAGE_BYTES + 1), garment.filename or 'garment.jpg'
        task_id = create_tryon(person_bytes, person.filename or 'person.jpg', garment_bytes, garment_name)
        return {'task_id': task_id, 'status': 'submitted'}
    except YouCamError as exc:
        raise HTTPException(502, detail=str(exc)) from exc


@app.get('/api/tryon/{task_id}')
def status(task_id: str):
    if not re.fullmatch(r'[A-Za-z0-9_+\-/]{5,180}', task_id):
        raise HTTPException(400, detail='Invalid task ID')
    if not os.getenv('YOUCAM_API_KEY'):
        raise HTTPException(503, detail='YouCam API is not configured.')
    try:
        return poll_tryon(task_id)
    except YouCamError as exc:
        raise HTTPException(502, detail=str(exc)) from exc
