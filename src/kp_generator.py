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


def _is_visible_in_kp(row: pd.Series) -> bool:
    return str(row.get("code", "")).strip() not in HIDDEN_KP_CODES


def build_kp_context(
    client_data: dict[str, Any],
    values: dict[str, Any],
    analysis_df: pd.DataFrame,
    selected_df: pd.DataFrame,
    reasons: list[str],
    base_dir: Path,
) -> dict[str, Any]:
    equipment = []
    visible_df = selected_df[selected_df.apply(_is_visible_in_kp, axis=1)].copy()
    for index, (_, row) in enumerate(visible_df.iterrows(), start=1):
        image = base_dir / "assets" / "equipment" / str(row.get("image", ""))
        equipment.append({
            "num": index,
            "code": str(row.get("code", "")),
            "name": str(row.get("name", "")),
            "category": str(row.get("category", "")),
            "description": str(row.get("description", "")),
            "price": float(row.get("price", 0) or 0),
            "price_text": _fmt_money(row.get("price", 0)),
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

    total = sum(item["price"] for item in equipment)
    return {
        "date": date.today().strftime("%d.%m.%Y"),
        "client": client_data,
        "values": values,
        "analysis_rows": analysis_rows,
        "equipment": equipment,
        "reasons": reasons,
        "total": total,
        "total_text": _fmt_money(total),
        "logo_uri": _file_to_data_uri(base_dir / "assets" / "twg_logo.svg"),
        "people": int(float(values.get("people", 4) or 4)),
        "flow_peak": values.get("flow_peak", 1.5),
    }


def render_kp_html(context: dict[str, Any], template_path: Path) -> str:
    template = Template(template_path.read_text(encoding="utf-8"))
    return template.render(**context)


def html_to_pdf_bytes(html: str, base_dir: Path | None = None) -> bytes:
    # xhtml2pdf converts the HTML template to a PDF without external services.
    # The HTML uses embedded data-uri images, so the PDF can be generated locally.
    from io import BytesIO

    output = BytesIO()
    from xhtml2pdf import pisa
    status = pisa.CreatePDF(src=html, dest=output, encoding="utf-8")
    if status.err:
        raise RuntimeError("xhtml2pdf не смог сформировать PDF. Скачайте HTML и распечатайте его в PDF через браузер.")
    return output.getvalue()
