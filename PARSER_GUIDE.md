# Парсер черги ДП «Документ» — Інструкція

## Як працює парсер

Наш парсер використовує **Playwright** для обходу Cloudflare та отримання доступних дат з сайту pasport.org.ua.

### Режими роботи

#### 1. **Demo режим** (за замовчуванням)
```bash
MODE=demo
```
- Генерує випадкові дати для тестування
- Не потребує доступу до сайту
- Корисний для розробки і тестування бота

#### 2. **Live режим** (потребує реального сайту)
```bash
MODE=live
```
- Запускає браузер Chromium через Playwright
- Автоматично обходить Cloudflare
- Перевіряє кожне місто і послугу
- Витягує доступні дати зі сторінки

## Як використовувати Live режим

### Крок 1: Переключитися на live режим
У файлі `.env`:
```env
MODE=live
```

### Крок 2: Переконатись що Playwright встановлений
```bash
pip install -q playwright
python -m playwright install chromium
```

### Крок 3: Запустити парсер
```bash
python test_parser.py
```

Парсер буде:
1. Запустити браузер для кожного міста
2. Навігувати на `https://{city}.pasport.org.ua/solutions/e-queue`
3. Дочекатися завантаження сторінки
4. Обійти Cloudflare (якщо потрібно)
5. Виділити послуги зі dropdown
6. Витягти доступні дати

## Як працює автоматичний парсинг

### Алгоритм парсера

1. **Запуск браузера**: Для кожного міста запускається окремий контекст Chromium в headless режимі
2. **Навігація**: Заходить на сторінку e-queue міста
3. **Очікування**: Чекає 2 секунди на завантаження JavaScript
4. **Cloudflare**: Намагається кликнути на Cloudflare checkbox (якщо присутній)
5. **Вибір послуги**: Отримує список послуг з dropdown і для кожної:
   - Вибирає послугу
   - Перевіряє чи є вільні дати
   - Витягує дати зі select елемента
6. **Закриття**: Закриває браузер і переходить до наступного міста

### Методи виявлення доступних дат

Парсер використовує **кілька методів** для надійного виявлення:

1. **Select елемент**: Шукає `<select name="date">` з опціями
2. **Контент сторінки**: Шукає слова "доступні", "available"
3. **Календар**: Шукає календарні елементи з `data-date` атрибутом

## Приклад виводу

```
2026-11-03 21:55:42 test INFO Testing Queue Parser
2026-11-03 21:55:42 test INFO Mode: demo
2026-11-03 21:55:42 test INFO Fetching dates...
2026-11-03 21:55:42 test INFO Found 2 open dates:
2026-11-03 21:55:42 test INFO   • Харків / Закордонний паспорт @ 2026-11-17
2026-11-03 21:55:42 test INFO   • Одеса / ID-картка @ 2026-11-29
2026-11-03 21:55:42 test INFO ✅ Parser works!
```

## Налагодження

### Логування
Для детального логування, змініть рівень у коді:
```python
logging.basicConfig(level=logging.DEBUG)
```

### Скріншоти
Щоб зберегти скріншот для налагодження:
```python
await page.screenshot(path="debug.png")
```

### Помилки

| Помилка | Рішення |
|---------|---------|
| `Playwright not installed` | `pip install playwright` |
| `No chromium found` | `python -m playwright install chromium` |
| `Cloudflare detected` | Парсер намагається обійти автоматично |
| `Timeout` | Сайт занадто повільний, збільште timeout у коді |

## Що далі?

1. **Перевести на live**: Поміняй `MODE=demo` на `MODE=live` в `.env`
2. **Запустити бота**: `python bot.py`
3. **Підписатися на обновлення**: Напиши `/subscribe` в Telegram
4. **Отримувати сповіщення**: Бот буде повідомляти коли з'являються вільні дати

## Архітектура

```
bot.py (Telegram бот)
  ↓
checker() (фоновий цикл кожні CHECK_INTERVAL секунд)
  ↓
fetch_dates() (витягує дати)
  ↓
_live_dates() або _demo_dates()
  ↓
Playwright браузер ← Сайт pasport.org.ua
```

## Коди міст

Парсер автоматично перевіряє ці міста:
- Варшава (warsaw.pasport.org.ua)
- Краків (krakow.pasport.org.ua)
- Вроцлав (wroclaw.pasport.org.ua)
- Гданськ (gdansk.pasport.org.ua)
- Люблін (lublin.pasport.org.ua)
- Прага (prague.pasport.org.ua)
- Берлін (berlin.pasport.org.ua)
- Київ (kyiv.pasport.org.ua)
- Львів (lviv.pasport.org.ua)
- Одеса (odesa.pasport.org.ua)
- Дніпро (dnipro.pasport.org.ua)
- Харків (kharkiv.pasport.org.ua)

Все це конфігурується в `config.py` в переменной `CITIES`.
