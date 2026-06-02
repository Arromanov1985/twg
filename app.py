from __future__ import annotations

import operator
from datetime import date
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
    "VR3F100T",
    "ECO_ORGANIC_B",
    "ECO_ORGANIC_PLUS_B",
    "TWG_ORGANIC_MIX",
    "VRSD100VB",
    "ECO_STD",
    "ECO_STD_B",
    "SALT70",
    "BB20",
    "PP20",
    "CARBON",
    "UV",
    "OSMOS",
]


STAGE_NAMES = {
    1: "Механическая очистка",
    2: "Аэрация",
    3: "Обезжелезивание",
    4: "Умягчение",
    5: "Финишная механика",
    6: "Сорбционная доочистка",
    7: "Питьевая вода",
    8: "Обеззараживание и опции",
}

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


TWG_MEDIA_CODES = {"VR3F100T", "VRSD100VB", "TWG_ORGANIC_MIX"}
ECOBRIGHT_MEDIA_CODES = {
    "ECO_STD",
    "ECO_STD_B",
    "ECO_ORGANIC",
    "ECO_ORGANIC_B",
    "ECO_ORGANIC_PLUS",
    "ECO_ORGANIC_PLUS_B",
}

EXTRA_PRODUCTS = [
    {
        "code": "TWG_ORGANIC_MIX",
        "name": "TWG VR5U Organic Mix",
        "stage": "Микс-загрузка",
        "category": "media",
        "description": "Комплексная загрузка TWG для воды с органикой, цветностью, запахом и повышенной окисляемостью.",
        "price": 0,
        "image": "vr5u100t.png",
        "base": False,
        "sort_order": 35,
    },
    {
        "code": "ECO_STD",
        "name": "ЭКОБРАЙТ Стандарт",
        "stage": "Ионообменная загрузка",
        "category": "media",
        "description": "Na-катионит для умягчения воды без выраженного железа, марганца и органики.",
        "price": 0,
        "image": "vr5d100vb.png",
        "base": False,
        "sort_order": 60,
    },
    {
        "code": "ECO_STD_B",
        "name": "ЭКОБРАЙТ Стандарт Б",
        "stage": "Ионообменная загрузка",
        "category": "media",
        "description": "Ионообменная загрузка для умягчения в более сложной воде.",
        "price": 0,
        "image": "vr5d100vb.png",
        "base": False,
        "sort_order": 61,
    },
    {
        "code": "ECO_ORGANIC",
        "name": "ЭКОБРАЙТ Органик",
        "stage": "Микс-загрузка",
        "category": "media",
        "description": "Микс для воды с органикой, цветностью и повышенной окисляемостью без сильного железа.",
        "price": 0,
        "image": "vr5u100t.png",
        "base": False,
        "sort_order": 62,
    },
    {
        "code": "ECO_ORGANIC_B",
        "name": "ЭКОБРАЙТ Органик Б",
        "stage": "Микс-загрузка",
        "category": "media",
        "description": "Микс-загрузка для воды с железом, марганцем, запахом и умеренной органикой.",
        "price": 0,
        "image": "vr5u100t.png",
        "base": False,
        "sort_order": 63,
    },
    {
        "code": "ECO_ORGANIC_PLUS",
        "name": "ЭКОБРАЙТ Органик+",
        "stage": "Микс-загрузка",
        "category": "media",
        "description": "Усиленный микс для воды с высокой окисляемостью, органикой и цветностью.",
        "price": 0,
        "image": "vr5u100t.png",
        "base": False,
        "sort_order": 64,
    },
    {
        "code": "ECO_ORGANIC_PLUS_B",
        "name": "ЭКОБРАЙТ Органик+ Б",
        "stage": "Микс-загрузка",
        "category": "media",
        "description": "Усиленный микс для сложной воды: органика, железо, марганец, запах, высокая окисляемость.",
        "price": 0,
        "image": "vr5u100t.png",
        "base": False,
        "sort_order": 65,
    },
]

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


