from pathlib import Path
import sqlite3

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "ocr_tpv.db"


def get_connection() -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        # =========================================================
        # 1) TABLAS BASE COMUNES A TODAS LAS PLANTILLAS
        # =========================================================
        # Aquí van las tablas generales del sistema, reutilizadas por
        # Zelenza, Necomplus y futuras plantillas.
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS image_uploads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_name TEXT NOT NULL,
                stored_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                mime_type TEXT,
                size_bytes INTEGER NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )

        # =========================================================
        # 2) BLOQUE ZELENZA
        # =========================================================
        # Histórico de partes Zelenza
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS zelenza_partes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                upload_id INTEGER NOT NULL UNIQUE,
                plantilla TEXT NOT NULL DEFAULT 'Zelenza',

                ot_id TEXT,
                entidad_bancaria TEXT,
                descripcion TEXT,
                poblacion TEXT,
                direccion TEXT,
                cod_postal TEXT,
                provincia TEXT,
                telefono_1 TEXT,
                telefono_2 TEXT,
                contacto TEXT,
                ref_cliente TEXT,
                num_comercio TEXT,
                horario TEXT,
                ns_inst TEXT,
                ns_ret_afec TEXT,

                actuacion INTEGER NOT NULL DEFAULT 0,

                raw_text TEXT,
                ocr_confidence REAL,

                source_uploaded_at TEXT NOT NULL,
                extracted_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,

                FOREIGN KEY(upload_id) REFERENCES image_uploads(id) ON DELETE CASCADE
            )
            """
        )

        # Estado actual del comercio Zelenza
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS zelenza_estado_comercio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                num_comercio TEXT NOT NULL UNIQUE,

                entidad_bancaria TEXT,
                descripcion TEXT,
                poblacion TEXT,
                direccion TEXT,
                cod_postal TEXT,
                provincia TEXT,
                telefono_1 TEXT,
                telefono_2 TEXT,
                contacto TEXT,
                horario TEXT,

                ns_inst_actual TEXT,
                ultimo_ns_ret_afec TEXT,

                ultimo_ot_id TEXT,
                ultimo_ref_cliente TEXT,
                ultimo_upload_id INTEGER,

                sector TEXT,
                tipo TEXT,
                comentario TEXT,
                actuacion INTEGER NOT NULL DEFAULT 0,

                coordenada_lat REAL,
                coordenada_lng REAL,
                geocoded_at TEXT,

                first_seen_at TEXT NOT NULL,
                last_extracted_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,

                FOREIGN KEY(ultimo_upload_id) REFERENCES image_uploads(id) ON DELETE SET NULL
            )
            """
        )

        # Contactos manuales Zelenza
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS zelenza_contactos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                comercio_id INTEGER NOT NULL,
                nombre TEXT NOT NULL,
                orden INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(comercio_id) REFERENCES zelenza_estado_comercio(id) ON DELETE CASCADE
            )
            """
        )

        # Índices Zelenza
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_zelenza_partes_num_comercio
            ON zelenza_partes (num_comercio)
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_zelenza_partes_ref_cliente
            ON zelenza_partes (ref_cliente)
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_zelenza_contactos_comercio
            ON zelenza_contactos (comercio_id)
            """
        )

        # =========================================================
        # 3) BLOQUE NECOMPLUS
        # =========================================================
        # Histórico de partes Necomplus.
        # Ojo: aquí una "unidad lógica" se compone de 2 imágenes:
        # - upload_comercio_id
        # - upload_detalle_id
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS necomplus_partes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                upload_comercio_id INTEGER NOT NULL,
                upload_detalle_id INTEGER NOT NULL,

                plantilla TEXT NOT NULL DEFAULT 'Necomplus',

                descripcion TEXT,
                codigo_comercio TEXT,
                direccion TEXT,
                localidad TEXT,
                provincia TEXT,
                cod_postal TEXT,
                telefono_1 TEXT,
                telefono_2 TEXT,
                horario TEXT,
                contacto TEXT,

                interv TEXT,
                ns_ret_afec TEXT,
                ns_inst_manual TEXT,

                raw_text_comercio TEXT,
                raw_text_detalle TEXT,
                ocr_confidence_comercio REAL,
                ocr_confidence_detalle REAL,

                source_uploaded_at TEXT NOT NULL,
                extracted_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,

                FOREIGN KEY(upload_comercio_id) REFERENCES image_uploads(id) ON DELETE CASCADE,
                FOREIGN KEY(upload_detalle_id) REFERENCES image_uploads(id) ON DELETE CASCADE,
                UNIQUE(upload_comercio_id, upload_detalle_id)
            )
            """
        )

        # Estado actual del comercio Necomplus
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS necomplus_estado_comercio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo_comercio TEXT NOT NULL UNIQUE,

                descripcion TEXT,
                direccion TEXT,
                localidad TEXT,
                provincia TEXT,
                cod_postal TEXT,
                telefono_1 TEXT,
                telefono_2 TEXT,
                horario TEXT,
                contacto TEXT,

                ns_inst_actual TEXT,
                ultimo_ns_ret_afec TEXT,
                ultima_interv TEXT,

                sector TEXT,
                tipo TEXT,
                comentario TEXT,
                actuacion INTEGER NOT NULL DEFAULT 0,
                coordenada_lat REAL,
                coordenada_lng REAL,
                geocoded_at TEXT,

                first_seen_at TEXT NOT NULL,
                last_extracted_at TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        # Contactos manuales Necomplus
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS necomplus_contactos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                comercio_id INTEGER NOT NULL,
                nombre TEXT NOT NULL,
                orden INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(comercio_id) REFERENCES necomplus_estado_comercio(id) ON DELETE CASCADE
            )
            """
        )

        # Índices Necomplus
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_necomplus_partes_codigo_comercio
            ON necomplus_partes (codigo_comercio)
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_necomplus_partes_interv
            ON necomplus_partes (interv)
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_necomplus_contactos_comercio
            ON necomplus_contactos (comercio_id)
            """
        )

        # =========================================================
        # 4) FUTURAS PLANTILLAS
        # =========================================================
        # Cuando añadas una nueva plantilla, por ejemplo DIUSFRAMI,
        # te recomiendo seguir este orden:
        #
        #   4.1 CREATE TABLE ..._partes
        #   4.2 CREATE TABLE ..._estado_comercio
        #   4.3 CREATE TABLE ..._contactos   (si aplica)
        #   4.4 CREATE INDEX ...
        #
        # Ejemplo:
        #
        # conn.execute(
        #     '''
        #     CREATE TABLE IF NOT EXISTS diusframi_partes (
        #         ...
        #     )
        #     '''
        # )
        #
        # conn.execute(
        #     '''
        #     CREATE TABLE IF NOT EXISTS diusframi_estado_comercio (
        #         ...
        #     )
        #     '''
        # )

        # =========================================================
        # 5) COMMIT FINAL
        # =========================================================
        conn.commit()