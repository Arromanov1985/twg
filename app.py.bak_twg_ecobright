from __future__ import annotations

import operator
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from src.kp_generator import build_kp_context, render_kp_html, html_to_pdf_bytes

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
ASSET_DIR = BASE_DIR / "assets" / "equipment"

CATALOG_FILE = DATA_DIR / "equipment_catalog.xlsx"
RULES_FILE = DATA_DIR / "selection_rules.xlsx"
ANALYSIS_FILE = DATA_DIR / "water_analysis.xlsx"

st.set_page_config(page_title="TerraWater | Робот подбора оборудования", layout="wide")

REQUIRED_ANALYSIS_COLUMNS = {"parameter", "value", "unit", "label"}
REQUIRED_CATALOG_COLUMNS = {
    "code", "name", "stage", "category", "description", "price", "image", "base", "sort_order"
}
REQUIRED_RULE_COLUMNS = {"parameter", "operator", "threshold", "equipment_codes", "reason", "active"}

OPS = {
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
    "==": operator.eq,
    "=": operator.eq,
}

# Жесткая технологическая очередность TWG для схемы и КП.
TECH_ORDER = [
    "DF100",
    "AERO",
    "VR3F100T",   # в КП отображается как TWG 1054-VR5U-100T
    "VRSD100VB",  # в КП отображается как TWG 1054-VR5D-100VB
    "SALT70",
    "BB20",
    "PP20",
    "OSMOS",
    "CARBON",
    "UV",
]

DISPLAY_NAME_OVERRIDES = {
    "VRSD100VB": "TWG 1054-VR5D-100VB",
    "VR3F100T": "TWG 1054-VR5U-100T",
}

DESCRIPTION_OVERRIDES = {
    "VRSD100VB": "Ионообменные смолы. Удаляет соли жесткости и всегда комплектуется солевым баком.",
    "VR3F100T": "Сорбционная загрузка VR5U-100T. Применяется после аэрации при повышенном железе и марганце.",
}

IMAGE_OVERRIDES = {
    "DF100": "df100.png",
    "AERO": "aero.png",
    "VR3F100T": "vr5u100t.png",
    "VRSD100VB": "vr5d100vb.png",
    "BB20": "bb20.png",
    "PP20": "pp20.png",
    "OSMOS": "osmos.png",
}

ODOR_TYPES = {
    "Нет запаха": {
        "codes": [],
        "reason": "Запах не указан — дополнительная ступень по запаху не требуется.",
    },
    "Сероводород / тухлые яйца": {
        "codes": ["AERO", "VR3F100T"],
        "reason": "Указан запах сероводорода: добавлены аэрация и сорбционная фильтрация.",
    },
    "Болотный / органический": {
        "codes": ["AERO", "CARBON"],
        "reason": "Указан болотный или органический запах: добавлены аэрация и сорбционная угольная очистка.",
    },
    "Хлор / химический": {
        "codes": ["CARBON"],
        "reason": "Указан хлорный или химический запах: добавлена угольная сорбционная очистка.",
    },
    "Нефтепродукты": {
        "codes": ["CARBON"],
        "reason": "Указан запах нефтепродуктов: добавлена сорбционная ступень. Требуется уточняющий лабораторный анализ.",
    },
    "Неопределенный неприятный запах": {
        "codes": ["AERO", "CARBON"],
        "reason": "Указан неопределенный запах: добавлены универсальные ступени аэрации и сорбционной очистки.",
    },
}

ODOR_LEVELS = {
    "Нет": 0,
    "Слабый": 1,
    "Средний": 2,
    "Сильный": 3,
}


def read_excel(path: Path) -> pd.DataFrame:
    if not path.exists():
        st.error(f"Не найден файл: {path}")
        st.stop()
    return pd.read_excel(path)


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df


def validate(df: pd.DataFrame, required: set[str], file_name: str) -> None:
    missing = required - set(df.columns)
    if missing:
        st.error(f"❌ В файле {file_name} не хватает колонок: {sorted(missing)}")
        st.stop()


