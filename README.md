# XLog — Logger для Xscope

Временное решение для автоматического сохранения чатов DeepSeek в Яндекс.Диск.

## Структура проекта
- `config/` — настройки и конфиги
- `source/` — исходный код
- `data/` — состояние программы (state.json)
- `logs/` — логи работы программы

## Установка
1. `python -m venv .venv`
2. `source .venv/bin/activate` (или `.venv\Scripts\activate` на Windows)
3. `pip install -r requirements.txt`
4. Скопируй `.env.example` в `.env` и заполни ключи
5. Запуск: `python main.py`