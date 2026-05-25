# 🕸️ Scrapyard — Web Scraper as a Service

[![Tests](https://github.com/Artem-Kornilov-pro/scrapyard/actions/workflows/tests.yml/badge.svg)](https://github.com/Artem-Kornilov-pro/scrapyard/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Платформа для распределенного сбора данных с веб-сайтов. Позволяет создавать задачи парсинга через REST API, выполнять их по расписанию и получать структурированные результаты с мощной аналитикой.

## 🎯 Возможности

- 📅 **Задачи по расписанию** — cron-выражения для периодического сбора данных
- 🧩 **Универсальный парсер** — задавай CSS-селекторы через API, без написания кода
- 🌐 **Playwright** — поддержка JavaScript-сайтов и SPA
- 📊 **Аналитика** — агрегации MongoDB для статистики по задачам
- 🔄 **Автоочистка** — TTL-индексы для старых результатов
- 🐳 **Docker** — полная контейнеризация, запуск одной командой

## 🛠️ Стек

| Компонент   | Технология             |
|-------------|------------------------|
| API         | FastAPI (async)        |
| База данных | MongoDB + Motor        |
| Очереди     | Celery + Redis         |
| Парсинг     | Playwright             |
| CI/CD       | GitHub Actions         |
| Контейнеры  | Docker, docker-compose |

## 🏗️ Архитектура

Client → FastAPI → Redis → Celery Worker → Playwright → Web
↓
MongoDB
(jobs, results, logs)

text

## 🚀 Быстрый старт

```bash
git clone https://github.com/Artem-Kornilov-pro/scrapyard.git
cd scrapyard
cp .env.example .env
docker-compose up -d
API доступно на http://localhost:8000/docs
```
📡 API (базовые эндпоинты)
http
- POST   /api/v1/jobs          # Создать задачу
- GET    /api/v1/jobs          # Список задач
- GET    /api/v1/jobs/{id}     # Детали задачи
- PUT    /api/v1/jobs/{id}     # Обновить задачу
- DELETE /api/v1/jobs/{id}     # Удалить задачу
- POST   /api/v1/jobs/{id}/pause   # Приостановить
- POST   /api/v1/jobs/{id}/resume  # Возобновить
- GET    /api/v1/results/{id}  # Результаты парсинга
- GET    /api/v1/analytics     # Статистика и метрики