def apply_catalog_overrides(catalog: pd.DataFrame) -> pd.DataFrame:
    catalog = catalog.copy()
    code_series = catalog["code"].astype(str).str.strip()
    for code, name in DISPLAY_NAME_OVERRIDES.items():
        mask = code_series == code
        catalog.loc[mask, "name"] = name
    for code, description in DESCRIPTION_OVERRIDES.items():
        mask = code_series == code
        catalog.loc[mask, "description"] = description
    for code, image in IMAGE_OVERRIDES.items():
        mask = code_series == code
        catalog.loc[mask, "image"] = image
    return catalog


def load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    analysis = normalize_columns(read_excel(ANALYSIS_FILE))
    catalog = normalize_columns(read_excel(CATALOG_FILE))
    rules = normalize_columns(read_excel(RULES_FILE))
    validate(analysis, REQUIRED_ANALYSIS_COLUMNS, ANALYSIS_FILE.name)
    validate(catalog, REQUIRED_CATALOG_COLUMNS, CATALOG_FILE.name)
    validate(rules, REQUIRED_RULE_COLUMNS, RULES_FILE.name)
    catalog["code"] = catalog["code"].astype(str).str.strip()
    catalog["base"] = catalog["base"].fillna(False).astype(bool)
    catalog["price"] = pd.to_numeric(catalog["price"], errors="coerce").fillna(0)
    catalog["sort_order"] = pd.to_numeric(catalog["sort_order"], errors="coerce").fillna(9999)
    catalog = apply_catalog_overrides(catalog)
    rules["active"] = rules["active"].fillna(True).astype(bool)
    return analysis, catalog, rules


def build_input_form(analysis: pd.DataFrame) -> dict[str, Any]:
    values: dict[str, Any] = {}
    st.subheader("1. Анализ воды и объект")
    cols = st.columns(4)
    for i, row in analysis.iterrows():
        parameter = str(row["parameter"]).strip()
        label = str(row.get("label", parameter))
        unit = str(row.get("unit", ""))
        default = row.get("value", 0)
        with cols[i % 4]:
            if str(default).lower() in {"yes", "no", "true", "false", "да", "нет"}:
                values[parameter] = st.selectbox(
                    label,
                    ["нет", "да"],
                    index=1 if str(default).lower() in {"yes", "true", "да"} else 0,
                )
            else:
                values[parameter] = st.number_input(
                    f"{label}, {unit}" if unit else label,
                    value=float(default),
                    step=0.1,
                )
    return values


def build_odor_form(values: dict[str, Any]) -> dict[str, Any]:
    st.subheader("1.1. Запах воды")
    c1, c2, c3 = st.columns([2, 1, 2])
    with c1:
        odor_type = st.selectbox("Тип запаха", list(ODOR_TYPES.keys()))
    with c2:
        odor_level = st.selectbox("Интенсивность", list(ODOR_LEVELS.keys()))
    with c3:
        st.info("Запах влияет на подбор аэрации, сорбционной загрузки и дополнительных ступеней очистки.")

    values["odor_type"] = odor_type
    values["odor_level"] = odor_level
    values["odor_score"] = ODOR_LEVELS[odor_level]
    return values


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def rule_matches(value: Any, op: str, threshold: Any) -> bool:
    op = str(op).strip()
    if op.lower() in {"yes", "да"}:
        return str(value).lower() in {"yes", "true", "да", "1"}
    if op.lower() in {"no", "нет"}:
        return str(value).lower() in {"no", "false", "нет", "0"}
    fn = OPS.get(op)
    if not fn:
        return False
    try:
        return fn(float(value), float(threshold))
    except Exception:
        return False


def add_code(selected: list[str], catalog: pd.DataFrame, code: str) -> None:
    code = str(code).strip()
    available_codes = set(catalog["code"].astype(str))
    if code and code in available_codes and code not in selected:
        selected.append(code)