PRICE_COLUMN_ALIASES = {
    "retail": ["Розница", "Цена Розница", "Цена розница", "retail_price", "price_retail", "price"],
    "partner": ["Партнер", "Партнёр", "Цена Партнер", "Цена партнера", "Цена партнёра", "partner_price", "price_partner"],
}


def _first_existing_column(df: pd.DataFrame, names: list[str]) -> str | None:
    normalized = {str(col).strip().lower(): col for col in df.columns}
    for name in names:
        key = name.strip().lower()
        if key in normalized:
            return normalized[key]
    return None


def ensure_price_columns(catalog: pd.DataFrame) -> pd.DataFrame:
    catalog = catalog.copy()

    retail_col = _first_existing_column(catalog, PRICE_COLUMN_ALIASES["retail"])
    partner_col = _first_existing_column(catalog, PRICE_COLUMN_ALIASES["partner"])

    if retail_col is None:
        catalog["Розница"] = 0
        retail_col = "Розница"

    catalog["Розница"] = pd.to_numeric(catalog[retail_col], errors="coerce").fillna(0)

    if partner_col is None:
        catalog["Партнер"] = catalog["Розница"]
    else:
        catalog["Партнер"] = pd.to_numeric(catalog[partner_col], errors="coerce").fillna(catalog["Розница"])

    catalog["Выгода"] = catalog["Розница"] - catalog["Партнер"]

    # ВАЖНО: для клиента и КП используем только розничную цену.
    catalog["retail_price"] = catalog["Розница"]
    catalog["partner_price"] = catalog["Партнер"]
    catalog["benefit"] = catalog["Выгода"]
    catalog["price"] = catalog["Розница"]

    return catalog


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



def add_extra_products(catalog: pd.DataFrame) -> pd.DataFrame:
    catalog = catalog.copy()
    existing_codes = set(catalog["code"].astype(str))
    rows = []
    for row in EXTRA_PRODUCTS:
        if row["code"] not in existing_codes:
            rows.append(row)
    if rows:
        catalog = pd.concat([catalog, pd.DataFrame(rows)], ignore_index=True)
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
    catalog = ensure_price_columns(catalog)
    catalog["sort_order"] = pd.to_numeric(catalog["sort_order"], errors="coerce").fillna(9999)
    catalog = apply_catalog_overrides(catalog)
    catalog = add_extra_products(catalog)
    rules["active"] = rules["active"].fillna(True).astype(bool)
    return analysis, catalog, rules


def build_input_form(analysis: pd.DataFrame) -> dict[str, Any]:
    values: dict[str, Any] = {}
    st.subheader("Анализ воды и объект")

    meta_cols = st.columns(2)
    with meta_cols[0]:
        values["analysis_number"] = st.text_input("Номер анализа", "")
    with meta_cols[1]:
        analysis_date = st.date_input("Дата анализа", value=date.today())
        values["analysis_date"] = analysis_date.strftime("%d.%m.%Y")

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



def build_resin_line_form(values: dict[str, Any]) -> dict[str, Any]:
    values["product_line"] = "ЭКОБРАЙТ"
    return values


def build_odor_form(values: dict[str, Any]) -> dict[str, Any]:
    st.subheader("1.2. Запах воды")
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



def get_value(values: dict[str, Any], aliases: list[str], default: float = 0.0) -> float:
    for key in aliases:
        if key in values:
            return safe_float(values.get(key), default)
    return default


def remove_codes(selected: list[str], codes: set[str]) -> list[str]:
    return [code for code in selected if code not in codes]

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




