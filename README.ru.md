# cinerec

*Документация на других языках: [English](README.md) · Русский.*

Современная **рекомендательная система для фильмов**: бэкенд на FastAPI +
PostgreSQL/pgvector и фронтенд на React (Vite). Система сочетает три стратегии
рекомендаций:

- **Контентные рекомендации** — семантические эмбеддинги каждого фильма
  (название + год + жанры + теги + описание), построенные с помощью
  `sentence-transformers` и хранящиеся в **pgvector**; «похожие фильмы» находятся
  по косинусной близости (индекс HNSW).
- **Коллаборативная фильтрация** — **ALS** (Alternating Least Squares) из библиотеки
  `implicit`, обученный на матрице оценок «пользователь–фильм», для блоков
  «рекомендуем вам» и «также понравилось».
- **Гибрид** — взвешенная смесь двух подходов с min-max-нормализацией
  (настраиваемый параметр `alpha`), что помогает при «холодном старте».

Качество рекомендаций измеряется офлайн по схеме leave-one-out с метриками
**HR@K / NDCG@K** (`scripts/evaluate.py`).

Ответы рекомендаций кэшируются в **Redis** (с прозрачным локальным кэшем в памяти
как запасным вариантом), а модель ALS обновляется **фоновым воркером**, поэтому новые
оценки учитываются без блокировки запросов.

