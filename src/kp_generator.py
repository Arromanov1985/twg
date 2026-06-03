from __future__ import annotations

import base64
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
from jinja2 import Template


HIDDEN_KP_CODES = {"SALT70"}


def _file_to_data_uri(path: Path) -> str:
    if not path.exists():
        return ""
    ext = path.suffix.lower().lstrip(".")
    mime = {
        "svg": "image/svg+xml",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
    }.get(ext, "application/octet-stream")
    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{data}"


def _fmt_money(value: Any) -> str:
    try:
        return f"{float(value):,.0f}".replace(",", " ") + " ₽"
    except Exception:
        return str(value)


def _row_price(row: pd.Series) -> float:
    for key in ("retail_price", "Розница", "price"):
        try:
            value = row.get(key, None)
            if value is not None and not pd.isna(value):
                return float(value)
        except Exception:
            continue
    return 0.0


def _is_visible_in_kp(row: pd.Series) -> bool:
    return str(row.get("code", "")).strip() not in HIDDEN_KP_CODES


def build_kp_context(
    client_data: dict[str, Any],
    values: dict[str, Any],
    analysis_df: pd.DataFrame,
    selected_df: pd.DataFrame,
    reasons: list[str],
    base_dir: Path,
    kp_type: str = "client",
) -> dict[str, Any]:
    equipment = []
    visible_df = selected_df[selected_df.apply(_is_visible_in_kp, axis=1)].copy()
    for index, (_, row) in enumerate(visible_df.iterrows(), start=1):
        image = base_dir / "assets" / "equipment" / str(row.get("image", ""))
        qty = int(float(row.get("qty", 1) or 1))
        price = _row_price(row)
        equipment.append({
            "num": index,
            "code": str(row.get("code", "")),
            "name": str(row.get("name", "")),
            "category": str(row.get("category", "")),
            "description": str(row.get("description", "")),
            "qty": qty,
            "price": price,
            "sum": price * qty,
            "price_text": _fmt_money(price),
            "sum_text": _fmt_money(price * qty),
            "partner_price": float(row.get("partner_price", row.get("Партнер", price)) or price),
            "partner_sum": float(row.get("partner_price", row.get("Партнер", price)) or price) * qty,
            "partner_price_text": _fmt_money(float(row.get("partner_price", row.get("Партнер", price)) or price)),
            "partner_sum_text": _fmt_money(float(row.get("partner_price", row.get("Партнер", price)) or price) * qty),
            "image_uri": _file_to_data_uri(image),
        })

    analysis_rows = []
    for _, row in analysis_df.iterrows():
        parameter = str(row.get("parameter", "")).strip()
        value = values.get(parameter, row.get("value", ""))
        unit = "" if pd.isna(row.get("unit", "")) else str(row.get("unit", ""))
        analysis_rows.append({
            "label": str(row.get("label", parameter)),
            "value": value,
            "unit": unit,
        })

    total = sum(item["sum"] for item in equipment)
    partner_total = sum(item.get("partner_sum", item["sum"]) for item in equipment)
    benefit_total = total - partner_total
    return {
        "date": date.today().strftime("%d.%m.%Y"),
        "kp_type": kp_type,
        "is_partner_kp": kp_type == "partner",
        "client": client_data,
        "values": values,
        "analysis_rows": analysis_rows,
        "equipment": equipment,
        "reasons": reasons,
        "total": total,
        "total_text": _fmt_money(total),
        "partner_total_text": _fmt_money(partner_total),
        "benefit_total_text": _fmt_money(benefit_total),
        "logo_uri": _file_to_data_uri(base_dir / "assets" / "twg_logo.png"),
        "people": int(float(values.get("people", 4) or 4)),
        "flow_peak": values.get("flow_peak", 1.5),
    }


def render_kp_html(context: dict[str, Any], template_path: Path) -> str:
    template = Template(template_path.read_text(encoding="utf-8"))
    return template.render(**context)


def html_to_pdf_bytes(html: str, base_dir: Path | None = None) -> bytes:
    raise RuntimeError("Серверная генерация PDF отключена. Используйте веб-КП: Печать -> Сохранить как PDF.")
