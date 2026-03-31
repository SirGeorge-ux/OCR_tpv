import re
import unicodedata


HEADER_NOISE = {
    "DETALLES",
    "ETAPAS",
    "TERMINALES",
    "COMERCIO",
}
DESCRIPTION_NOISE_PARTS = [
    "DETALLES",
    "TALLES",
    "ETAPAS",
    "TERMINALES",
    "COMERCIO",
    "ORDEN",
]


def remove_accents(value: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", value)
        if unicodedata.category(c) != "Mn"
    )


def normalize_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def clean_value(value: str | None) -> str | None:
    if value is None:
        return None

    value = normalize_spaces(value)
    value = value.strip(":- ")

    if not value:
        return None

    if value.upper() in {"N/A", "NULL", "NONE"}:
        return None

    return value

def is_noise_line_for_description(value: str) -> bool:
    raw = normalize_spaces(value)
    upper = remove_accents(raw).upper()

    if not raw:
        return True

    if "%" in raw:
        return True

    if re.search(r"\d{1,2}:\d{2}", raw):
        return True

    if any(token in upper for token in DESCRIPTION_NOISE_PARTS):
        return True

    if len(raw) <= 4 and re.fullmatch(r"[A-Z0-9]+", upper):
        return True

    return False

def clean_description_text(value: str | None) -> str | None:
    if not value:
        return None

    text = normalize_spaces(value)

    # elimina cabecera basura típica de móvil / pestañas
    text = re.sub(
        r'^(?:[A-Z]{1,3}\s*)?(?:\S*%+\s*)?(?:DETALLES|TALLES|ETAPAS|TERMINALES|COMERCIO)\s+',
        '',
        text,
        flags=re.IGNORECASE,
    )

    # elimina símbolos raros al inicio
    text = re.sub(r'^[^A-Za-zÁÉÍÓÚÜÑ]+', '', text)

    text = normalize_spaces(text)
    return text or None


def normalize_phone(value: str | None) -> str | None:
    if not value:
        return None

    digits = re.sub(r"\D", "", value)
    return digits or None


def extract_after_label(lines: list[str], labels: list[str]) -> str | None:
    normalized_labels = [remove_accents(label).upper() for label in labels]

    for index, line in enumerate(lines):
        raw = normalize_spaces(line)
        cmp_line = remove_accents(raw).upper()

        for label in normalized_labels:
            if label in cmp_line:
                if ":" in raw:
                    inline = clean_value(raw.split(":", 1)[1])
                    if inline:
                        return inline

                for next_index in range(index + 1, min(index + 4, len(lines))):
                    candidate = clean_value(lines[next_index])
                    if candidate:
                        return candidate

    return None


def extract_phone_block(lines: list[str]) -> tuple[str | None, str | None]:
    for index, line in enumerate(lines):
        cmp_line = remove_accents(normalize_spaces(line)).upper()

        if "TELEFONOS" in cmp_line or "TELEFONO" in cmp_line:
            found: list[str] = []

            for next_index in range(index + 1, min(index + 6, len(lines))):
                candidate = normalize_spaces(lines[next_index])
                cmp_candidate = remove_accents(candidate).upper()

                if any(label in cmp_candidate for label in ["HORARIO", "LINEA", "CONTACTO"]):
                    break

                phone_match = re.findall(r"\+?\d[\d\s().-]{7,}\d", candidate)
                for match in phone_match:
                    phone = normalize_phone(match)
                    if phone and phone not in found:
                        found.append(phone)

            phone_1 = found[0] if len(found) > 0 else None
            phone_2 = found[1] if len(found) > 1 else None
            return phone_1, phone_2

    return None, None


def extract_codigo_comercio(lines: list[str]) -> str | None:
    for index, line in enumerate(lines[:20]):
        raw = normalize_spaces(line)

        if "ORDEN" in remove_accents(raw).upper():
            continue

        if re.fullmatch(r"\d{7,12}", raw):
            return raw

        match = re.search(r"\b(\d{7,12})\b", raw)
        if match:
            return match.group(1)

    return None


def extract_descripcion(lines: list[str], codigo_comercio: str | None) -> str | None:
    code_index = None

    for index, line in enumerate(lines[:25]):
        raw = normalize_spaces(line)
        if codigo_comercio and codigo_comercio in raw:
            code_index = index
            break

    if code_index is None:
        code_index = min(8, len(lines))

    parts: list[str] = []

    for line in lines[:code_index]:
        raw = normalize_spaces(line)

        if is_noise_line_for_description(raw):
            continue

        if ":" in raw:
            continue

        if re.fullmatch(r"\d{7,12}", raw):
            continue

        parts.append(raw)

    text = " ".join(parts)
    return clean_description_text(text)


def parse_necomplus_comercio(lines: list[str], raw_text: str) -> dict[str, str | None]:
    cleaned_lines = [normalize_spaces(line) for line in lines if normalize_spaces(line)]

    codigo_comercio = extract_codigo_comercio(cleaned_lines)
    telefono_1, telefono_2 = extract_phone_block(cleaned_lines)

    return {
        "descripcion": extract_descripcion(cleaned_lines, codigo_comercio),
        "codigo_comercio": codigo_comercio,
        "direccion": extract_after_label(cleaned_lines, ["Dirección", "Direccion"]),
        "localidad": extract_after_label(cleaned_lines, ["Localidad"]),
        "provincia": extract_after_label(cleaned_lines, ["Provincia"]),
        "cod_postal": extract_after_label(cleaned_lines, ["Código Postal", "Codigo Postal"]),
        "telefono_1": telefono_1,
        "telefono_2": telefono_2,
        "horario": extract_after_label(cleaned_lines, ["Horario"]),
        "contacto": extract_after_label(cleaned_lines, ["Contacto"]),
    }


def parse_necomplus_detalle(raw_text: str) -> dict[str, str | None]:
    compact = normalize_spaces(raw_text)

    interv_match = re.search(r"interv\s*=\s*([A-Za-z0-9]+)", compact, re.IGNORECASE)
    serie_match = re.search(
        r"(?:N[º°o]\s*serie|N\s*serie|serie)\s*=\s*([A-Za-z0-9]+)",
        compact,
        re.IGNORECASE,
    )

    return {
        "interv": interv_match.group(1) if interv_match else None,
        "ns_ret_afec": serie_match.group(1) if serie_match else None,
    }