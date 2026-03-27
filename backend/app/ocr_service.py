import re
from functools import lru_cache
from pathlib import Path


def _import_paddle():
    from paddleocr import PaddleOCR
    return PaddleOCR


@lru_cache(maxsize=1)
def get_ocr_engine():
    PaddleOCR = _import_paddle()
    return PaddleOCR(
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
    )


def _clean_line(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _extract_phone_candidates(lines: list[str]) -> list[str]:
    text = " | ".join(lines)
    pattern = re.compile(r"(?:\+?\d[\d\s\-().]{7,}\d)")
    raw_matches = pattern.findall(text)

    candidates: list[str] = []
    seen: set[str] = set()

    for match in raw_matches:
        normalized = re.sub(r"\D", "", match)

        if len(normalized) < 9 or len(normalized) > 15:
            continue

        if normalized not in seen:
            seen.add(normalized)
            candidates.append(normalized)

    return candidates


def _extract_name_candidates(lines: list[str]) -> list[str]:
    blacklist = {
        "whatsapp",
        "llamar",
        "mensaje",
        "en línea",
        "online",
        "ayer",
        "hoy",
        "buscar",
        "editar",
        "copiar",
        "reenviar",
        "bloquear",
        "eliminar",
        "instagram",
        "facebook",
        "tiktok",
        "telegram",
    }

    candidates: list[str] = []
    seen: set[str] = set()

    for line in lines:
        candidate = _clean_line(line)

        if not candidate:
            continue

        lower = candidate.lower()

        if lower in blacklist:
            continue

        if "http" in lower or "www" in lower or "@" in lower:
            continue

        if sum(ch.isdigit() for ch in candidate) > 1:
            continue

        if len(candidate) < 2 or len(candidate) > 40:
            continue

        letters = sum(ch.isalpha() for ch in candidate)
        spaces = candidate.count(" ")
        ratio = (letters + spaces) / max(len(candidate), 1)

        if ratio < 0.75:
            continue

        if candidate not in seen:
            seen.add(candidate)
            candidates.append(candidate)

    return candidates[:5]


def run_ocr(image_path: Path) -> dict:
    ocr = get_ocr_engine()
    results = ocr.predict(str(image_path))
    first = next(iter(results), None)

    if first is None:
        return {
            "raw_text": "",
            "lines": [],
            "avg_confidence": 0.0,
            "phone_candidates": [],
            "name_candidates": [],
            "parsed_phone": None,
            "parsed_name": None,
        }

    payload = first.json
    rec_texts = payload.get("res", {}).get("rec_texts", []) or []
    rec_scores = payload.get("res", {}).get("rec_scores", []) or []

    lines = [_clean_line(text) for text in rec_texts if _clean_line(text)]

    if rec_scores:
        avg_confidence = round(sum(float(score) for score in rec_scores) / len(rec_scores), 4)
    else:
        avg_confidence = 0.0

    phone_candidates = _extract_phone_candidates(lines)
    name_candidates = _extract_name_candidates(lines)

    return {
        "raw_text": "\n".join(lines),
        "lines": lines,
        "avg_confidence": avg_confidence,
        "phone_candidates": phone_candidates,
        "name_candidates": name_candidates,
        "parsed_phone": phone_candidates[0] if phone_candidates else None,
        "parsed_name": name_candidates[0] if name_candidates else None,
    }