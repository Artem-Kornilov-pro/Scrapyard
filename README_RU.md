# 🕸️ Scrapyard — Web Scraper as a Service

[![Tests](https://github.com/Artem-Kornilov-pro/scrapyard/actions/workflows/tests.yml/badge.svg)](https://github.com/Artem-Kornilov-pro/scrapyard/actions/workflows/tests.yml)
[![Docker Compose E2E](https://github.com/Artem-Kornilov-pro/scrapyard/actions/workflows/docker-e2e.yml/badge.svg)](https://github.com/Artem-Kornilov-pro/scrapyard/actions/workflows/docker-e2e.yml)
[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[English](README.md) | **Русский**

Платформа для распределённого сбора данных с веб-сайтов. Позволяет создавать задачи парсинга через REST API, выполнять их по расписанию и получать структурированные результаты с мощной аналитикой.

---

## 🎯 Возможности

- 📅 **Задачи по расписанию** — cron-выражения для периодического сбора данных
- 🧩 **Универсальный парсер** — задавай CSS-селекторы через API, без написания кода
- 🌐 **Playwright** — поддержка JavaScript-сайтов и SPA
- 📊 **Аналитика** — агрегации MongoDB для статистики по задачам
- 🔄 **Автоочистка** — TTL-индексы для старых результатов
- ⚡ **Кэширование Redis** — аналитика кэшируется на 5 мин, списки задач на 1 мин
- 🔐 **API-ключи и rate limiting** — опциональный заголовок `X-API-Key`, лимиты на Redis по IP
- 🤖 **Этика парсинга** — учитывает `robots.txt`, троттлинг запросов по домену
- 📈 **Grafana + Prometheus** — дашборд с метриками запросов/латентности/ошибок и Redis, auto-provisioned
- 🛡️ **Глобальный обработчик 500** — все непойманные исключения логируются с трейсбеком, клиент получает безопасный JSON
- 🐳 **Docker** — запуск всех сервисов одной командой

---

## 🛠️ Стек технологий

| Компонент   | Технология             | Почему |
|-------------|------------------------|--------|
| API         | FastAPI (async)        | Высокая производительность, автодокументация |
| База данных | MongoDB + Motor        | Гибкие схемы, асинхронный драйвер |
| Очереди     | Celery + Redis         | Надёжное распределение задач |
| Парсинг     | Playwright             | Поддержка JavaScript-рендеринга |
| Кэширование | Redis                  | Быстрые ответы аналитики |
| CI/CD       | GitHub Actions         | Тесты, линтинг, покрытие |
| Контейнеры  | Docker, docker-compose | Простое развёртывание |

---

## 🏗️ Архитектура

```
                    ┌─────────────┐
                    │   Celery    │
                    │    Beat     │
                    └──────┬──────┘
                           │ планирует задачи
                           ▼
┌──────────┐      ┌─────────────────┐      ┌──────────────┐
│  Клиент  │────▶│   FastAPI        │────▶│    Redis     │
│          │      │   (REST API)    │      │   (Брокер)   │
└──────────┘      └─────────────────┘      └──────┬───────┘
       ▲                                          │
       │                                          ▼
       │                              ┌─────────────────┐
       │                              │  Celery Worker  │
       │                              │  (Playwright)   │
       │                              └────────┬────────┘
       │                                       │
       │                                       ▼
       │                              ┌─────────────────┐
       └──────────────────────────────│    MongoDB      │
                                      │ (задачи, рез-ты,│
                                      │     логи)       │
                                      └─────────────────┘
```

---

## 🚀 Быстрый старт

```bash
git clone https://github.com/Artem-Kornilov-pro/scrapyard.git
cd scrapyard
cp .env.example .env
docker-compose up -d
```

| Сервис | URL |
|--------|-----|
| API (Swagger UI) | `http://localhost:8000/docs` |
| Prometheus-метрики | `http://localhost:8000/metrics` |
| Prometheus UI | `http://localhost:9090` |
| Grafana | `http://localhost:3000` (admin / admin) |

Дашборд "Scrapyard Overview" подхватывается автоматически через provisioning. Показывает частоту запросов по статусам, P95-латентность, частоту ошибок и метрики Redis.

---

## 🔒 Чеклист для продакшна

По умолчанию эти параметры выключены ради простого локального старта, но их стоит настроить перед публичным запуском:

| Параметр | По умолчанию | Эффект |
|----------|--------------|--------|
| `API_KEY` | не задан (auth выключен) | Если задан, каждый запрос к `/api/v1/*` должен содержать заголовок `X-API-Key` |
| `RATE_LIMIT_PER_MINUTE` | `120` | Лимит запросов с одного IP на `/api/v1/*`, на Redis; `0` отключает |
| `RESPECT_ROBOTS_TXT` | `true` | Воркер проверяет `robots.txt` целевого сайта перед парсингом и пропускает запрещённые URL |
| `DOMAIN_THROTTLE_SECONDS` | `2.0` | Минимальный интервал между запросами к одному домену, общий для всех воркеров (через Redis-лок) |
| `SCRAPER_USER_AGENT` | `ScrapyardBot/1.0 (+https://github.com/...)` | User-Agent браузера, также используется для сверки с правилами `robots.txt` |
| `DRY_RUN_TIMEOUT_SECONDS` | `30` | Сколько API ждёт ответа воркера на `/dry-run`, прежде чем вернуть 504 |

Функции на Redis (кэш, rate limiting, троттлинг доменов) работают в режиме fail-open: если Redis недоступен, API и воркеры продолжают работать без этой защиты, а не падают. `/health` никогда не требует авторизации и не лимитируется — для проверок оркестратором.

```bash
# с заданным API_KEY
curl http://localhost:8000/api/v1/jobs -H "X-API-Key: <ваш-ключ>"
```

---

## 📡 API Эндпоинты

### Задачи

```http
POST   /api/v1/jobs              # Создать задачу
GET    /api/v1/jobs              # Список задач (с пагинацией)
GET    /api/v1/jobs/{id}         # Детали задачи
PUT    /api/v1/jobs/{id}         # Обновить задачу
DELETE /api/v1/jobs/{id}         # Удалить задачу
POST   /api/v1/jobs/{id}/pause   # Приостановить
POST   /api/v1/jobs/{id}/resume  # Возобновить
POST   /api/v1/jobs/{id}/run     # Запустить задачу сейчас, минуя расписание
POST   /api/v1/jobs/dry-run      # Проверить селекторы на реальной странице без сохранения задачи
GET    /api/v1/jobs/{id}/logs    # Логи задачи
```

### Результаты

```http
GET    /api/v1/jobs/{id}/results         # Список результатов (сначала новые)
GET    /api/v1/jobs/{id}/results/export  # Экспорт items одного запуска в JSON или CSV
GET    /api/v1/jobs/{id}/results/diff    # Diff двух запусков (по умолчанию — два последних)
```

### Аналитика

```http
GET    /api/v1/analytics/overview        # Общая сводка
GET    /api/v1/analytics/jobs/{id}/stats # Статистика по задаче
GET    /api/v1/analytics/slowest         # Топ медленных задач
GET    /api/v1/analytics/success-rate    # Процент успешных
GET    /api/v1/logs                      # Все логи (с фильтрацией)
```

### Примеры

```bash
# Проверить селекторы перед сохранением задачи
curl -X POST http://localhost:8000/api/v1/jobs/dry-run \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/products",
    "selectors": {
      "items": "div.product-card",
      "fields": {"title": {"selector": "h3.title", "attr": "text"}}
    }
  }'

# Создать задачу парсинга — notify_webhook сработает после 5 подряд
# неудачных попыток; diff_key используется для сопоставления items
# между запусками в /diff
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Цены товаров",
    "url": "https://example.com/products",
    "selectors": {
      "items": "div.product-card",
      "fields": {
        "title": {"selector": "h3.title", "attr": "text"},
        "price": {"selector": "span.price", "attr": "text", "transform": "strip_currency"}
      }
    },
    "schedule": "0 */6 * * *",
    "diff_key": "title",
    "notify_webhook": "https://hooks.example.com/scrapyard-alerts"
  }'

# Запустить прямо сейчас, не дожидаясь расписания
curl -X POST http://localhost:8000/api/v1/jobs/{id}/run

# Посмотреть, что изменилось с последнего запуска
curl http://localhost:8000/api/v1/jobs/{id}/results/diff

# Экспортировать последний запуск в CSV
curl http://localhost:8000/api/v1/jobs/{id}/results/export?format=csv

# Получить сводку
curl http://localhost:8000/api/v1/analytics/overview
```

---

## 📁 Структура проекта

```
scrapyard/
├── api/                    # FastAPI приложение
│   ├── core/               # Конфигурация, БД, кэш
│   ├── models/             # Pydantic модели
│   ├── routes/             # API эндпоинты
│   ├── services/           # Бизнес-логика
│   └── tests/              # Тесты API
├── worker/                 # Celery воркер
│   ├── engines/            # Playwright движок, парсеры
│   ├── tasks/              # Celery задачи (парсер, планировщик)
│   └── tests/              # Тесты воркера
├── scripts/                # Скрипт нагрузочного тестирования
├── docker/                 # Dockerfile'ы
├── .github/workflows/      # CI/CD
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## 🤝 Участие в разработке

См. [CONTRIBUTING.md](CONTRIBUTING.md) для правил внесения изменений.

---

## 📄 Лицензия

Этот проект распространяется под лицензией MIT — подробности в [LICENSE](LICENSE).

