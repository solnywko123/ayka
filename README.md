# Ayka Cleaning — сайт клининговой компании

Статический сайт (Python/Jinja2) + FastAPI-бэкенд для заявок и админки. Подробное ТЗ — [BRIEF.md](BRIEF.md), лог самостоятельных решений — [DECISIONS.md](DECISIONS.md), инструкция для владельца бизнеса без техфона — [НАСТРОЙКА.md](НАСТРОЙКА.md).

## Стек

- **Фронтенд:** статический HTML, генерируется `site/build.py` (Python + Jinja2) из JSON-контента. Ванильные CSS/JS, без фреймворков и сборщиков.
- **Бэкенд:** Python 3.12+ (проверено на 3.13), FastAPI, SQLAlchemy 2.0, Pydantic v2, Alembic. SQLite локально, PostgreSQL в проде.

## Требования

- Python 3.12+ (на Windows, если `python`/`python3` не в PATH — используйте `py`, лаунчер Python).
- `make` (на Windows — через Git Bash/WSL, либо запускайте команды из Makefile напрямую).

## Быстрый старт (локально)

```bash
# 1. Виртуальные окружения и зависимости
py -m venv site/.venv && site/.venv/Scripts/pip install -r site/requirements.txt
py -m venv api/.venv && api/.venv/Scripts/pip install -r api/requirements.txt

# 2. Переменные окружения
cp .env.example .env
# отредактируйте .env — минимум JWT_SECRET, IP_HASH_SALT, ADMIN_PASSWORD_HASH (см. ниже)

# 3. Пароль администратора
api/.venv/Scripts/python -c "import bcrypt, getpass; pw = getpass.getpass(); print(bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode())"
# полученный хеш вставьте в .env как ADMIN_PASSWORD_HASH

# 4. Миграции БД
cd api && ../api/.venv/Scripts/alembic upgrade head && cd ..

# 5. Сборка сайта
site/.venv/Scripts/python site/build.py
# результат — в site/dist/, открыть site/dist/ru/index.html в браузере

# 6. Запуск API
cd api && ../api/.venv/Scripts/uvicorn app.main:app --reload --port 8000
```

На Linux/macOS вместо `Scripts/` используйте `bin/`, и можно пользоваться `make dev` / `make build` / `make test` — см. [Makefile](Makefile).

## Структура репозитория

См. раздел 3 [BRIEF.md](BRIEF.md) — она соблюдена дословно: `site/` — фронтенд-генератор, `api/` — бэкенд, `deploy/` — конфиги деплоя.

## Как редактировать контент

- **Контакты, соцсети, домен, часы работы** → `site/content/config.json` (единственное место, см. раздел 19.1 BRIEF.md).
- **Цены и коэффициенты калькулятора** → `site/content/pricing.json`. Бэкенд читает тот же файл (через `PRICING_PATH` в `.env`), пересобирать API не нужно — только перезапустить процесс, чтобы он перечитал файл при старте.
- **Тексты страниц, FAQ, отзывы, услуги, районы** → `site/content/{ru,ky,en}/*.json`.
- **Статьи блога** → `site/content/{ru,ky,en}/blog/*.md` (Markdown с YAML frontmatter: `title`, `description`, `date`, `slug`).

После любой правки контента пересоберите сайт: `python site/build.py` (или `make build`).

## Как добавить новую услугу

1. Добавьте объект в `services` в `site/content/{ru,ky,en}/services.json` (см. существующие поля: `slug`, `title`, `price_from`, `checklist_included`, `checklist_excluded`, `faq`, `related`).
2. Добавьте базовую ставку в `pricing.json`, если это новый тип уборки.
3. Пересоберите сайт — страница `/{lang}/uslugi/{slug}/` появится автоматически, добавится в sitemap и в блок «Услуги» на главной.

## Как добавить статью в блог

Создайте `site/content/{lang}/blog/{slug}.md` с frontmatter:

```markdown
---
title: "Заголовок статьи"
description: "Мета-описание 140-160 символов"
date: "2026-08-15"
---

Текст статьи в Markdown...
```

Пересоберите сайт — статья появится в `/{lang}/blog/{slug}/` и в списке `/{lang}/blog/`.

## Как добавить язык