def apply_odor_selection(
    selected: list[str],
    reasons: list[str],
    values: dict[str, Any],
    catalog: pd.DataFrame,
) -> None:
    odor_type = str(values.get("odor_type", "Нет запаха"))
    odor_level = str(values.get("odor_level", "Нет"))
    odor_score = int(values.get("odor_score", 0) or 0)

    if odor_type == "Нет запаха" or odor_score == 0:
        return

    setup = ODOR_TYPES.get(odor_type, ODOR_TYPES["Неопределенный неприятный запах"])
    for code in setup["codes"]:
        add_code(selected, catalog, code)

    reasons.append(f"{setup['reason']} Интенсивность запаха: {odor_level.lower()}.")

    if odor_score >= 3:
        add_code(selected, catalog, "CARBON")
        reasons.append("Так как запах сильный, дополнительно рекомендована сорбционная ступень для улучшения вкуса и запаха воды.")


def apply_engineering_rules(
    selected: list[str],
    reasons: list[str],
    values: dict[str, Any],
    catalog: pd.DataFrame,
) -> None:
    iron = safe_float(values.get("iron", 0))
    manganese = safe_float(values.get("manganese", 0))
    hardness = safe_float(values.get("hardness", 0))
    iron_manganese_sum = iron + manganese

    add_code(selected, catalog, "DF100")

    if 5 <= iron_manganese_sum <= 10:
        add_code(selected, catalog, "AERO")
        add_code(selected, catalog, "VR3F100T")
        reasons.append(
            "Сумма железа и марганца от 5 до 10 мг/л: требуется аэрация и сорбционный фильтр TWG 1054-VR5U-100T."
        )
    elif iron_manganese_sum > 10:
        add_code(selected, catalog, "AERO")
        add_code(selected, catalog, "VR3F100T")
        reasons.append(
            "Сумма железа и марганца выше 10 мг/л: требуется аэрация и усиленная сорбционная ступень; рекомендуется инженерная проверка схемы."
        )

    if hardness > 0 and "VRSD100VB" in selected:
        add_code(selected, catalog, "SALT70")
    elif hardness >= 5:
        add_code(selected, catalog, "VRSD100VB")
        add_code(selected, catalog, "SALT70")
        reasons.append("Высокая жесткость: требуется умягчитель TWG 1054-VR5D-100VB и солевой бак TWG SALT-70L PRO.")

    add_code(selected, catalog, "BB20")
    add_code(selected, catalog, "PP20")


def normalize_selection_order(selected: list[str]) -> list[str]:
    unique = []
    for code in selected:
        if code not in unique:
            unique.append(code)

    priority = {code: index for index, code in enumerate(TECH_ORDER)}
    return sorted(unique, key=lambda code: priority.get(code, 999 + unique.index(code)))


def select_equipment(values: dict[str, Any], catalog: pd.DataFrame, rules: pd.DataFrame) -> tuple[list[str], list[str]]:
    # Базовые позиции из Excel сохраняются, но итоговая очередность задается инженерной схемой TWG.
    selected: list[str] = catalog.loc[catalog["base"], "code"].astype(str).tolist()
    reasons: list[str] = []

    for _, rule in rules[rules["active"]].iterrows():
        parameter = str(rule["parameter"]).strip()
        if parameter not in values:
            continue
        if rule_matches(values[parameter], rule["operator"], rule["threshold"]):
            codes = [c.strip() for c in str(rule["equipment_codes"]).replace(";", ",").split(",") if c.strip()]
            for code in codes:
                add_code(selected, catalog, code)
            reason = str(rule.get("reason", "")).strip()
            if reason:
                reasons.append(reason)

    apply_engineering_rules(selected, reasons, values, catalog)
    apply_odor_selection(selected, reasons, values, catalog)

    if "VRSD100VB" in selected:
        add_code(selected, catalog, "SALT70")

    return normalize_selection_order(selected), reasons