def apply_column_size_logic(selected: list[str], reasons: list[str], values: dict[str, Any], catalog: pd.DataFrame) -> None:
    people = int(safe_float(values.get("people", 4), 4))

    # Убираем старые типоразмеры колонн, чтобы не смешивались разные группы
    column_codes = {
        "FRP0844",
        "FRP1044",
        "FRP1054",
        "FRP1252",
        "FRP1354",
    }
    selected[:] = [code for code in selected if code not in column_codes]

    if people <= 4:
        for code in ["FRP0844", "FRP1044", "FRP1054"]:
            add_code(selected, catalog, code)
        reasons.append("До 4 проживающих включительно: подобраны колонны TWG FRP0844, TWG FRP1044, TWG FRP1054.")
    elif 5 <= people <= 7:
        for code in ["FRP1252", "FRP1354"]:
            add_code(selected, catalog, code)
        reasons.append("От 5 до 7 проживающих включительно: подобраны колонны TWG FRP1252 и TWG FRP1354.")
    else:
        for code in ["FRP1354"]:
            add_code(selected, catalog, code)
        reasons.append("Более 7 проживающих: требуется инженерная проверка производительности, предварительно выбрана TWG FRP1354.")

def apply_engineering_rules(
    selected: list[str],
    reasons: list[str],
    values: dict[str, Any],
    catalog: pd.DataFrame,
) -> None:
    line = str(values.get("product_line", "TWG"))
    iron = get_value(values, ["iron", "fe", "железо"])
    manganese = get_value(values, ["manganese", "mn", "марганец"])
    hardness = get_value(values, ["hardness", "жесткость", "hard"])
    oxid = get_value(values, ["permanganate", "oxidizability", "permanganate_oxidizability", "окисляемость"])
    h2s = get_value(values, ["h2s", "hydrogen_sulfide", "сероводород"])
    ph = get_value(values, ["ph", "pH"], default=7.0)
    tds = get_value(values, ["tds", "salt", "солесодержание"])
    odor_score = int(values.get("odor_score", 0) or 0)

    fe_mn = iron + manganese

    selected[:] = remove_codes(selected, TWG_MEDIA_CODES | ECOBRIGHT_MEDIA_CODES)

    add_code(selected, catalog, "DF100")

    needs_aeration = fe_mn >= 1.0 or h2s > 0 or odor_score >= 2
    hard_water = hardness >= 3.0
    very_hard_water = hardness >= 5.0
    has_iron_mn = iron > 0.3 or manganese > 0.05
    high_iron_mn = fe_mn >= 5.0
    organic = oxid >= 5.0
    high_organic = oxid >= 9.0
    complex_water = high_iron_mn or high_organic or (organic and has_iron_mn) or h2s > 0 or odor_score >= 2

    if needs_aeration:
        add_code(selected, catalog, "AERO")
        reasons.append("Требуется предварительная аэрация: есть железо/марганец, сероводород или выраженный запах.")

    if line == "TWG":
        if complex_water and high_organic:
            add_code(selected, catalog, "TWG_ORGANIC_MIX")
            reasons.append("Выбрана TWG VR5U Organic Mix: высокая окисляемость/органика и сложный состав воды.")
        elif has_iron_mn or h2s > 0 or odor_score > 0:
            add_code(selected, catalog, "VR3F100T")
            reasons.append("Выбрана TWG 1054-VR5U-100T: удаление железа, марганца и запаха после подготовки воды.")

        if hard_water:
            add_code(selected, catalog, "VRSD100VB")
            add_code(selected, catalog, "SALT70")
            if very_hard_water:
                reasons.append("Жесткость высокая: требуется TWG 1054-VR5D-100VB и солевой бак TWG SALT-70L PRO.")
            else:
                reasons.append("Жесткость выше комфортной: рекомендовано умягчение на TWG 1054-VR5D-100VB.")

    else:
        if high_organic and has_iron_mn:
            add_code(selected, catalog, "ECO_ORGANIC_PLUS_B")
            reasons.append("Выбран ЭКОБРАЙТ Органик+ Б: органика/окисляемость плюс железо или марганец.")
        elif high_organic:
            add_code(selected, catalog, "ECO_ORGANIC_PLUS")
            reasons.append("Выбран ЭКОБРАЙТ Органик+: высокая окисляемость и органические загрязнения.")
        elif organic and has_iron_mn:
            add_code(selected, catalog, "ECO_ORGANIC_B")
            reasons.append("Выбран ЭКОБРАЙТ Органик Б: органика плюс железо/марганец/запах.")
        elif organic:
            add_code(selected, catalog, "ECO_ORGANIC")
            reasons.append("Выбран ЭКОБРАЙТ Органик: повышенная окисляемость и органические примеси.")
        elif has_iron_mn or h2s > 0 or odor_score > 0:
            add_code(selected, catalog, "ECO_ORGANIC_B")
            reasons.append("Выбран ЭКОБРАЙТ Органик Б: железо/марганец/запах без выраженной органики.")

        if hard_water:
            if complex_water:
                add_code(selected, catalog, "ECO_STD_B")
                reasons.append("Для умягчения в сложной воде выбран ЭКОБРАЙТ Стандарт Б.")
            else:
                add_code(selected, catalog, "ECO_STD")
                reasons.append("Для умягчения выбран ЭКОБРАЙТ Стандарт.")
            add_code(selected, catalog, "SALT70")

    if ph < 6.5 or ph > 8.5:
        reasons.append("pH вне комфортного диапазона 6.5–8.5: нужна инженерная проверка перед финальным КП.")

    if tds >= 800:
        add_code(selected, catalog, "OSMOS")
        reasons.append("Солесодержание повышено: рекомендован обратный осмос для питьевой воды.")

    apply_column_size_logic(selected, reasons, values, catalog)

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

    if any(code in selected for code in {"VRSD100VB", "ECO_STD", "ECO_STD_B", "ECO_ORGANIC", "ECO_ORGANIC_B", "ECO_ORGANIC_PLUS", "ECO_ORGANIC_PLUS_B"}):
        add_code(selected, catalog, "SALT70")

    return normalize_selection_order(selected), reasons


