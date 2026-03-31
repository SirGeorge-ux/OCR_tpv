import json
from pathlib import Path
from typing import Any

from paddlex import create_pipeline


class OCRService:
    def __init__(self) -> None:
        self.pipeline = create_pipeline(pipeline="OCR")

    def run(self, image_path: str | Path) -> dict[str, Any]:
        output = self.pipeline.predict(
            input=str(image_path),
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
        )

        first_result = next(iter(output))
        payload = self._normalize_result(first_result)
        res = payload.get("res", payload)

        text_lines = self._extract_text_lines(res)
        scores = self._extract_scores(res)
        confidence = self._average_score(scores)

        return {
            "raw_payload": res,
            "raw_payload_json": json.dumps(res, ensure_ascii=False, default=str),
            "text_lines": text_lines,
            "raw_text": "\n".join(text_lines),
            "confidence": confidence,
        }

    def _normalize_result(self, result: Any) -> dict[str, Any]:
        if isinstance(result, dict):
            return result

        json_attr = getattr(result, "json", None)

        if isinstance(json_attr, dict):
            return json_attr

        if isinstance(json_attr, str):
            try:
                return json.loads(json_attr)
            except json.JSONDecodeError:
                return {"raw": json_attr}

        if callable(json_attr):
            value = json_attr()
            if isinstance(value, dict):
                return value
            if isinstance(value, str):
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return {"raw": value}

        return {"raw": str(result)}

    def _extract_text_lines(self, payload: dict[str, Any]) -> list[str]:
        raw_lines = payload.get("rec_texts") or payload.get("rec_text") or []
        if not isinstance(raw_lines, list):
            return []

        return [str(item).strip() for item in raw_lines if str(item).strip()]

    def _extract_scores(self, payload: dict[str, Any]) -> list[float]:
        raw_scores = payload.get("rec_scores") or payload.get("rec_score") or []
        scores: list[float] = []

        if isinstance(raw_scores, list):
            for item in raw_scores:
                try:
                    scores.append(float(item))
                except (TypeError, ValueError):
                    continue

        return scores

    def _average_score(self, scores: list[float]) -> float | None:
        if not scores:
            return None
        return round(sum(scores) / len(scores), 4)


ocr_service: OCRService | None = None


def get_ocr_service() -> OCRService:
    global ocr_service
    if ocr_service is None:
        ocr_service = OCRService()
    return ocr_service