def enrich_analysis_for_kp(analysis: pd.DataFrame, values: dict[str, Any]) -> pd.DataFrame:
    extra_rows = pd.DataFrame([
        {
            "parameter": "odor_type",
            "value": values.get("odor_type", "Нет запаха"),
            "unit": "",
            "label": "Тип запаха",
        },
        {
            "parameter": "odor_level",
            "value": values.get("odor_level", "Нет"),
            "unit": "",
            "label": "Интенсивность запаха",
        },
    ])
    return pd.concat([analysis, extra_rows], ignore_index=True)


def image_path(file_name: str) -> Path:
    return ASSET_DIR / str(file_name).strip()


def render_visual_kp(selected_df: pd.DataFrame, reasons: list[str], values: dict[str, Any], client_data: dict[str, Any]) -> None:
    st.markdown("---")
    st.title("Коммерческое предложение")
    st.markdown("### Система очистки воды для частного дома")
    st.caption(f"Клиент: {client_data.get('client_name', 'Частный клиент')} | Объект: {client_data.get('object_type', 'Частный дом')}")

    top = st.columns([1.2, 3])
    with top[0]:
        st.info(
            f"**Для кого**\n\n"
            f"{client_data.get('object_type', 'Частный дом')}\n\n"
            f"Источник: {client_data.get('water_source', 'скважина')}\n\n"
            f"Проживающих: до {int(values.get('people', 4))} человек\n\n"
            f"Расход: до {values.get('flow_peak', 1.5)} м³/ч\n\n"
            f"Запах: {values.get('odor_type', 'Нет запаха')} / {values.get('odor_level', 'Нет')}"
        )

    with top[1]:
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Чистая вода", "без запаха")
        k2.metric("Защита техники", "от накипи")
        k3.metric("Комфорт", "для семьи")
        k4.metric("Гарантия", "5 лет")

    st.subheader("2. Как работает система")

    selected_df_scheme = selected_df[
        selected_df["code"] != "SALT70"
    ].copy()

    step_cols = st.columns(
        min(len(selected_df_scheme), 8)
        if len(selected_df_scheme)
        else 1
    )

    for i, (_, item) in enumerate(selected_df_scheme.iterrows(), start=1):
        with step_cols[(i - 1) % len(step_cols)]:
            code = str(item["code"]).strip()

            image_file = IMAGE_OVERRIDES.get(
                code,
                str(item.get("image", "")).strip()
            )

            p = image_path(image_file)

            if p.exists():
                st.image(str(p), width="stretch")
            else:
                st.warning(f"Нет картинки: {image_file}")

            st.markdown(f"**{i}. {item['name']}**")
            st.caption(str(item["description"]))

    st.subheader("3. Комплектация и стоимость")
    table = selected_df[["name", "code", "price", "description"]].copy()
    table.insert(0, "№", range(1, len(table) + 1))
    table.rename(
        columns={
            "name": "Наименование",
            "code": "Модель",
            "price": "Цена, ₽",
            "description": "Назначение",
        },
        inplace=True,
    )

    st.dataframe(table, width="stretch", hide_index=True)
    st.success(
        f"Итого за базовый комплект: {selected_df['price'].sum():,.0f} ₽".replace(",", " ")
    )

    if reasons:
        st.subheader("Почему выбрано это оборудование")
        for reason in reasons:
            st.write("✅ " + reason)


def save_uploaded_image(uploaded_file, code: str) -> str | None:
    if uploaded_file is None:
        return None
    suffix = Path(uploaded_file.name).suffix.lower() or ".png"
    safe_code = "".join(ch for ch in code if ch.isalnum() or ch in {"-", "_"})
    target = ASSET_DIR / f"{safe_code}{suffix}"
    target.write_bytes(uploaded_file.getbuffer())
    return target.name


