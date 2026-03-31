from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4
import shutil

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .db import BASE_DIR, get_connection, init_db
from .services.ocr_service import get_ocr_service
from .parsers.zelenza_parser import normalize_serial, parse_zelenza
from .parsers.necomplus_parser import parse_necomplus_comercio, parse_necomplus_detalle

UPLOADS_DIR = BASE_DIR / "uploads"
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


class ContactoManualInput(BaseModel):
    nombre: str = Field(min_length=1, max_length=150)
    orden: int = Field(default=1, ge=1)


class ComercioManualUpdate(BaseModel):
    sector: str | None = None
    tipo: str | None = None
    comentario: str | None = None
    actuacion: int = 0
    coordenada_lat: float | None = None
    coordenada_lng: float | None = None
    geocoded_at: str | None = None
    contactos: list[ContactoManualInput] = []

class NecomplusPairInput(BaseModel):
    upload_comercio_id: int
    upload_detalle_id: int

class NecomplusManualUpdate(BaseModel):
    ns_inst_manual: str | None = None
    sector: str | None = None
    tipo: str | None = None
    comentario: str | None = None
    actuacion: int = 0
    coordenada_lat: float | None = None
    coordenada_lng: float | None = None
    geocoded_at: str | None = None
    contactos: list[ContactoManualInput] = []


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def serialize_contact_rows(rows: list[Any]) -> list[dict[str, Any]]:
    return [
        {
            "id": row["id"],
            "nombre": row["nombre"],
            "orden": row["orden"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
        for row in rows
    ]


def serialize_estado_row(row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "num_comercio": row["num_comercio"],
        "entidad_bancaria": row["entidad_bancaria"],
        "descripcion": row["descripcion"],
        "poblacion": row["poblacion"],
        "direccion": row["direccion"],
        "cod_postal": row["cod_postal"],
        "provincia": row["provincia"],
        "telefono_1": row["telefono_1"],
        "telefono_2": row["telefono_2"],
        "contacto": row["contacto"],
        "horario": row["horario"],
        "ns_inst_actual": row["ns_inst_actual"],
        "ultimo_ns_ret_afec": row["ultimo_ns_ret_afec"],
        "ultimo_ot_id": row["ultimo_ot_id"],
        "ultimo_ref_cliente": row["ultimo_ref_cliente"],
        "ultimo_upload_id": row["ultimo_upload_id"],
        "sector": row["sector"],
        "tipo": row["tipo"],
        "comentario": row["comentario"],
        "actuacion": row["actuacion"],
        "coordenada_lat": row["coordenada_lat"],
        "coordenada_lng": row["coordenada_lng"],
        "geocoded_at": row["geocoded_at"],
        "first_seen_at": row["first_seen_at"],
        "last_extracted_at": row["last_extracted_at"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }

def serialize_necomplus_estado_row(row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "codigo_comercio": row["codigo_comercio"],
        "descripcion": row["descripcion"],
        "direccion": row["direccion"],
        "localidad": row["localidad"],
        "provincia": row["provincia"],
        "cod_postal": row["cod_postal"],
        "telefono_1": row["telefono_1"],
        "telefono_2": row["telefono_2"],
        "horario": row["horario"],
        "contacto": row["contacto"],
        "ns_inst_actual": row["ns_inst_actual"],
        "ultimo_ns_ret_afec": row["ultimo_ns_ret_afec"],
        "ultima_interv": row["ultima_interv"],
        "sector": row["sector"],
        "tipo": row["tipo"],
        "comentario": row["comentario"],
        "actuacion": row["actuacion"],
        "coordenada_lat": row["coordenada_lat"],
        "coordenada_lng": row["coordenada_lng"],
        "geocoded_at": row["geocoded_at"],
        "first_seen_at": row["first_seen_at"],
        "last_extracted_at": row["last_extracted_at"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def upsert_necomplus_parte(
    upload_comercio_id: int,
    upload_detalle_id: int,
    upload_created_at: str,
    comercio_data: dict[str, Any],
    detalle_data: dict[str, Any],
    raw_text_comercio: str,
    raw_text_detalle: str,
    confidence_comercio: float | None,
    confidence_detalle: float | None,
) -> None:
    now = utc_now()

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO necomplus_partes (
                upload_comercio_id,
                upload_detalle_id,
                plantilla,
                descripcion,
                codigo_comercio,
                direccion,
                localidad,
                provincia,
                cod_postal,
                telefono_1,
                telefono_2,
                horario,
                contacto,
                interv,
                ns_ret_afec,
                ns_inst_manual,
                raw_text_comercio,
                raw_text_detalle,
                ocr_confidence_comercio,
                ocr_confidence_detalle,
                source_uploaded_at,
                extracted_at,
                created_at,
                updated_at
            )
            VALUES (?, ?, 'Necomplus', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(upload_comercio_id, upload_detalle_id) DO UPDATE SET
                descripcion = excluded.descripcion,
                codigo_comercio = excluded.codigo_comercio,
                direccion = excluded.direccion,
                localidad = excluded.localidad,
                provincia = excluded.provincia,
                cod_postal = excluded.cod_postal,
                telefono_1 = excluded.telefono_1,
                telefono_2 = excluded.telefono_2,
                horario = excluded.horario,
                contacto = excluded.contacto,
                interv = excluded.interv,
                ns_ret_afec = excluded.ns_ret_afec,
                raw_text_comercio = excluded.raw_text_comercio,
                raw_text_detalle = excluded.raw_text_detalle,
                ocr_confidence_comercio = excluded.ocr_confidence_comercio,
                ocr_confidence_detalle = excluded.ocr_confidence_detalle,
                extracted_at = excluded.extracted_at,
                updated_at = excluded.updated_at
            """,
            (
                upload_comercio_id,
                upload_detalle_id,
                comercio_data.get("descripcion"),
                comercio_data.get("codigo_comercio"),
                comercio_data.get("direccion"),
                comercio_data.get("localidad"),
                comercio_data.get("provincia"),
                comercio_data.get("cod_postal"),
                comercio_data.get("telefono_1"),
                comercio_data.get("telefono_2"),
                comercio_data.get("horario"),
                comercio_data.get("contacto"),
                detalle_data.get("interv"),
                detalle_data.get("ns_ret_afec"),
                raw_text_comercio,
                raw_text_detalle,
                confidence_comercio,
                confidence_detalle,
                upload_created_at,
                now,
                now,
                now,
            ),
        )
        conn.commit()


def update_necomplus_estado_comercio(comercio_data: dict[str, Any], detalle_data: dict[str, Any]) -> dict[str, Any]:
    codigo_comercio = comercio_data.get("codigo_comercio")
    if not codigo_comercio:
        raise HTTPException(status_code=422, detail="No se pudo extraer el código de comercio.")

    now = utc_now()

    with get_connection() as conn:
        existing = conn.execute(
            """
            SELECT *
            FROM necomplus_estado_comercio
            WHERE codigo_comercio = ?
            """,
            (codigo_comercio,),
        ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO necomplus_estado_comercio (
                    codigo_comercio,
                    descripcion,
                    direccion,
                    localidad,
                    provincia,
                    cod_postal,
                    telefono_1,
                    telefono_2,
                    horario,
                    contacto,
                    ns_inst_actual,
                    ultimo_ns_ret_afec,
                    ultima_interv,
                    sector,
                    tipo,
                    comentario,
                    actuacion,
                    coordenada_lat,
                    coordenada_lng,
                    geocoded_at,
                    first_seen_at,
                    last_extracted_at,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, NULL, NULL, NULL, 0, NULL, NULL, NULL, ?, ?, ?, ?)
                """,
                (
                    codigo_comercio,
                    comercio_data.get("descripcion"),
                    comercio_data.get("direccion"),
                    comercio_data.get("localidad"),
                    comercio_data.get("provincia"),
                    comercio_data.get("cod_postal"),
                    comercio_data.get("telefono_1"),
                    comercio_data.get("telefono_2"),
                    comercio_data.get("horario"),
                    comercio_data.get("contacto"),
                    detalle_data.get("ns_ret_afec"),
                    detalle_data.get("interv"),
                    now,
                    now,
                    now,
                    now,
                ),
            )
            conn.commit()

            row = conn.execute(
                """
                SELECT *
                FROM necomplus_estado_comercio
                WHERE codigo_comercio = ?
                """,
                (codigo_comercio,),
            ).fetchone()

            return {
                "action": "created",
                "row": serialize_necomplus_estado_row(row),
            }

        conn.execute(
            """
            UPDATE necomplus_estado_comercio
            SET
                descripcion = ?,
                direccion = ?,
                localidad = ?,
                provincia = ?,
                cod_postal = ?,
                telefono_1 = ?,
                telefono_2 = ?,
                horario = ?,
                contacto = ?,
                ultimo_ns_ret_afec = ?,
                ultima_interv = ?,
                last_extracted_at = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                comercio_data.get("descripcion"),
                comercio_data.get("direccion"),
                comercio_data.get("localidad"),
                comercio_data.get("provincia"),
                comercio_data.get("cod_postal"),
                comercio_data.get("telefono_1"),
                comercio_data.get("telefono_2"),
                comercio_data.get("horario"),
                comercio_data.get("contacto"),
                detalle_data.get("ns_ret_afec"),
                detalle_data.get("interv"),
                now,
                now,
                existing["id"],
            ),
        )
        conn.commit()

        row = conn.execute(
            """
            SELECT *
            FROM necomplus_estado_comercio
            WHERE id = ?
            """,
            (existing["id"],),
        ).fetchone()

        return {
            "action": "updated",
            "row": serialize_necomplus_estado_row(row),
        }

def upsert_zelenza_parte(upload_id: int, upload_created_at: str, parsed: dict[str, Any], raw_text: str, confidence: float | None) -> None:
    now = utc_now()

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO zelenza_partes (
                upload_id,
                plantilla,
                ot_id,
                entidad_bancaria,
                descripcion,
                poblacion,
                direccion,
                cod_postal,
                provincia,
                telefono_1,
                telefono_2,
                contacto,
                ref_cliente,
                num_comercio,
                horario,
                ns_inst,
                ns_ret_afec,
                actuacion,
                raw_text,
                ocr_confidence,
                source_uploaded_at,
                extracted_at,
                created_at,
                updated_at
            )
            VALUES (?, 'Zelenza', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(upload_id) DO UPDATE SET
                ot_id = excluded.ot_id,
                entidad_bancaria = excluded.entidad_bancaria,
                descripcion = excluded.descripcion,
                poblacion = excluded.poblacion,
                direccion = excluded.direccion,
                cod_postal = excluded.cod_postal,
                provincia = excluded.provincia,
                telefono_1 = excluded.telefono_1,
                telefono_2 = excluded.telefono_2,
                contacto = excluded.contacto,
                ref_cliente = excluded.ref_cliente,
                num_comercio = excluded.num_comercio,
                horario = excluded.horario,
                ns_inst = excluded.ns_inst,
                ns_ret_afec = excluded.ns_ret_afec,
                raw_text = excluded.raw_text,
                ocr_confidence = excluded.ocr_confidence,
                extracted_at = excluded.extracted_at,
                updated_at = excluded.updated_at
            """,
            (
                upload_id,
                parsed.get("ot_id"),
                parsed.get("entidad_bancaria"),
                parsed.get("descripcion"),
                parsed.get("poblacion"),
                parsed.get("direccion"),
                parsed.get("cod_postal"),
                parsed.get("provincia"),
                parsed.get("telefono_1"),
                parsed.get("telefono_2"),
                parsed.get("contacto"),
                parsed.get("ref_cliente"),
                parsed.get("num_comercio"),
                parsed.get("horario"),
                parsed.get("ns_inst"),
                parsed.get("ns_ret_afec"),
                raw_text,
                confidence,
                upload_created_at,
                now,
                now,
                now,
            ),
        )
        conn.commit()


def update_estado_comercio(upload_id: int, parsed: dict[str, Any]) -> dict[str, Any]:
    num_comercio = parsed.get("num_comercio")
    if not num_comercio:
        raise HTTPException(status_code=422, detail="No se pudo extraer 'Nº Comercio'. No se puede actualizar el estado del comercio.")

    now = utc_now()
    ns_inst_nuevo = normalize_serial(parsed.get("ns_inst"))
    ns_ret_afec_nuevo = normalize_serial(parsed.get("ns_ret_afec"))

    with get_connection() as conn:
        existing = conn.execute(
            """
            SELECT *
            FROM zelenza_estado_comercio
            WHERE num_comercio = ?
            """,
            (num_comercio,),
        ).fetchone()

        if existing is None:
            conn.execute(
                """
                INSERT INTO zelenza_estado_comercio (
                    num_comercio,
                    entidad_bancaria,
                    descripcion,
                    poblacion,
                    direccion,
                    cod_postal,
                    provincia,
                    telefono_1,
                    telefono_2,
                    contacto,
                    horario,
                    ns_inst_actual,
                    ultimo_ns_ret_afec,
                    ultimo_ot_id,
                    ultimo_ref_cliente,
                    ultimo_upload_id,
                    sector,
                    tipo,
                    comentario,
                    actuacion,
                    coordenada_lat,
                    coordenada_lng,
                    geocoded_at,
                    first_seen_at,
                    last_extracted_at,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, 0, NULL, NULL, NULL, ?, ?, ?, ?)
                """,
                (
                    num_comercio,
                    parsed.get("entidad_bancaria"),
                    parsed.get("descripcion"),
                    parsed.get("poblacion"),
                    parsed.get("direccion"),
                    parsed.get("cod_postal"),
                    parsed.get("provincia"),
                    parsed.get("telefono_1"),
                    parsed.get("telefono_2"),
                    parsed.get("contacto"),
                    parsed.get("horario"),
                    ns_inst_nuevo,
                    ns_ret_afec_nuevo,
                    parsed.get("ot_id"),
                    parsed.get("ref_cliente"),
                    upload_id,
                    now,
                    now,
                    now,
                    now,
                ),
            )
            conn.commit()

            created_row = conn.execute(
                """
                SELECT *
                FROM zelenza_estado_comercio
                WHERE num_comercio = ?
                """,
                (num_comercio,),
            ).fetchone()

            return {
                "action": "created",
                "row": serialize_estado_row(created_row),
            }

        current_ns_inst = normalize_serial(existing["ns_inst_actual"])
        should_rotate_terminal = (
            ns_ret_afec_nuevo is not None
            and current_ns_inst is not None
            and ns_ret_afec_nuevo == current_ns_inst
            and ns_inst_nuevo is not None
        )

        new_ns_inst_actual = existing["ns_inst_actual"]
        if should_rotate_terminal:
            new_ns_inst_actual = ns_inst_nuevo
        elif not existing["ns_inst_actual"] and ns_inst_nuevo:
            new_ns_inst_actual = ns_inst_nuevo

        conn.execute(
            """
            UPDATE zelenza_estado_comercio
            SET
                entidad_bancaria = ?,
                descripcion = ?,
                poblacion = ?,
                direccion = ?,
                cod_postal = ?,
                provincia = ?,
                telefono_1 = ?,
                telefono_2 = ?,
                contacto = ?,
                horario = ?,
                ns_inst_actual = ?,
                ultimo_ns_ret_afec = ?,
                ultimo_ot_id = ?,
                ultimo_ref_cliente = ?,
                ultimo_upload_id = ?,
                last_extracted_at = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                parsed.get("entidad_bancaria"),
                parsed.get("descripcion"),
                parsed.get("poblacion"),
                parsed.get("direccion"),
                parsed.get("cod_postal"),
                parsed.get("provincia"),
                parsed.get("telefono_1"),
                parsed.get("telefono_2"),
                parsed.get("contacto"),
                parsed.get("horario"),
                new_ns_inst_actual,
                ns_ret_afec_nuevo,
                parsed.get("ot_id"),
                parsed.get("ref_cliente"),
                upload_id,
                now,
                now,
                existing["id"],
            ),
        )
        conn.commit()

        updated_row = conn.execute(
            """
            SELECT *
            FROM zelenza_estado_comercio
            WHERE id = ?
            """,
            (existing["id"],),
        ).fetchone()

        return {
            "action": "updated",
            "terminal_rotated": should_rotate_terminal,
            "row": serialize_estado_row(updated_row),
        }


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
    stored_name = f"{uuid4().hex}{suffix}"
    destination = UPLOADS_DIR / stored_name

    try:
        with destination.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    finally:
        await file.close()

    size_bytes = destination.stat().st_size
    created_at = utc_now()
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
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                file.filename,
                stored_name,
                file_path,
                file.content_type,
                size_bytes,
                created_at,
            ),
        )
        conn.commit()
        upload_id = cursor.lastrowid

    return {
        "id": upload_id,
        "original_name": file.filename,
        "stored_name": stored_name,
        "file_path": file_path,
        "mime_type": file.content_type,
        "size_bytes": size_bytes,
        "created_at": created_at,
        "url": f"http://localhost:8000/media/{stored_name}",
        "zelenza_result": None,
    }


@app.get("/uploads")
def list_uploads():
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT
                u.id,
                u.original_name,
                u.stored_name,
                u.file_path,
                u.mime_type,
                u.size_bytes,
                u.created_at,

                z.id AS zelenza_id,
                z.entidad_bancaria,
                z.descripcion,
                z.poblacion,
                z.direccion,
                z.cod_postal,
                z.provincia,
                z.telefono_1,
                z.telefono_2,
                z.contacto,
                z.ref_cliente,
                z.num_comercio,
                z.horario,
                z.ns_inst,
                z.ns_ret_afec,
                z.ot_id,
                z.ocr_confidence
            FROM image_uploads u
            LEFT JOIN zelenza_partes z ON z.upload_id = u.id
            ORDER BY u.id DESC
            """
        ).fetchall()

    items = []
    for row in rows:
        item = dict(row)
        item["url"] = f"http://localhost:8000/media/{item['stored_name']}"

        if item["zelenza_id"] is not None:
            item["zelenza_result"] = {
                "id": item["zelenza_id"],
                "ot_id": item["ot_id"],
                "entidad_bancaria": item["entidad_bancaria"],
                "descripcion": item["descripcion"],
                "poblacion": item["poblacion"],
                "direccion": item["direccion"],
                "cod_postal": item["cod_postal"],
                "provincia": item["provincia"],
                "telefono_1": item["telefono_1"],
                "telefono_2": item["telefono_2"],
                "contacto": item["contacto"],
                "ref_cliente": item["ref_cliente"],
                "num_comercio": item["num_comercio"],
                "horario": item["horario"],
                "ns_inst": item["ns_inst"],
                "ns_ret_afec": item["ns_ret_afec"],
                "ocr_confidence": item["ocr_confidence"],
            }
        else:
            item["zelenza_result"] = None

        for field in [
            "zelenza_id",
            "ot_id",
            "entidad_bancaria",
            "descripcion",
            "poblacion",
            "direccion",
            "cod_postal",
            "provincia",
            "telefono_1",
            "telefono_2",
            "contacto",
            "ref_cliente",
            "num_comercio",
            "horario",
            "ns_inst",
            "ns_ret_afec",
            "ocr_confidence",
        ]:
            item.pop(field, None)

        items.append(item)

    return items


@app.post("/uploads/{upload_id}/process/zelenza")
def process_upload_zelenza(upload_id: int):
    with get_connection() as conn:
        upload = conn.execute(
            """
            SELECT *
            FROM image_uploads
            WHERE id = ?
            """,
            (upload_id,),
        ).fetchone()

    if upload is None:
        raise HTTPException(status_code=404, detail="Imagen no encontrada.")

    image_path = BASE_DIR / upload["file_path"]
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="El archivo físico no existe.")

    ocr_service = get_ocr_service()
    ocr_output = ocr_service.run(image_path)

    parsed = parse_zelenza(ocr_output["text_lines"], ocr_output["raw_text"])

    upsert_zelenza_parte(
        upload_id=upload["id"],
        upload_created_at=upload["created_at"],
        parsed=parsed,
        raw_text=ocr_output["raw_text"],
        confidence=ocr_output["confidence"],
    )

    estado_result = update_estado_comercio(upload["id"], parsed)

    return {
        "upload_id": upload["id"],
        "plantilla": "Zelenza",
        "parsed": parsed,
        "raw_text": ocr_output["raw_text"],
        "ocr_confidence": ocr_output["confidence"],
        "estado_comercio": estado_result,
    }


@app.get("/uploads/{upload_id}/zelenza")
def get_upload_zelenza(upload_id: int):
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM zelenza_partes
            WHERE upload_id = ?
            """,
            (upload_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Esta imagen todavía no tiene procesamiento Zelenza.")

    return dict(row)


@app.get("/zelenza/comercios")
def list_zelenza_comercios():
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM zelenza_estado_comercio
            ORDER BY updated_at DESC
            """
        ).fetchall()

    return [serialize_estado_row(row) for row in rows]


@app.get("/zelenza/comercios/{comercio_id}")
def get_zelenza_comercio(comercio_id: int):
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM zelenza_estado_comercio
            WHERE id = ?
            """,
            (comercio_id,),
        ).fetchone()

        if row is None:
            raise HTTPException(status_code=404, detail="Comercio no encontrado.")

        contacts = conn.execute(
            """
            SELECT *
            FROM zelenza_contactos
            WHERE comercio_id = ?
            ORDER BY orden ASC, id ASC
            """,
            (comercio_id,),
        ).fetchall()

    return {
        **serialize_estado_row(row),
        "contactos_manuales": serialize_contact_rows(contacts),
    }


@app.put("/zelenza/comercios/{comercio_id}/manual")
def update_zelenza_comercio_manual(comercio_id: int, payload: ComercioManualUpdate):
    now = utc_now()

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM zelenza_estado_comercio
            WHERE id = ?
            """,
            (comercio_id,),
        ).fetchone()

        if row is None:
            raise HTTPException(status_code=404, detail="Comercio no encontrado.")

        conn.execute(
            """
            UPDATE zelenza_estado_comercio
            SET
                sector = ?,
                tipo = ?,
                comentario = ?,
                actuacion = ?,
                coordenada_lat = ?,
                coordenada_lng = ?,
                geocoded_at = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                payload.sector,
                payload.tipo,
                payload.comentario,
                payload.actuacion,
                payload.coordenada_lat,
                payload.coordenada_lng,
                payload.geocoded_at,
                now,
                comercio_id,
            ),
        )

        conn.execute(
            """
            DELETE FROM zelenza_contactos
            WHERE comercio_id = ?
            """,
            (comercio_id,),
        )

        for index, contact in enumerate(payload.contactos, start=1):
            conn.execute(
                """
                INSERT INTO zelenza_contactos (
                    comercio_id,
                    nombre,
                    orden,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    comercio_id,
                    contact.nombre,
                    contact.orden or index,
                    now,
                    now,
                ),
            )

        conn.commit()

        updated_row = conn.execute(
            """
            SELECT *
            FROM zelenza_estado_comercio
            WHERE id = ?
            """,
            (comercio_id,),
        ).fetchone()

        contacts = conn.execute(
            """
            SELECT *
            FROM zelenza_contactos
            WHERE comercio_id = ?
            ORDER BY orden ASC, id ASC
            """,
            (comercio_id,),
        ).fetchall()

    return {
        **serialize_estado_row(updated_row),
        "contactos_manuales": serialize_contact_rows(contacts),
    }

@app.post("/necomplus/process-pair")
def process_necomplus_pair(payload: NecomplusPairInput):
    with get_connection() as conn:
        upload_comercio = conn.execute(
            """
            SELECT *
            FROM image_uploads
            WHERE id = ?
            """,
            (payload.upload_comercio_id,),
        ).fetchone()

        upload_detalle = conn.execute(
            """
            SELECT *
            FROM image_uploads
            WHERE id = ?
            """,
            (payload.upload_detalle_id,),
        ).fetchone()

    if upload_comercio is None:
        raise HTTPException(status_code=404, detail="No existe la imagen de comercio.")
    if upload_detalle is None:
        raise HTTPException(status_code=404, detail="No existe la imagen de detalle.")

    image_path_comercio = BASE_DIR / upload_comercio["file_path"]
    image_path_detalle = BASE_DIR / upload_detalle["file_path"]

    if not image_path_comercio.exists():
        raise HTTPException(status_code=404, detail="El archivo físico de comercio no existe.")
    if not image_path_detalle.exists():
        raise HTTPException(status_code=404, detail="El archivo físico de detalle no existe.")

    ocr_service = get_ocr_service()

    ocr_comercio = ocr_service.run(image_path_comercio)
    ocr_detalle = ocr_service.run(image_path_detalle)

    comercio_data = parse_necomplus_comercio(ocr_comercio["text_lines"], ocr_comercio["raw_text"])
    detalle_data = parse_necomplus_detalle(ocr_detalle["raw_text"])

    source_uploaded_at = upload_comercio["created_at"]

    upsert_necomplus_parte(
        upload_comercio_id=payload.upload_comercio_id,
        upload_detalle_id=payload.upload_detalle_id,
        upload_created_at=source_uploaded_at,
        comercio_data=comercio_data,
        detalle_data=detalle_data,
        raw_text_comercio=ocr_comercio["raw_text"],
        raw_text_detalle=ocr_detalle["raw_text"],
        confidence_comercio=ocr_comercio["confidence"],
        confidence_detalle=ocr_detalle["confidence"],
    )

    estado = update_necomplus_estado_comercio(comercio_data, detalle_data)

    return {
        "plantilla": "Necomplus",
        "upload_comercio_id": payload.upload_comercio_id,
        "upload_detalle_id": payload.upload_detalle_id,
        "comercio_data": comercio_data,
        "detalle_data": detalle_data,
        "ocr_confidence_comercio": ocr_comercio["confidence"],
        "ocr_confidence_detalle": ocr_detalle["confidence"],
        "estado_comercio": estado,
    }


@app.get("/necomplus/comercios")
def list_necomplus_comercios():
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM necomplus_estado_comercio
            ORDER BY updated_at DESC
            """
        ).fetchall()

    return [serialize_necomplus_estado_row(row) for row in rows]


@app.get("/necomplus/comercios/{comercio_id}")
def get_necomplus_comercio(comercio_id: int):
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM necomplus_estado_comercio
            WHERE id = ?
            """,
            (comercio_id,),
        ).fetchone()

        if row is None:
            raise HTTPException(status_code=404, detail="Comercio Necomplus no encontrado.")

        contacts = conn.execute(
            """
            SELECT *
            FROM necomplus_contactos
            WHERE comercio_id = ?
            ORDER BY orden ASC, id ASC
            """,
            (comercio_id,),
        ).fetchall()

    return {
        **serialize_necomplus_estado_row(row),
        "contactos_manuales": serialize_contact_rows(contacts),
    }


@app.put("/necomplus/comercios/{comercio_id}/manual")
def update_necomplus_comercio_manual(comercio_id: int, payload: NecomplusManualUpdate):
    now = utc_now()

    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM necomplus_estado_comercio
            WHERE id = ?
            """,
            (comercio_id,),
        ).fetchone()

        if row is None:
            raise HTTPException(status_code=404, detail="Comercio Necomplus no encontrado.")

        conn.execute(
            """
            UPDATE necomplus_estado_comercio
            SET
                ns_inst_actual = ?,
                sector = ?,
                tipo = ?,
                comentario = ?,
                actuacion = ?,
                coordenada_lat = ?,
                coordenada_lng = ?,
                geocoded_at = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                payload.ns_inst_manual,
                payload.sector,
                payload.tipo,
                payload.comentario,
                payload.actuacion,
                payload.coordenada_lat,
                payload.coordenada_lng,
                payload.geocoded_at,
                now,
                comercio_id,
            ),
        )

        conn.execute(
            """
            DELETE FROM necomplus_contactos
            WHERE comercio_id = ?
            """,
            (comercio_id,),
        )

        for index, contact in enumerate(payload.contactos, start=1):
            conn.execute(
                """
                INSERT INTO necomplus_contactos (
                    comercio_id,
                    nombre,
                    orden,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    comercio_id,
                    contact.nombre,
                    contact.orden or index,
                    now,
                    now,
                ),
            )

        conn.commit()

        updated = conn.execute(
            """
            SELECT *
            FROM necomplus_estado_comercio
            WHERE id = ?
            """,
            (comercio_id,),
        ).fetchone()

        contacts = conn.execute(
            """
            SELECT *
            FROM necomplus_contactos
            WHERE comercio_id = ?
            ORDER BY orden ASC, id ASC
            """,
            (comercio_id,),
        ).fetchall()

    return {
        **serialize_necomplus_estado_row(updated),
        "contactos_manuales": serialize_contact_rows(contacts),
    }