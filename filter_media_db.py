# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
FILTER_MEDIA_DB_PATH = BASE_DIR / "data" / "filter_media_ekobright.json"


def load_filter_media_db() -> dict[str, Any]:
    """Загружает справочник фильтрующих загрузок ЭКОБРАЙТ/TWG."""
    if not FILTER_MEDIA_DB_PATH.exists():
        return {"version": "", "groups": {}}

    return json.loads(FILTER_MEDIA_DB_PATH.read_text(encoding="utf-8"))


def iter_filter_media_items() -> list[dict[str, Any]]:
    """Возвращает плоский список всех загрузок из справочника."""
    db = load_filter_media_db()
    result: list[dict[str, Any]] = []

    for group_key, group in db.get("groups", {}).items():
        for item_key, item in group.get("items", {}).items():
            row = dict(item)
            row["id"] = item_key
            row["group"] = group_key
            row["group_title"] = group.get("title", group_key)
            result.append(row)

    return result


def find_filter_media_by_article(article_or_name: str) -> dict[str, Any] | None:
    """Ищет загрузку по артикулу или названию."""
    query = str(article_or_name or "").strip().lower()
    if not query:
        return None

    for item in iter_filter_media_items():
        haystack = " ".join([
            str(item.get("id", "")),
            str(item.get("article", "")),
            str(item.get("name", "")),
        ]).lower()

        if query in haystack or haystack in query:
            return item

    return None


def get_filter_media_description(article_or_name: str) -> str:
    """Возвращает клиентское описание загрузки для КП."""
    item = find_filter_media_by_article(article_or_name)
    if not item:
        return ""

    return str(item.get("description_for_kp") or item.get("purpose") or "")
