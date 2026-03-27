from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .db import BASE_DIR, get_connection, init_db
from .ocr_service import run_ocr

UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_TYPES = {"image/png", "image/jpeg", "image/webp"}

app = FastAPI(title="OCR TPV API")


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:4200",
        "http://127.0.0.1:4200",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    init_db()


app.mount("/media", StaticFiles(directory=str(UPLOADS_DIR)), name="media")


def _serialize_upload_row(row) -> dict:
    item = dict(row)
    item["url"] = f"http://localhost:8000/media/{item['stored_name']}"

    phone_candidates = item.get("phone_candidates")
    name_candidates = item.get("name_candidates")

    item["phone_candidates"] = json.loads(phone_candidates) if phone_candidates else []
    item["name_candidates"] = json.loads(name_candidates) if name_candidates else []

    return item


def _get_upload_or_404(upload_id: int):
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT
                iu.id,
                iu.original_name,
                iu.stored_name,
                iu.file_path,
                iu.mime_type,
                iu.size_bytes,
                iu.created_at,
                iu.ocr_status,
                iu.ocr_processed_at,
                iu.ocr_error,
                o.id AS ocr_id,
                o.raw_text,
                o.line_count,
                o.avg_confidence,
                o.parsed_name,
                o.parsed_phone,
                o.phone_candidates,
                o.name_candidates
            FROM image_uploads iu
            LEFT JOIN ocr_results o ON o.upload_id = iu.id
            WHERE iu.id = ?
            """,
            (upload_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="No existe esa subida.")

    return row


def _process_upload(upload_id: int) -> dict:
    upload_row = _get_upload_or_404(upload_id)
    image_path = BASE_DIR / upload_row["file_path"]

    if not image_path.exists():
        raise HTTPException(status_code=404, detail="No se encuentra la imagen en disco.")

    now = datetime.now(timezone.utc).isoformat()

    with get_connection() as conn:
        conn.execute(
            """
            UPDATE image_uploads
            SET ocr_status = ?, ocr_error = NULL
            WHERE id = ?
            """,
            ("processing", upload_id),
        )
        conn.commit()

    try:
        result = run_ocr(image_path)
    except Exception as exc:
        with get_connection() as conn:
            conn.execute(
                """
                UPDATE image_uploads
                SET ocr_status = ?, ocr_error = ?, ocr_processed_at = ?
                WHERE id = ?
                """,
                ("error", str(exc), now, upload_id),
            )
            conn.commit()

        raise HTTPException(status_code=500, detail=f"OCR falló: {exc}") from exc

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO ocr_results (
                upload_id,
                raw_text,
                line_count,
                avg_confidence,
                parsed_name,
                parsed_phone,
                phone_candidates,
                name_candidates,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(upload_id)
            DO UPDATE SET
                raw_text = excluded.raw_text,
                line_count = excluded.line_count,
                avg_confidence = excluded.avg_confidence,
                parsed_name = excluded.parsed_name,
                parsed_phone = excluded.parsed_phone,
                phone_candidates = excluded.phone_candidates,
                name_candidates = excluded.name_candidates,
                updated_at = excluded.updated_at
            """,
            (
                upload_id,
                result["raw_text"],
                len(result["lines"]),
                result["avg_confidence"],
                result["parsed_name"],
                result["parsed_phone"],
                json.dumps(result["phone_candidates"], ensure_ascii=False),
                json.dumps(result["name_candidates"], ensure_ascii=False),
                now,
                now,
            ),
        )

        conn.execute(
            """
            UPDATE image_uploads
            SET ocr_status = ?, ocr_error = NULL, ocr_processed_at = ?
            WHERE id = ?
            """,
            ("done", now, upload_id),
        )
        conn.commit()

    processed = _get_upload_or_404(upload_id)
    return _serialize_upload_row(processed)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/uploads")
async def create_upload(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="El archivo no tiene nombre.")

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Solo se permiten imágenes PNG, JPG/JPEG o WEBP.",
        )

    suffix = Path(file.filename).suffix.lower() or ".bin"
    stored_name = f"{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}.{suffix.lstrip('.')}"
    destination = UPLOADS_DIR / stored_name

    try:
        with destination.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        await file.close()

    size_bytes = destination.stat().st_size
    created_at = datetime.now(timezone.utc).isoformat()
    file_path = f"uploads/{stored_name}"

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO image_uploads (
                original_name,
                stored_name,
                file_path,
                mime_type,
                size_bytes,
                created_at,
                ocr_status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                file.filename,
                stored_name,
                file_path,
                file.content_type,
                size_bytes,
                created_at,
                "pending",
            ),
        )
        conn.commit()
        upload_id = cursor.lastrowid

    return _serialize_upload_row(_get_upload_or_404(upload_id))


@app.get("/uploads")
def list_uploads():
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                iu.id,
                iu.original_name,
                iu.stored_name,
                iu.file_path,
                iu.mime_type,
                iu.size_bytes,
                iu.created_at,
                iu.ocr_status,
                iu.ocr_processed_at,
                iu.ocr_error,
                o.id AS ocr_id,
                o.raw_text,
                o.line_count,
                o.avg_confidence,
                o.parsed_name,
                o.parsed_phone,
                o.phone_candidates,
                o.name_candidates
            FROM image_uploads iu
            LEFT JOIN ocr_results o ON o.upload_id = iu.id
            ORDER BY iu.id DESC
            """
        ).fetchall()

    return [_serialize_upload_row(row) for row in rows]


@app.post("/uploads/{upload_id}/process")
def process_upload(upload_id: int):
    return _process_upload(upload_id)


@app.post("/uploads/process-pending")
def process_pending_uploads():
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id
            FROM image_uploads
            WHERE ocr_status IS NULL OR ocr_status IN ('pending', 'error')
            ORDER BY id ASC
            """
        ).fetchall()

    items = []
    for row in rows:
        items.append(_process_upload(row["id"]))

    return {
        "processed_count": len(items),
        "items": items,
    }