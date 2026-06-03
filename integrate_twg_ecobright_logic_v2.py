from __future__ import annotations

from pathlib import Path
import re

APP = Path("app.py")
if not APP.exists():
    raise SystemExit("app.py не найден. Запустите скрипт из корня репозитория twg.")

src = APP.read_text(encoding="utf-8")
backup = APP.with_suffix(".py.bak_twg_ecobright")
backup.write_text(src, encoding="utf-8")

def sub_once(pattern: str, repl: str, text: str, name: str, flags=re.S) -> str:
    new, count = re.subn(pattern, repl, text, count=1, flags=flags)
    if count != 1:
        raise SystemExit(f"Не удалось применить блок: {name}")
    return new

new_tech_order = '''TECH_ORDER = [
    "DF100",
    "AERO",
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
]'''

src = sub_once(r'TECH_ORDER = \[\n.*?\n\]\n\nDISPLAY_NAME_OVERRIDES', new_tech_order + "\n\nDISPLAY_NAME_OVERRIDES", src, "TECH_ORDER")

extra_constants = '''
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
'''

if "ECOBRIGHT_MEDIA_CODES" not in src:
    src = src.replace("\nODOR_TYPES = {", "\n" + extra_constants + "\nODOR_TYPES = {", 1)

new_apply_catalog_overrides = '''
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
'''
src = sub_once(
    r'def apply_catalog_overrides\(catalog: pd\.DataFrame\) -> pd\.DataFrame:\n.*?\n\ndef load_data',
    new_apply_catalog_overrides + "\n\ndef load_data",
    src,
    "apply_catalog_overrides",
)

add_extra_products_func = '''
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

'''

if "def add_extra_products(" not in src:
    src = src.replace("\n\ndef load_data()", "\n\n" + add_extra_products_func + "def load_data()", 1)

if "catalog = add_extra_products(catalog)" not in src:
    src = src.replace(
        "    catalog = apply_catalog_overrides(catalog)\n    rules[\"active\"]",
        "    catalog = apply_catalog_overrides(catalog)\n    catalog = add_extra_products(catalog)\n    rules[\"active\"]",
        1,
    )

build_resin_line_form = '''
def build_resin_line_form(values: dict[str, Any]) -> dict[str, Any]:
    st.subheader("1.1. Линейка загрузок")
    c1, c2 = st.columns([1, 3])
    with c1:
        values["product_line"] = st.radio(
            "Что подбирать",
            ["TWG", "ЭКОБРАЙТ"],
            horizontal=True,
        )
    with c2:
        st.info(
            "Робот использует одну инженерную схему, но меняет линейку загрузок: TWG или ЭКОБРАЙТ. "
            "Механические фильтры, аэрация, УФ и осмос остаются общими элементами системы."
        )
    return values

'''

if "def build_resin_line_form(" not in src:
    src = src.replace("\n\ndef build_odor_form", "\n\n" + build_resin_line_form + "def build_odor_form", 1)
    src = src.replace('    st.subheader("1.1. Запах воды")', '    st.subheader("1.2. Запах воды")', 1)

helper_funcs = '''
def get_value(values: dict[str, Any], aliases: list[str], default: float = 0.0) -> float:
    for key in aliases:
        if key in values:
            return safe_float(values.get(key), default)
    return default


def remove_codes(selected: list[str], codes: set[str]) -> list[str]:
    return [code for code in selected if code not in codes]

'''

if "def get_value(" not in src:
    src = src.replace("\n\ndef rule_matches", "\n\n" + helper_funcs + "def rule_matches", 1)

new_apply_engineering_rules = '''
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

    add_code(selected, catalog, "BB20")
    add_code(selected, catalog, "PP20")
'''

src = sub_once(
    r'def apply_engineering_rules\(\n.*?\n\ndef normalize_selection_order',
    new_apply_engineering_rules + "\n\ndef normalize_selection_order",
    src,
    "apply_engineering_rules",
)

old_salt = '''    if "VRSD100VB" in selected:
        add_code(selected, catalog, "SALT70")
'''
new_salt = '''    if any(code in selected for code in {"VRSD100VB", "ECO_STD", "ECO_STD_B", "ECO_ORGANIC", "ECO_ORGANIC_B", "ECO_ORGANIC_PLUS", "ECO_ORGANIC_PLUS_B"}):
        add_code(selected, catalog, "SALT70")
'''
if old_salt in src:
    src = src.replace(old_salt, new_salt, 1)

if "values = build_resin_line_form(values)" not in src:
    src = src.replace(
        "    values = build_input_form(analysis)\n    values = build_odor_form(values)",
        "    values = build_input_form(analysis)\n    values = build_resin_line_form(values)\n    values = build_odor_form(values)",
        1,
    )

if '"parameter": "product_line"' not in src:
    src = src.replace(
        '    extra_rows = pd.DataFrame([\n',
        '    extra_rows = pd.DataFrame([\n        {\n            "parameter": "product_line",\n            "value": values.get("product_line", "TWG"),\n            "unit": "",\n            "label": "Линейка загрузок",\n        },\n',
        1,
    )

if "Линейка: {values.get('product_line'" not in src:
    src = src.replace(
        '            f"Расход: до {values.get(\'flow_peak\', 1.5)} м³/ч\\n\\n"\n            f"Запах:',
        '            f"Расход: до {values.get(\'flow_peak\', 1.5)} м³/ч\\n\\n"\n            f"Линейка: {values.get(\'product_line\', \'TWG\')}\\n\\n"\n            f"Запах:',
        1,
    )

APP.write_text(src, encoding="utf-8")
print("Готово: app.py обновлен.")
print(f"Резервная копия: {backup}")