def enrich_analysis_for_kp(analysis: pd.DataFrame, values: dict[str, Any]) -> pd.DataFrame:
    extra_rows = [
        {
            "parameter": "analysis_number",
            "value": values.get("analysis_number", ""),
            "unit": "",
            "label": "Номер анализа",
        },
        {
            "parameter": "analysis_date",
            "value": values.get("analysis_date", ""),
            "unit": "",
            "label": "Дата анализа",
        },
    ]

    if "product_line" in values:
        extra_rows.append({
            "parameter": "product_line",
            "value": values.get("product_line", ""),
            "unit": "",
            "label": "Линейка загрузок",
        })

    extra_rows.extend([
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

    return pd.concat([analysis, pd.DataFrame(extra_rows)], ignore_index=True)


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
            f"Линейка: {values.get('product_line', 'TWG')}\n\n"
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
    table = selected_df[["name", "code", "qty", "price", "description"]].copy()
    table["sum"] = table["qty"] * table["price"]
    table.insert(0, "№", range(1, len(table) + 1))
    table.rename(
        columns={
            "name": "Наименование",
            "code": "Модель",
            "qty": "Кол-во",
            "price": "Цена, ₽",
            "sum": "Сумма, ₽",
            "description": "Назначение",
        },
        inplace=True,
    )

    st.dataframe(table, width="stretch", hide_index=True)
    total_sum = (selected_df["qty"] * selected_df["price"]).sum()
    st.success(
        f"Итого за базовый комплект: {total_sum:,.0f} ₽".replace(",", " ")
    )

    if {"retail_price", "partner_price", "benefit"}.issubset(selected_df.columns):
        with st.expander("Внутренний расчет выгоды (не выводится в КП)"):
            internal_table = selected_df[["name", "code", "qty", "retail_price", "partner_price", "benefit"]].copy()
            internal_table["Выгода итого, ₽"] = internal_table["qty"] * internal_table["benefit"]
            internal_table.rename(
                columns={
                    "name": "Наименование",
                    "code": "Модель",
                    "qty": "Кол-во",
                    "retail_price": "Розница, ₽",
                    "partner_price": "Партнер, ₽",
                    "benefit": "Выгода за ед., ₽",
                },
                inplace=True,
            )
            st.dataframe(internal_table, width="stretch", hide_index=True)
            total_benefit = (selected_df["qty"] * selected_df["benefit"]).sum()
            st.info(f"Итого выгода: {total_benefit:,.0f} ₽".replace(",", " "))

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
    st.subheader("Данные объекта")
    o1, o2, o3 = st.columns(3)
    with o1:
        object_type = st.text_input("Тип объекта", "Частный дом")
    with o2:
        water_source = st.text_input("Источник воды", "Скважина")
    with o3:
        address = st.text_input("Адрес/объект для КП", "")

    st.subheader("Контакты")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        company = st.text_input("Компания", "Частный клиент")
    with c2:
        manager = st.text_input("Менеджер", "TerraWater Group")
    with c3:
        phone = st.text_input("Телефон", "")
    with c4:
        email = st.text_input("Почта", "")

    return {
        "client_name": company,
        "company": company,
        "object_type": object_type,
        "water_source": water_source,
        "manager": manager,
        "phone": phone,
        "email": email,
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



def build_stage_selection(catalog: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    st.subheader("Подбор оборудования по стадиям")

    catalog = catalog.copy()
    selected_rows = []
    reasons = []

    stage_numeric = pd.to_numeric(catalog["stage"], errors="coerce")

    for stage_num in range(1, 9):
        stage_df = catalog[stage_numeric == stage_num].copy()

        stage_name = STAGE_NAMES.get(stage_num, f"Stage {stage_num}")

        if stage_df.empty:
            st.caption(f"{stage_num}. {stage_name}: нет позиций в прайсе")
            continue

        options = list(stage_df.index)

        def label_func(idx):
            row = catalog.loc[idx]
            code = str(row.get("code", ""))
            name = str(row.get("name", ""))
            price = float(row.get("price", 0) or 0)
            return f"{code} — {name} — {price:,.0f} ₽".replace(",", " ")

        chosen = st.multiselect(
            f"{stage_num}. {stage_name}",
            options=options,
            format_func=label_func,
            key=f"stage_select_{stage_num}",
        )

        for idx in chosen:
            row = catalog.loc[idx].copy()
            code = str(row.get("code", ""))
            name = str(row.get("name", ""))

            qty = st.number_input(
                f"Кол-во: {code} — {name}",
                min_value=1,
                value=1,
                step=1,
                key=f"qty_stage_{stage_num}_{idx}",
            )

            row["qty"] = int(qty)
            selected_rows.append(row)

        if chosen:
            reasons.append(f"{stage_num}. {stage_name}: выбрано позиций — {len(chosen)}.")

    if not selected_rows:
        empty = catalog.iloc[0:0].copy()
        empty["qty"] = []
        return empty, reasons

    selected_df = pd.DataFrame(selected_rows)
    selected_df["_order"] = range(len(selected_df))

    return selected_df, reasons


def main() -> None:
    st.sidebar.image(str(BASE_DIR / "assets" / "twg_logo.svg"), width="stretch")
    st.sidebar.title("TerraWater Robot")
    st.sidebar.write("Подбор оборудования по анализу воды и формирование КП в HTML/PDF.")

    analysis, catalog, rules = load_data()
    client_data = build_client_form()
    values = build_input_form(analysis)
    values = build_resin_line_form(values)
    values = build_odor_form(values)
    selected_df, reasons = build_stage_selection(catalog)

    if selected_df.empty:
        st.warning("Выберите оборудование хотя бы в одном Stage.")
        selected_df = catalog.iloc[0:0].copy()
    else:
        selected_df["_order"] = range(len(selected_df))
        selected_df = selected_df.sort_values(["_order", "sort_order"])

    render_visual_kp(selected_df, reasons, values, client_data)
    export_kp_block(selected_df, reasons, values, client_data, analysis)
    # admin_panel(catalog, rules)  # отключено, чтобы не падало на пустых code в прайсе


if __name__ == "__main__":
    main()