1. Скопируйте `site/content/en/` в `site/content/{новый_код}/` и переведите все JSON и Markdown.
2. Добавьте код языка в `languages` в `site/content/config.json`.
3. Добавьте hreflang-запись — она генерируется автоматически из списка языков в конфиге.

## Проверка конфига перед деплоем

```bash
BUILD_ENV=prod python site/check_config.py
```

В режиме `prod` сборка прерывается, если в конфиге остались демо-значения (`+996 700 000 000`, `example.kg`, `info@example.kg` и т.п.) — это защита от выкатки в прод с плейсхолдерами. В режиме `dev` (по умолчанию) выводится предупреждение, сборка продолжается, а на сайте показывается жёлтый баннер демо-режима.

## Тесты

```bash
site/.venv/Scripts/python -m pytest site/tests -v
api/.venv/Scripts/python -m pytest api/tests -v
```

## Деплой

### Фронтенд — Netlify

Конфиг — [deploy/netlify.toml](deploy/netlify.toml). Build command: `python site/build.py`, publish dir: `site/dist`. Подключите репозиторий на netlify.com, переменные окружения из `.env.example` (для сборки достаточно `BUILD_ENV=prod`).

### Бэкенд — Render

Конфиг — [deploy/render.yaml](deploy/render.yaml). Docker-образ из `api/Dockerfile`, health check `/api/v1/health`, управляемый PostgreSQL. Все переменные окружения из `.env.example` нужно задать в дашборде Render.

**Важно:** на бесплатном тарифе Render бывает "холодный старт" ~30 секунд после простоя. Сайт спроектирован так, чтобы не зависеть от API при первой отрисовке (статические страницы отдаются Netlify независимо от состояния бэкенда) — при недоступном API форма заявки деградирует до кнопки WhatsApp.

### Альтернатива — VPS (Docker Compose + Caddy)

```bash
cp .env.example .env   # заполните реальными значениями — POSTGRES_PASSWORD, JWT_SECRET и т.д.
# перед первым запуском отредактируйте deploy/Caddyfile: замените example.kg на реальный домен

docker compose -f docker-compose.prod.yml run --rm site-builder   # собирает site/dist
docker compose -f docker-compose.prod.yml up -d --build           # postgres + api + caddy
```

`deploy/Caddyfile` настраивает автоматический HTTPS через Let's Encrypt. Подробности — в комментариях внутри файла. Пересобирайте `site-builder` после каждой правки контента сайта — Caddy отдаёт `site/dist` как обычную файловую директорию, а не пересобирает её сам.

### Локальная проверка прод-подобного окружения

`docker-compose.yml` (в корне репозитория, без `.prod`) поднимает `postgres` + `api` + `nginx` со собранной статикой на `localhost:8080` — удобно, чтобы проверить, что Docker-образ API вообще стартует и проходит health check, не разворачивая реальный VPS:

```bash
python site/build.py            # site/dist должен существовать до старта nginx
docker compose up --build
```

### Чеклист домена

1. Купить домен `.kg` — регистрируется только через локальных регистраторов Кыргызстана (например NIC.KG), требуется подтверждение личности/организации.
2. DNS: A/AAAA или CNAME на Netlify для корня и `www`, CNAME `api.` → Render.
3. SSL — выпускается автоматически (Netlify/Render Let's Encrypt), для VPS-варианта — Caddy делает это сам.
4. Дождаться распространения DNS (до 24–48 часов), проверить `https://` без предупреждений браузера.

## Аналитика и верификация в поисковиках

ID Google Analytics / Google Ads / Яндекс.Метрики задаются в `site/content/config.json` (поле `analytics`). Пустое значение — скрипт соответствующей системы не подключается вообще. Google Ads конверсия (`lead_submitted`) отправляется только если заполнены оба поля `google_ads_id` и `google_ads_conversion_label` — второе появляется после создания цели конверсии в интерфейсе Google Ads. Инструкция по подтверждению сайта в Google Search Console и Яндекс.Вебмастере — [deploy/verification/README.md](deploy/verification/README.md).

## Опционально: уведомления о заявках в Telegram

Задайте `TELEGRAM_BOT_TOKEN` и `TELEGRAM_CHAT_ID` в `.env` — после этого новые заявки будут дублироваться в Telegram-чат. По умолчанию выключено (пустые значения).
