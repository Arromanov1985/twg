# -*- coding: utf-8 -*-
from __future__ import annotations

import base64
import json
import mimetypes
from typing import Any

from openai import OpenAI


WATER_ANALYSIS_SYSTEM_PROMPT = """
Ты инженер водоочистки Terra Water Group.

Распознай показатели анализа воды с изображения лабораторного анализа.

Верни только JSON. Без Markdown. Без пояснений.

Формат:
{
  "recognized": true,
  "confidence": "high|medium|low",
  "source_quality": "описание качества изображения",
  "values": {
    "ph": null,
    "iron": null,
    "manganese": null,
    "hardness": null,
    "tds": null,
    "permanganate": null,
    "odor_h2s": null,
    "bacteria": "да|нет|не указано",
    "turbidity": null,
    "color": null,
    "ammonium": null
  },
  "warnings": [],
  "raw_detected_text": ""
}

Правила:
- Не выдумывай значения.
- Если показатель не найден, верни null.
- Если число написано через запятую, преобразуй в число с точкой.
- Если написано "менее 0,1", верни 0.1 и добавь предупреждение.
- pH / водородный показатель -> ph.
- Железо / Fe / железо общее -> iron, мг/л.
- Марганец / Mn -> manganese, мг/л.
- Жесткость / общая жесткость -> hardness, мг-экв/л.
- Сухой остаток / минерализация / TDS -> tds, мг/л.
- Перманганатная окисляемость / ПМО -> permanganate, мгО2/л.
- Запах / сероводород / H2S -> odor_h2s.
- ОМЧ / ОКБ / ТКБ / колиформные бактерии -> bacteria.
- Если бактерии обнаружены или есть превышение микробиологии, bacteria = "да".
- Если написано "не обнаружено", "отсутствует", "0", bacteria = "нет".
- Если бактериология не указана, bacteria = "не указано".
- Если единицы измерения неясны, добавь предупреждение.
"""


def file_bytes_to_data_url(raw: bytes, filename: str | None = None, mime: str | None = None) -> str:
    guessed_mime = mime or mimetypes.guess_type(filename or "")[0] or "image/jpeg"
    encoded = base64.b64encode(raw).decode("utf-8")
    return f"data:{guessed_mime};base64,{encoded}"


def extract_json_object(text: str) -> dict[str, Any]:
    text = str(text or "").strip()

    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else {}
    except Exception:
        pass

    start = text.find("{")
    end = text.rfind("}")

    if start >= 0 and end > start:
        try:
            data = json.loads(text[start:end + 1])
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    return {}


def normalize_number(value: Any) -> Any:
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip().replace(",", ".")
    low = text.lower()

    if low in {"", "-", "nan", "none", "null", "не указано", "нет данных"}:
        return None

    for prefix in ["<", "≤", "менее", "до"]:
        if low.startswith(prefix):
            cleaned = (
                low.replace("менее", "")
                .replace("до", "")
                .replace("<", "")
                .replace("≤", "")
                .strip()
            )
            try:
                return float(cleaned)
            except Exception:
                return None

    try:
        return float(text)
    except Exception:
        return None


def normalize_bacteria(value: Any) -> str:
    text = str(value or "").strip().lower()

    if text in {"да", "обнаружено", "присутствует", "есть", "выше нормы", "превышение"}:
        return "да"

    if text in {"нет", "не обнаружено", "отсутствует", "0", "норма", "в норме"}:
        return "нет"

    return "не указано"


