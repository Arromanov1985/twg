# patch_twg_vs.py
# Запуск:
# 1. Скопировать файл в корень проекта twg-master
# 2. Открыть VS Code терминал
# 3. Выполнить: python patch_twg_vs.py

from pathlib import Path

print("TWG patch helper")

print("""
Нужно внести изменения:

1. Добавить поля:
   - Номер анализа
   - Дата анализа

2. Добавить контакты:
   - Компания
   - Менеджер
   - Телефон
   - Почта

3. В прайс добавить колонки:
   - Розница
   - Партнер
   - Выгода

4. Формула:
   Выгода = Розница - Партнер

5. В КП выводить только Розницу.

Откройте:
- app.py
- src/kp_generator.py
- templates/kp_template.html
- data/equipment_catalog.xlsx
""")
