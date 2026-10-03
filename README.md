# Data Validation Sandbox v2

Вебсистема для інтерактивної декларативної валідації та профілювання якості
даних. Завантажте файл один раз, і система автоматично його профілює та складе
чернетку правил. Далі можна уточнити правила у візуальному конструкторі або в
YAML, миттєво перевірити їх на випадковій вибірці, запустити повну валідацію у
фоні, переглянути проблемні клітинки прямо в таблиці та вивантажити коректні й
карантинні дані.

> v2 продовжує MVP, створений як магістерський інженерний проєкт
> (MSc Computer Science, Neoversity). Що змінилося, див. у розділі
> [Що нового у v2](#що-нового-у-v2).

## Можливості

**Дані**
- Формати: **CSV/TSV** (роздільник визначається автоматично; кодування UTF-8 або CP1251),
  **JSON**, **JSON Lines**, **Parquet**, **Excel (.xlsx)**.
- Формат перевіряється за сигнатурою вмісту (magic bytes), а не лише за розширенням.
  Є захист від decompression bomb і надто глибокого JSON, а також ліміти на розмір, кількість рядків і колонок.
- Файл завантажується **один раз** і зберігається. Усі подальші операції виконуються за `dataset_id`.

**Профілювання**
- Для кожної колонки: тип (integer/float/string/boolean/datetime/array), семантичний тип
  (email, url, uuid, phone, date), повнота, унікальність, min/max/mean/median/std,
  довжини рядків, топ-значення і гістограма.
- Для датасету: повнота клітинок, дублікати рядків, обсяг у пам'яті.
- **Стартові правила** генеруються з профілю: `not_null`, тип, діапазон, regex для
  email/uuid/url, `date` для дат, `allowed_values` для категорій, `unique` для ключів.

**Правила**
- 14 типів перевірок:

  | Колонка | Датасет |
  |---|---|
  | `not_null`, `not_blank`, `dtype`, `range`, `unique`, `allowed_values`, `length`, `regex` (з захистом від ReDoS), `date`, `compare` (між колонками, напр. `end >= start`), `array_length`, `array_items` | `row_count`, `unique_together` (складений ключ) |

- Кожна перевірка має `severity: error | warning`. Попередження показуються у звіті,
  але не переносять рядок у карантин. Також кожній перевірці можна задати власне повідомлення `message`.
- **Візуальний конструктор** будується з каталогу правил на бекенді, тож новий тип правила
  автоматично з'являється в UI. Поруч є **YAML-редактор** із живим лінтингом: помилка
  підкреслюється на потрібному рядку.
- Чернетка правил автоматично зберігається для кожного датасету. Набори правил
  (**rule sets**) можна зберегти й повторно застосувати до інших датасетів.

**Валідація та результати**
- **Перевірка вибірки** (до 1000 випадкових рядків, детермінована) дає миттєвий результат.
- **Повний прогін** виконується асинхронно (Celery + Redis) з прогресом у відсотках.
- Історія всіх запусків, а в кожному запуску зберігається знімок правил.
- Звіт: quality score, склад рядків (валідні / лише попередження / карантин),
  графік проблем по колонках, перелік невдалих перевірок із прикладами значень.
- **Таблиця даних із підсвіткою**: клітинки з помилками й попередженнями виділені,
  причина видна при наведенні. Є фільтри (з проблемами / помилки / попередження / чисті / всі)
  і фільтр за колонкою.
- **Експорт** у CSV, JSON, Parquet або XLSX: чисті рядки, карантин (з колонкою `_issues`)
  або весь набір з анотаціями (`_status`, `_issues`).

**Інтерфейс**: React 19 + Tailwind, світла й темна тема, адаптивна верстка.

## Технології

| Шар | Стек |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2 + Alembic, pandas, pyarrow, Celery, pytest, ruff |
| Сховище | PostgreSQL (метадані), Redis (черга задач), локальна папка або S3/MinIO (файли) |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS 4, React Router, TanStack Query, CodeMirror, Recharts, Vitest |
| Інфраструктура | Docker Compose (dev та prod-like), nginx, GitHub Actions |

## Швидкий старт (Docker)

Потрібен лише Docker з Docker Compose.

```bash
docker compose up --build        # або: make up
```

| Що | Адреса |
|---|---|
| Інтерфейс | <http://localhost:5173> |
| API docs (Swagger) | <http://localhost:8000/api/docs> |
| Стан сервісів | <http://localhost:8000/api/health> |

Піднімаються `postgres`, `redis`, `api` (міграції застосовуються автоматично),
`worker` (Celery) і `web` (Vite з hot reload). Код монтується в контейнери, тому
зміни підхоплюються без перезбирання. Для спроби є приклад даних:
[`examples/customers.csv`](examples/customers.csv) і правила до нього
[`examples/customers.rules.yaml`](examples/customers.rules.yaml).

Корисні команди (`make help` покаже всі):

```bash
make logs        # логи всіх сервісів
make test        # тести бекенду і фронтенду в контейнерах
make lint        # ruff + eslint + tsc
make down        # зупинити (дані зберігаються у volumes)
make reset       # зупинити і ВИДАЛИТИ базу та завантажені файли
make migration m="опис"   # нова міграція Alembic після зміни моделей
```

### Production-like запуск

```bash
make prod-up     # docker compose -f docker-compose.prod.yml up --build -d
```

Інтерфейс і API доступні через nginx на <http://localhost:8080>. Тут використовуються
образи без dev-залежностей, API працює від non-root користувача, `restart: unless-stopped`.
Цей файл є основою для розгортання на сервері: задайте `POSTGRES_PASSWORD` у `.env`,
а щоб зберігати файли в S3 чи MinIO замість volume, вкажіть `STORAGE_BACKEND=s3`,
`S3_BUCKET` і `S3_ENDPOINT_URL`.

## Запуск без Docker

```bash
# Backend: SQLite і задачі в процесі API, Redis не потрібен
cd backend
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env              # INLINE_JOBS=true, SQLite у ./data
alembic upgrade head
uvicorn app.main:app --reload     # http://localhost:8000

# Frontend
cd frontend
npm install
npm run dev                       # http://localhost:5173 (проксіює /api на :8000)
```

## Конфігурація

Усі налаштування задаються змінними оточення (див. [`backend/app/config.py`](backend/app/config.py)
та [`backend/.env.example`](backend/.env.example)):

| Змінна | За замовчуванням | Призначення |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./data/dvs.db` | БД метаданих (у Docker використовується Postgres) |
| `REDIS_URL` | `redis://localhost:6379/0` | брокер Celery |
| `INLINE_JOBS` | `false` | `true` виконує повні прогони у процесі API, без Celery |
| `STORAGE_BACKEND` | `local` | `local` або `s3` |
| `STORAGE_DIR` | `./data/storage` | папка для файлів (`local`) |
| `S3_BUCKET`, `S3_ENDPOINT_URL` | — | для `s3` (MinIO, AWS тощо) |
| `MAX_FILE_SIZE_MB` | `100` | ліміт розміру файлу |
| `MAX_ROWS`, `MAX_COLUMNS` | `2000000`, `500` | ліміти розміру даних |
| `SAMPLE_ROWS` | `1000` | розмір вибірки для швидкої перевірки |

## Формат правил

```yaml
columns:
  customer_id:
    not_null: {}
    unique: {}
  email:
    regex: { pattern: "^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$", message: "Невалідний e-mail" }
  age:
    dtype: { expected: int }
    range: { min: 18, max: 100 }
  plan:
    allowed_values: { values: [free, pro, team], severity: warning }
  last_login:
    date: { format: "%Y-%m-%d" }
    compare: { op: ">=", column: signup_date }
dataset:
  row_count: { min: 100 }
  unique_together: { columns: [email, country] }
```

- `{}`, порожнє значення або `true` вмикають перевірку з параметрами за замовчуванням, `false` вимикає.
- Правила з v1 (лише секція `columns:`) сумісні з v2 без змін.
- Повний опис параметрів віддає `GET /api/rules/catalog`. У UI він видимий у конструкторі.

## API

Усі ендпоінти мають префікс `/api`. Інтерактивна документація: `/api/docs`.

| Метод | Шлях | Опис |
|---|---|---|
| `GET` | `/health` | стан БД, Redis і сховища |
| `POST` | `/datasets` | завантажити файл (multipart), отримати профіль і стартові правила |
| `GET` | `/datasets`, `/datasets/{id}` | список / деталі з профілем і чернеткою правил |
| `PATCH` / `DELETE` | `/datasets/{id}` | перейменувати або зберегти чернетку правил / видалити разом із запусками |
| `GET` | `/datasets/{id}/rows` | рядки з пагінацією |
| `GET` | `/datasets/{id}/suggested-rules` | згенерувати правила з профілю заново |
| `GET` | `/datasets/{id}/jobs` | запуски датасету |
| `GET` | `/rules/catalog` | каталог типів правил і їхніх параметрів |
| `POST` | `/rules/lint` | перевірити YAML (помилки з номерами рядків) |
| `GET/POST/PATCH/DELETE` | `/rule-sets[/{id}]` | збережені набори правил |
| `POST` | `/jobs` | запуск: `{dataset_id, mode: sample\|full, rules_yaml? \| rule_set_id?}` |
| `GET` | `/jobs`, `/jobs/{id}` | історія / статус, прогрес, звіт |
| `GET` | `/jobs/{id}/rows?filter=issues\|errors\|warnings\|clean\|all&column=` | рядки з проблемами по клітинках |
| `GET` | `/jobs/{id}/export/{clean\|quarantine\|annotated}?format=csv\|json\|parquet\|xlsx` | експорт |

## Структура проєкту

```
backend/
  app/
    main.py            FastAPI-застосунок, обробка помилок, /api/health
    config.py          налаштування (env) та ліміти
    db.py              SQLAlchemy engine/session
    models/            orm.py (таблиці) та schemas.py (API-моделі)
    parsers/           CSV/TSV, JSON/JSONL, Parquet, XLSX + визначення формату
    validators/        types.py (каталог правил), lint.py (перевірка YAML), rule_engine.py
    services/          profiler, yaml_generator (стартові правила), datasets, jobs, storage
    routers/           datasets, jobs, rules, rule_sets
    workers/           Celery-воркер
  alembic/             міграції БД
  tests/               pytest (91 тест)
frontend/
  src/
    api/               типізований клієнт і хуки TanStack Query
    components/        UI-примітиви, конструктор і редактор правил, таблиця даних, графіки
    pages/             датасети, датасет (огляд / дані / правила / запуски), запуск, набори правил
    utils/             форматування, модель правил (YAML ⇄ конструктор), тема
examples/              приклад даних і правил
docker-compose.yml       dev-стек
docker-compose.prod.yml  production-like стек (nginx на :8080)
```

## Що нового у v2

| | v1 (MVP) | v2 |
|---|---|---|
| Завантаження | файл передається заново на кожну дію | один раз, далі робота за `dataset_id` |
| Збереження | лише Redis із TTL 24 год | PostgreSQL + Alembic: датасети, набори правил, історія запусків |
| Файли | тільки AWS S3 (потрібен навіть локально) | локальна папка за замовчуванням, S3/MinIO за бажанням |
| Формати | CSV, JSON, Parquet | + TSV, JSON Lines, XLSX, автовизначення роздільника |
| Вибірка | перші N рядків | детермінована випадкова вибірка |
| Правила | 7 типів, тільки на одну колонку | 14 типів, міжколонкові та датасетні, severity, власні повідомлення |
| Редактор | YAML без перевірки | лінтинг із номерами рядків, конструктор із каталогу правил |
| Профіль | тип, пропуски, min/max | + семантичні типи, статистики, гістограми, топ-значення |
| Результати | список порушень | quality score, графіки, таблиця з підсвіченими клітинками, фільтри |
| Експорт | CSV | CSV, JSON, Parquet, XLSX; clean / quarantine / annotated |
| UI | одна сторінка | роутинг, темна тема, адаптивність, тости, історія |
| Якість | pytest | + ruff, ESLint, Vitest, CI (SQLite + Postgres), Docker-збірка в CI |

## Ліцензія

[MIT](LICENSE)
