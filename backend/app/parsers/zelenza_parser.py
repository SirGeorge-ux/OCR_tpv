import re
import unicodedata


BANK_ALIASES = {
    "SANTANDER": "Santander",
    "BBVA": "BBVA",
    "CAIXABANK": "CaixaBank",
    "CAIXA": "CaixaBank",
    "SABADELL": "Sabadell",
    "UNICAJA": "Unicaja",
    "ABANCA": "ABANCA",
    "BANKINTER": "Bankinter",
    "ING": "ING",
    "RURAL": "Caja Rural",
    "KUTXABANK": "Kutxabank",
}

LABELS = {
    "ot_id": ["Datos de OT", "OT", "Datos OT"],
    "descripcion": ["Descripción", "Descripcion"],
    "poblacion": ["Población", "Poblacion"],
    "direccion": ["Dirección", "Direccion"],
    "cod_postal": ["Cód. Postal", "Cod. Postal", "Código Postal", "Codigo Postal"],
    "provincia": ["Provincia"],
    "telefono_1": ["Teléfono 1", "Telefono 1"],
    "telefono_2": ["Teléfono 2", "Telefono 2"],
    "contacto": ["Contacto"],
    "ref_cliente": ["Ref. Cliente", "Referencia Cliente", "Ref Cliente"],
    "num_comercio": ["Nº Comercio", "N° Comercio", "No Comercio", "Numero Comercio"],
    "horario": ["Horario"],
    "ns_inst": ["N/S Inst.", "N/S Inst", "NS Inst", "N S Inst"],
    "ns_ret_afec": ["N/S Ret/Afec:", "N/S Ret/Afec", "NS Ret/Afec", "N S Ret Afec"],
}

SECTION_TITLES = [
    "Datos Generales",
    "Requisitos",
    "Datos de OT",
    "Pocket Vulcano",
    "Estado",
    "Prioridad",
    "Concepto",
    "Tipo",
    "Cliente",
    "Comp. Dir.",
    "País",
    "Pais",
    "Email",
    "Agencia",
    "Fc.Entrada",
    "Fc.Objetivo",
    "Modelo Inst.",
    "Modelo Inst",
    "Modelo Ret/Afec:",
    "Modelo Ret/Afec",
    "N/S Inst.:",
    "N/S Inst.",
    "N/S Ret/Afec:",
    "N/S Ret/Afec",
    "Fc.Entrada:",
    "Fc.Entrada",
    "Fc.Objetivo:",
    "Fc.Objetivo",
]

def nullify_fake_values(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = normalize_key(value)

    fake_values = {
        "MODELOINST",
        "MODELOINST.",
        "MODELORETAFEC",
        "MODELORETAFEC.",
        "FCENTRADA",
        "FCOBJETIVO",
    }

    if normalized in fake_values:
        return None

    return value

def remove_accents(value: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", value)
        if unicodedata.category(c) != "Mn"
    )


def normalize_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def normalize_key(value: str) -> str:
    value = remove_accents(value).upper()
    value = re.sub(r"[^A-Z0-9/]+", "", value)
    return value.strip()


def clean_value(value: str | None) -> str | None:
    if value is None:
        return None

    value = value.replace("_", " ")
    value = normalize_spaces(value)
    value = value.strip(":- ")

    if not value:
        return None

    if re.fullmatch(r"[-. ]+", value):
        return None

    return value


def normalize_phone(value: str | None) -> str | None:
    if not value:
        return None

    digits = re.sub(r"\D", "", value)
    if not digits:
        return None

    return digits


def all_known_label_keys() -> set[str]:
    keys: set[str] = set()

    for variants in LABELS.values():
        for label in variants:
            keys.add(normalize_key(label))

    for title in SECTION_TITLES:
        keys.add(normalize_key(title))

    return keys


KNOWN_LABEL_KEYS = all_known_label_keys()


def is_label_line(line: str) -> bool:
    key = normalize_key(line)

    if not key:
        return False

    for known in KNOWN_LABEL_KEYS:
        if key == known or key.startswith(known):
            return True

    return False


def extract_value_after_label(lines: list[str], variants: list[str]) -> str | None:
    normalized_variants = [normalize_key(item) for item in variants]

    for index, line in enumerate(lines):
        raw_line = normalize_spaces(line)
        raw_key = normalize_key(raw_line)

        if not raw_key:
            continue

        for variant_key in normalized_variants:
            if raw_key == variant_key or raw_key.startswith(variant_key):
                inline_value = None

                if ":" in raw_line:
                    inline_value = clean_value(raw_line.split(":", 1)[1])
                    if inline_value:
                        return inline_value

                for next_index in range(index + 1, min(index + 4, len(lines))):
                    candidate = clean_value(lines[next_index])

                    if not candidate:
                        continue

                    if is_label_line(candidate):
                        break

                    return candidate

    return None


def extract_bank_name(lines: list[str], raw_text: str) -> str | None:
    haystack = normalize_key(raw_text)

    for alias, canonical in BANK_ALIASES.items():
        if alias in haystack:
            return canonical

    for line in lines:
        upper_line = remove_accents(line).upper()
        for alias, canonical in BANK_ALIASES.items():
            if alias in upper_line:
                return canonical

    return None


def parse_zelenza(lines: list[str], raw_text: str) -> dict[str, str | None]:
    data: dict[str, str | None] = {}

    data["entidad_bancaria"] = extract_bank_name(lines, raw_text)
    data["ot_id"] = clean_value(extract_value_after_label(lines, LABELS["ot_id"]))
    data["descripcion"] = clean_value(extract_value_after_label(lines, LABELS["descripcion"]))
    data["poblacion"] = clean_value(extract_value_after_label(lines, LABELS["poblacion"]))
    data["direccion"] = clean_value(extract_value_after_label(lines, LABELS["direccion"]))
    data["cod_postal"] = clean_value(extract_value_after_label(lines, LABELS["cod_postal"]))
    data["provincia"] = clean_value(extract_value_after_label(lines, LABELS["provincia"]))
    data["telefono_1"] = normalize_phone(extract_value_after_label(lines, LABELS["telefono_1"]))
    data["telefono_2"] = normalize_phone(extract_value_after_label(lines, LABELS["telefono_2"]))
    data["contacto"] = clean_value(extract_value_after_label(lines, LABELS["contacto"]))
    data["ref_cliente"] = clean_value(extract_value_after_label(lines, LABELS["ref_cliente"]))
    data["num_comercio"] = clean_value(extract_value_after_label(lines, LABELS["num_comercio"]))
    data["horario"] = clean_value(extract_value_after_label(lines, LABELS["horario"]))    
    data["ns_inst"] = nullify_fake_values(clean_value(extract_value_after_label(lines, LABELS["ns_inst"])))    
    data["ns_ret_afec"] = clean_value(extract_value_after_label(lines, LABELS["ns_ret_afec"]))

    if data["telefono_1"] and data["telefono_2"] and data["telefono_1"] == data["telefono_2"]:
        data["telefono_2"] = None

    return data


def normalize_serial(value: str | None) -> str | None:
    if value is None:
        return None
    value = re.sub(r"\s+", "", value).upper()
    return value or None