def admin_panel(catalog: pd.DataFrame, rules: pd.DataFrame) -> None:
    with st.expander("Администрирование: прайс, оборудование, правила и картинки"):
        st.write("Здесь можно быстро проверить базу. Для постоянных изменений редактируйте Excel-файлы в папке `data`.")
        st.dataframe(catalog, width="stretch", hide_index=True)
        st.dataframe(rules, width="stretch", hide_index=True)
        st.subheader("Заменить картинку оборудования")
        code = st.selectbox("Оборудование", catalog["code"].tolist(), format_func=lambda c: f"{c} — {catalog.loc[catalog['code']==c, 'name'].iloc[0]}")
        file = st.file_uploader("Новая картинка PNG/JPG/SVG", type=["png", "jpg", "jpeg", "svg"])
        if st.button("Сохранить картинку"):
            saved = save_uploaded_image(file, code)
            if saved:
                st.success(f"Картинка сохранена: assets/equipment/{saved}. Теперь укажите это имя в equipment_catalog.xlsx в колонке image.")
            else:
                st.warning("Сначала выберите файл картинки.")


def build_client_form() -> dict[str, Any]:
    st.subheader("0. Данные клиента")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        client_name = st.text_input("Клиент", "Частный клиент")
    with c2:
        object_type = st.text_input("Тип объекта", "Частный дом")
    with c3:
        water_source = st.text_input("Источник воды", "Скважина")
    with c4:
        manager = st.text_input("Менеджер", "TerraWater Group")
    address = st.text_input("Адрес/объект для КП", "")
    return {
        "client_name": client_name,
        "object_type": object_type,
        "water_source": water_source,
        "manager": manager,
        "address": address,
    }


def export_kp_block(selected_df: pd.DataFrame, reasons: list[str], values: dict[str, Any], client_data: dict[str, Any], analysis: pd.DataFrame) -> None:
    st.subheader("4. Формирование КП")
    analysis_for_kp = enrich_analysis_for_kp(analysis, values)
    context = build_kp_context(
        client_data=client_data,
        values=values,
        analysis_df=analysis_for_kp,
        selected_df=selected_df,
        reasons=reasons,
        base_dir=BASE_DIR,
    )
    html = render_kp_html(context, BASE_DIR / "templates" / "kp_template.html")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.download_button(
            "Скачать КП в HTML",
            data=html.encode("utf-8"),
            file_name="KP_TerraWater.html",
            mime="text/html",
            width="stretch",
        )
    with col2:
        try:
            pdf = html_to_pdf_bytes(html, base_dir=BASE_DIR)
            st.download_button(
                "Скачать КП в PDF",
                data=pdf,
                file_name="KP_TerraWater.pdf",
                mime="application/pdf",
                width="stretch",
            )
        except Exception as exc:
            st.warning("PDF не сформировался. HTML доступен для скачивания; его можно открыть в браузере и распечатать в PDF.")
            st.caption(str(exc))
    with col3:
        if st.checkbox("Показать HTML-превью"):
            st.components.v1.html(html, height=900, scrolling=True)


def main() -> None:
    st.sidebar.image(str(BASE_DIR / "assets" / "twg_logo.svg"), width="stretch")
    st.sidebar.title("TerraWater Robot")
    st.sidebar.write("Подбор оборудования по анализу воды и формирование КП в HTML/PDF.")

    analysis, catalog, rules = load_data()
    client_data = build_client_form()
    values = build_input_form(analysis)
    values = build_odor_form(values)
    selected_codes, reasons = select_equipment(values, catalog, rules)
    selected_df = catalog[catalog["code"].isin(selected_codes)].copy()
    selected_df["_order"] = selected_df["code"].apply(lambda x: selected_codes.index(x) if x in selected_codes else 999)
    selected_df = selected_df.sort_values(["_order", "sort_order"])

    render_visual_kp(selected_df, reasons, values, client_data)
    export_kp_block(selected_df, reasons, values, client_data, analysis)
    admin_panel(catalog, rules)


if __name__ == "__main__":
    main()