def normalize_water_analysis_result(data: dict[str, Any]) -> dict[str, Any]:
    values = data.get("values") or {}

    return {
        "recognized": bool(data.get("recognized", True)),
        "confidence": data.get("confidence") or "medium",
        "source_quality": data.get("source_quality") or "",
        "values": {
            "ph": normalize_number(values.get("ph")),
            "iron": normalize_number(values.get("iron")),
            "manganese": normalize_number(values.get("manganese")),
            "hardness": normalize_number(values.get("hardness")),
            "tds": normalize_number(values.get("tds")),
            "permanganate": normalize_number(values.get("permanganate")),
            "odor_h2s": normalize_number(values.get("odor_h2s")),
            "bacteria": normalize_bacteria(values.get("bacteria")),
            "turbidity": normalize_number(values.get("turbidity")),
            "color": normalize_number(values.get("color")),
            "ammonium": normalize_number(values.get("ammonium")),
        },
        "warnings": data.get("warnings") or [],
        "raw_detected_text": data.get("raw_detected_text") or "",
    }


def recognize_water_analysis_image(
    *,
    api_key: str,
    raw: bytes,
    filename: str,
    mime: str | None = None,
    model: str = "gpt-4.1-mini",
) -> dict[str, Any]:
    client = OpenAI(api_key=api_key)
    data_url = file_bytes_to_data_url(raw, filename, mime)

    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": WATER_ANALYSIS_SYSTEM_PROMPT},
                    {"type": "input_image", "image_url": data_url},
                ],
            }
        ],
    )

    parsed = extract_json_object(response.output_text)

    if not parsed:
        return {
            "recognized": False,
            "confidence": "low",
            "source_quality": "Не удалось получить JSON от ИИ",
            "values": {
                "ph": None,
                "iron": None,
                "manganese": None,
                "hardness": None,
                "tds": None,
                "permanganate": None,
                "odor_h2s": None,
                "bacteria": "не указано",
                "turbidity": None,
                "color": None,
                "ammonium": None,
            },
            "warnings": [
                "ИИ не вернул корректный JSON. Загрузите более четкое фото или введите данные вручную."
            ],
            "raw_detected_text": response.output_text or "",
        }

    return normalize_water_analysis_result(parsed)

def recognize_water_analysis_pdf(
    *,
    api_key: str,
    raw: bytes,
    filename: str,
    model: str = "gpt-4.1-mini",
) -> dict[str, Any]:
    """
    Распознает анализ воды из PDF.
    PDF отправляется в OpenAI как файл, модель извлекает текст/таблицы и возвращает JSON.
    """
    client = OpenAI(api_key=api_key)

    uploaded = client.files.create(
        file=(filename or "analysis.pdf", raw, "application/pdf"),
        purpose="assistants"
    )

    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": WATER_ANALYSIS_SYSTEM_PROMPT},
                    {"type": "input_file", "file_id": uploaded.id}
                ],
            }
        ],
    )

    parsed = extract_json_object(response.output_text)

    if not parsed:
        return {
            "recognized": False,
            "confidence": "low",
            "source_quality": "Не удалось получить JSON от ИИ по PDF",
            "values": {
                "ph": None,
                "iron": None,
                "manganese": None,
                "hardness": None,
                "tds": None,
                "permanganate": None,
                "odor_h2s": None,
                "bacteria": "не указано",
                "turbidity": None,
                "color": None,
                "ammonium": None,
            },
            "warnings": [
                "ИИ не вернул корректный JSON по PDF. Загрузите фото первой страницы анализа или введите данные вручную."
            ],
            "raw_detected_text": response.output_text or "",
        }

    return normalize_water_analysis_result(parsed)


def recognize_water_analysis_document(
    *,
    api_key: str,
    raw: bytes,
    filename: str,
    mime: str | None = None,
    model: str = "gpt-4.1-mini",
) -> dict[str, Any]:
    """Маршрутизатор: PDF распознаем как файл, изображения — как image input."""
    mime_clean = str(mime or "").lower()
    filename_clean = str(filename or "").lower()

    if mime_clean == "application/pdf" or filename_clean.endswith(".pdf"):
        return recognize_water_analysis_pdf(
            api_key=api_key,
            raw=raw,
            filename=filename,
            model=model,
        )

    return recognize_water_analysis_image(
        api_key=api_key,
        raw=raw,
        filename=filename,
        mime=mime,
        model=model,
    )

