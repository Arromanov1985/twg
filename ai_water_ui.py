# -*- coding: utf-8 -*-
import streamlit as st
from ai_water_recognition import recognize_water_analysis_document


def _set_value(name, value):
    if value is None or value == "":
        return

    keys = [
        name,
        "water_" + name,
        "input_" + name,
        "analysis_" + name,
    ]

    aliases = {
        "ph": ["pH", "ph_value"],
        "iron": ["fe", "iron_value"],
        "manganese": ["mn", "manganese_value"],
        "hardness": ["hardness_value"],
        "tds": ["mineralization", "dry_residue", "tds_value"],
        "permanganate": ["pmo", "permanganate_value"],
        "odor_h2s": ["odor", "h2s", "odor_value"],
        "bacteria": ["microbiology", "bacteria_value"],
        "turbidity": ["turbidity_value"],
        "color": ["color_value"],
        "ammonium": ["nh4", "ammonium_value"],
    }

    for alias in aliases.get(name, []):
        keys.extend([alias, "water_" + alias, "input_" + alias, "analysis_" + alias])

    for key in keys:
        st.session_state[key] = value


def apply_ai_water_values_to_session(values):
    for key, value in (values or {}).items():
        _set_value(key, value)


def render_ai_water_recognition_block():
    st.markdown("---")
    st.subheader("AI распознавание анализа воды по фото")
    st.caption("Загрузите фото анализа воды или сделайте фото с телефона. ИИ распознает показатели и подставит их в расчет.")

    api_key = st.secrets.get("OPENAI_API_KEY", "")
    if not api_key:
        st.info("ИИ-распознавание появится после добавления OPENAI_API_KEY в Streamlit Secrets.")

    tab_upload, tab_camera = st.tabs(["Загрузить фото", "Камера телефона"])

    uploaded_file = None

    with tab_upload:
        f = st.file_uploader(
            "Загрузите фото или PDF анализа воды для ИИ-распознавания",
            type=["jpg", "jpeg", "png", "pdf"],
            key="ai_water_photo_upload",
        )
        if f is not None:
            uploaded_file = f

    with tab_camera:
        cam = st.camera_input(
            "Сфотографируйте анализ воды",
            key="ai_water_photo_camera",
        )
        if cam is not None:
            uploaded_file = cam

    if uploaded_file is None:
        return

    st.image(uploaded_file, caption="Фото / PDF анализа воды", use_container_width=True)

    if st.button("Распознать анализ воды ИИ", use_container_width=True):
        if not api_key:
            st.error("Нет OPENAI_API_KEY в Streamlit Secrets.")
            return

        try:
            with st.spinner("ИИ распознает показатели анализа воды..."):
                result = recognize_water_analysis_document(
                    api_key=api_key,
                    raw=uploaded_file.getvalue(),
                    filename=getattr(uploaded_file, "name", "analysis.jpg"),
                    mime=getattr(uploaded_file, "type", None),
                )

            st.session_state["ai_water_recognition_result"] = result

        except Exception as exc:
            message = str(exc)

            if "rate_limit" in message.lower() or "ratelimit" in message.lower() or "429" in message:
                st.error("ИИ-распознавание временно недоступно: превышен лимит OpenAI API. Введите анализ вручную или повторите позже.")
            elif "insufficient_quota" in message.lower() or "quota" in message.lower():
                st.error("ИИ-распознавание недоступно: закончилась квота OpenAI API. Проверьте баланс/лимиты API-ключа.")
            else:
                st.error("ИИ-распознавание не выполнено. Введите анализ вручную или попробуйте другое фото.")
                with st.expander("Техническая ошибка"):
                    st.code(message)

            st.session_state["ai_water_recognition_result"] = {
                "recognized": False,
                "confidence": "low",
                "source_quality": "Ошибка распознавания",
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
                    "ammonium": None
                },
                "warnings": ["ИИ-распознавание не выполнено. Можно ввести показатели вручную."],
                "raw_detected_text": ""
            }

    result = st.session_state.get("ai_water_recognition_result")
    if not result:
        return

    if result.get("recognized"):
        st.success("Анализ распознан. Проверьте значения перед подбором.")
    else:
        st.error("Анализ не удалось надежно распознать.")

    st.caption("Уверенность: " + str(result.get("confidence", "medium")))

    if result.get("source_quality"):
        st.caption("Качество изображения: " + str(result.get("source_quality")))

    values = result.get("values") or {}

    labels = {
        "ph": "pH",
        "iron": "Железо, мг/л",
        "manganese": "Марганец, мг/л",
        "hardness": "Жесткость, мг-экв/л",
        "tds": "Минерализация / TDS, мг/л",
        "permanganate": "Перманганатная окисляемость, мгО2/л",
        "odor_h2s": "Запах / H2S",
        "bacteria": "Бактериология",
        "turbidity": "Мутность",
        "color": "Цветность",
        "ammonium": "Аммоний",
    }

    rows = []
    for key, label in labels.items():
        rows.append({"Показатель": label, "Распознано": values.get(key)})

    st.dataframe(rows, width="stretch", hide_index=True)

    warnings = result.get("warnings") or []
    if warnings:
        st.warning("Проверьте перед расчетом:")
        for warning in warnings:
            st.write("- " + str(warning))

    with st.expander("Распознанный текст анализа"):
        st.text(result.get("raw_detected_text", ""))

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Подставить данные в расчет", use_container_width=True):
            apply_ai_water_values_to_session(values)
            st.success("Данные подставлены. Проверьте поля и запустите подбор.")
            st.rerun()

    with col2:
        if st.button("Очистить распознавание", use_container_width=True):
            st.session_state.pop("ai_water_recognition_result", None)
            st.rerun()
