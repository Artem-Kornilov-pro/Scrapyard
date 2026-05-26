# 🕸️ Scrapyard — Web Scraper as a Service

[![Tests](https://github.com/Artem-Kornilov-pro/scrapyard/actions/workflows/tests.yml/badge.svg)](https://github.com/Artem-Kornilov-pro/scrapyard/actions/workflows/tests.yml)
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

API доступно на `http://localhost:8000/docs`

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
GET    /api/v1/jobs/{id}/logs    # Логи задачи
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
# Создать задачу парсинга
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
    "schedule": "0 */6 * * *"
  }'

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