Данные берутся из датасета [MovieLens](https://grouplens.org/datasets/movielens/)
(API-ключ не нужен). Опционально поддерживается обогащение данными из TMDB через
переменную `CINEREC_TMDB_API_KEY`.

## Архитектура

```
frontend/  React + Vite + TS + Tailwind      → http://localhost:5173 (проксирует /api → :8000)
backend/   FastAPI + SQLAlchemy + pgvector    → http://localhost:8000 (документация на /docs)
           recsys/  контентные рекомендации + ALS
           scripts/ load_data, build_embeddings
PostgreSQL 16 + pgvector                      → localhost:5432  (db/пользователь/пароль: cinerec)
```

## Технологический стек

| Слой            | Технологии |
|-----------------|------------|
| API бэкенда     | Python 3.12, FastAPI, Uvicorn, SQLAlchemy 2.0, Pydantic v2 |
| База данных     | PostgreSQL 16 + pgvector (индекс HNSW по косинусу) |
| Кэш             | Redis (запасной вариант — кэш в памяти процесса) |
| Эмбеддинги      | sentence-transformers (`all-MiniLM-L6-v2`, 384 измерения) |
| Коллаборативная | `implicit` ALS (фоновое переобучение) |
| Фронтенд        | React 19, Vite 6, TypeScript, Tailwind CSS v4 |
| Инструменты     | uv (Python), npm (JS), ruff, pytest, eslint |

## Требования

- Python 3.12, [`uv`](https://docs.astral.sh/uv/)
- Node.js 22+
- PostgreSQL 16 с расширением `pgvector`
- Redis (опционально — при недоступности кэш переключается на кэш в памяти)

## Установка

### 1. База данных

```bash
# Создание роли и базы данных (один раз)
sudo -u postgres psql -c "CREATE USER cinerec WITH PASSWORD 'cinerec' SUPERUSER CREATEDB;"
sudo -u postgres psql -c "CREATE DATABASE cinerec OWNER cinerec;"
sudo -u postgres psql -d cinerec -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

Либо используйте Docker: `docker compose up -d db`.

### 2. Бэкенд

```bash
cd backend
uv sync --extra dev                       # установка зависимостей
uv run python -m scripts.migrate          # применить аддитивные миграции схемы (идемпотентно)
uv run python -m scripts.load_data        # скачать и загрузить MovieLens
uv run python -m scripts.build_embeddings # вычислить эмбеддинги + индекс HNSW
uv run uvicorn app.main:app --reload      # http://localhost:8000/docs

# Опционально: обогащение постерами/описаниями из TMDB (нужен CINEREC_TMDB_API_KEY), затем пересчёт эмбеддингов
CINEREC_TMDB_API_KEY=xxx uv run python -m scripts.enrich_tmdb
uv run python -m scripts.build_embeddings

# Опционально: оценка качества рекомендаций (HR@K / NDCG@K)
uv run python -m scripts.evaluate --k 10 --users 300
```

### 3. Фронтенд

```bash
cd frontend
npm install
npm run dev                               # http://localhost:5173
```

## Полезные команды

| Задача          | Бэкенд (`cd backend`)             | Фронтенд (`cd frontend`) |
|-----------------|-----------------------------------|--------------------------|
| Запуск (dev)    | `uv run uvicorn app.main:app --reload` | `npm run dev`        |
| Линтинг         | `uv run ruff check .`             | `npm run lint`           |
| Тесты           | `uv run pytest`                   | —                        |
| Сборка          | —                                 | `npm run build`          |

## Основные эндпоинты API

- `GET /health` — количество фильмов / оценок / эмбеддингов, бэкенд кэша и статус ALS
- `GET /movies?q=&genre=&year_from=&year_to=&min_rating=&sort=&order=&limit=&offset=` —
  каталог с пагинацией (сортировка по `popularity|rating|year|title`);
  возвращает `{total, limit, offset, items}`
- `GET /movies/genres` — список уникальных жанров
- `GET /movies/{id}` — детали фильма + статистика оценок
- `GET /recommend/similar/{movie_id}?method=content|collaborative|hybrid&alpha=`
- `GET /recommend/user/{user_id}?method=hybrid|collaborative|content&alpha=`
- `POST /ratings` — добавить оценку (сбрасывает кэшированную модель ALS и кэш рекомендаций)

## Как это работает

### Контентные рекомендации

Для каждого фильма строится текстовое представление из названия, года, жанров,
тегов и описания (`recsys/content.py`), которое кодируется моделью
`sentence-transformers` в вектор из 384 чисел. Векторы хранятся в столбце типа
`vector` (pgvector) с индексом HNSW по косинусному расстоянию. Поиск похожих фильмов
— это запрос ближайших соседей по этому индексу.

Для офлайн-режима и тестов доступен облегчённый эмбеддер `hash` (на основе
`HashingVectorizer` из scikit-learn), не требующий загрузки модели. Выбор эмбеддера
управляется переменной `CINEREC_EMBEDDER` (`sentence-transformers` или `hash`).

### Коллаборативная фильтрация (ALS)

Модель ALS (`recsys/collaborative.py`) обучается на разреженной матрице
«пользователь–фильм». Она даёт персональные рекомендации и список похожих по
поведению пользователей фильмов. При добавлении новой оценки модель помечается как
«устаревшая» (`invalidate()`), а фоновый воркер переобучает её асинхронно, не блокируя
HTTP-запросы. Если фоновое переобучение отключено, модель переобучается синхронно при
следующем обращении.

### Гибрид

Гибридный режим (`recsys/hybrid.py`) нормализует оценки контентной и коллаборативной
моделей методом min-max и смешивает их с весом `alpha` (по умолчанию контент и
коллаборатив комбинируются так, чтобы сгладить «холодный старт» для новых
пользователей и фильмов).

### Кэш и фоновое переобучение

Ответы рекомендаций кэшируются (`recsys/cache.py`). Если Redis доступен по адресу
`CINEREC_REDIS_URL`, используется он (пространство имён `cinerec:rec:`, сериализация
в JSON, TTL из `CINEREC_CACHE_TTL_SECONDS`); иначе прозрачно используется кэш в памяти
процесса. Текущий бэкенд кэша виден в ответе `GET /health`.

## Конфигурация

Все настройки задаются переменными окружения с префиксом `CINEREC_`
(см. `app/config.py`). Основные:

| Переменная                          | По умолчанию | Назначение |
|-------------------------------------|--------------|------------|
| `CINEREC_DATABASE_URL`              | `postgresql+psycopg://cinerec:cinerec@localhost:5432/cinerec` | Строка подключения к БД |
| `CINEREC_EMBEDDER`                  | `sentence-transformers` | Тип эмбеддера (`sentence-transformers` или `hash`) |
| `CINEREC_EMBEDDING_MODEL`           | `all-MiniLM-L6-v2` | Модель sentence-transformers |
| `CINEREC_EMBEDDING_DIM`             | `384` | Размерность эмбеддингов |
| `CINEREC_ALS_FACTORS`               | `64` | Число латентных факторов ALS |
| `CINEREC_ALS_ITERATIONS`            | `20` | Число итераций обучения ALS |
| `CINEREC_REDIS_URL`                 | `redis://localhost:6379/0` | Адрес Redis (пусто — отключить) |
| `CINEREC_CACHE_TTL_SECONDS`         | `300` | TTL кэша рекомендаций |
| `CINEREC_ENABLE_BACKGROUND_RETRAIN` | `true` | Фоновое переобучение ALS |
| `CINEREC_RETRAIN_INTERVAL_SECONDS`  | `60` | Интервал проверки «устаревания» модели |
| `CINEREC_TMDB_API_KEY`              | — | Ключ TMDB для обогащения постерами/описаниями |

## Разработка

- Линтинг бэкенда: `cd backend && uv run ruff check .`
- Тесты бэкенда: `cd backend && uv run pytest` (тесты используют эмбеддер `hash`,
  отдельную БД `cinerec_test` и синхронное переобучение)
- Линтинг фронтенда: `cd frontend && npm run lint`
- Сборка фронтенда: `cd frontend && npm run build`
- CI (GitHub Actions) прогоняет линтинг и тесты бэкенда (с сервисом pgvector) и
  линтинг/сборку фронтенда — см. `.github/workflows/ci.yml`.
