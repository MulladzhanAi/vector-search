# clothing-search — семантический поиск по одежде (MVP)

Поиск по каталогу одежды **по смыслу**, а не только по совпадению слов:
запрос «тёплая зимняя куртка для города» находит товар «Пуховик мужской с
капюшоном». Под капотом — эмбеддинги + Elasticsearch kNN, с гибридом
смысл+слова (ручной RRF).

**Стек:** Python 3.11, FastAPI, Elasticsearch 8.x (нативный kNN),
sentence-transformers (`intfloat/multilingual-e5-base`, векторы 768).

> ⚠️ Elasticsearch поднимается на порту **9201** (порт 9200 занят другим
> локальным проектом). Kibana — на **5602**.

---

## Как работает (вкратце)

- Каждый товар превращается в **эмбеддинг** (768 чисел, кодирующих смысл).
  Текст для эмбеддинга собирается из смысловых полей (`name`, `category`,
  `color`, `material`, `gender`, `season`, `description`).
- Товары и векторы хранятся в Elasticsearch. ES ищет и по словам (BM25), и по
  векторам (kNN, cosine).
- На запрос: запрос → эмбеддинг → kNN ближайших товаров, с фильтрами.
- **Гибрид** (по умолчанию): объединяет смысловой (kNN) и словесный (BM25)
  поиск через RRF (Reciprocal Rank Fusion).
- Модель e5 требует префиксов: товары — `passage: `, запросы — `query: `.

---

## Запуск с нуля

### 1. Поднять Elasticsearch + Kibana

```bash
cp .env.example .env
docker compose up -d
# через ~минуту проверить:
curl http://localhost:9201        # JSON с версией ES
# Kibana (опционально, для отладки): http://localhost:5601 -> на хосте 5602
```

### 2. Установить зависимости (в виртуальном окружении)

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

> При первом запуске модель `intfloat/multilingual-e5-base` (~1.1 GB)
> скачается в проектную папку `models/` (она в `.gitignore`).

### 3. Создать индекс и залить тестовые данные

```bash
python -m scripts.create_index          # создать индекс products
python -m scripts.load_sample_data      # залить 15 тестовых товаров
```

Пересоздать индекс с нуля (удаляет данные — деструктивно, под явным флагом):

```bash
python -m scripts.create_index --recreate
```

### 4. Запустить API

```bash
uvicorn app.main:app --reload
# Swagger UI: http://localhost:8000/docs
```

Проверка готовности:

```bash
curl http://localhost:8000/health
# {"es":"ok","model":"loaded","index_exists":true}
```

---

## API

### `GET /health`
Готовность: доступен ли ES, загружена ли модель, существует ли индекс.

### `POST /index`
Принимает список товаров, считает эмбеддинги (`passage:`), заливает bulk-ом.

```bash
curl -X POST http://localhost:8000/index \
  -H 'Content-Type: application/json' \
  -d '{"products":[ { ... товар ... } ]}'
# {"indexed": 1}
```

### `POST /search`
Основной эндпоинт. `mode`: `"hybrid"` (по умолчанию) или `"knn"`.
Все `filters` опциональны (`null` = не применять).

```bash
curl -X POST http://localhost:8000/search \
  -H 'Content-Type: application/json' \
  -d '{
    "query": "тёплая зимняя куртка для города",
    "size": 20,
    "mode": "hybrid",
    "filters": {
      "in_stock": true,
      "price_min": null,
      "price_max": 10000,
      "category": null,
      "color": null,
      "gender": "мужской",
      "season": null
    }
  }'
```

Ответ:

```json
{
  "total": 12,
  "results": [
    { "id": "sku-001", "name": "...", "category": "куртка", "color": "чёрный",
      "price": 7990, "in_stock": true, "image_url": "...", "score": 0.0312 }
  ]
}
```

> В режиме `hybrid` поле `score` — итоговый RRF-балл (малые значения порядка
> `0.01–0.03`, это нормально). В режиме `knn` — косинусная близость ES.

---

## Примеры запросов

```bash
# смысловой поиск
curl -sX POST localhost:8000/search -H 'Content-Type: application/json' \
  -d '{"query":"лёгкое летнее платье в цветочек","size":5}'

# с фильтром по цене
curl -sX POST localhost:8000/search -H 'Content-Type: application/json' \
  -d '{"query":"тёплая кофта в офис","size":5,"filters":{"price_max":5000}}'

# с фильтром по полу
curl -sX POST localhost:8000/search -H 'Content-Type: application/json' \
  -d '{"query":"удобная обувь на каждый день","size":5,"filters":{"gender":"женский"}}'

# чистый смысловой режим (без BM25)
curl -sX POST localhost:8000/search -H 'Content-Type: application/json' \
  -d '{"query":"что надеть на пробежку","size":5,"mode":"knn"}'
```

---

## Структура проекта

```
vector-search/
├── docker-compose.yml          # Elasticsearch 8.x (порт 9201) + Kibana (5602)
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── app/
│   ├── config.py               # настройки из .env
│   ├── es_client.py            # клиент ES
│   ├── embeddings.py           # модель (singleton) + embed() с префиксами e5
│   ├── schemas.py              # pydantic-модели
│   ├── indexing.py             # build_embed_text() + bulk-индексация
│   ├── search.py               # knn / hybrid (RRF) логика
│   └── main.py                 # FastAPI: /health, /index, /search
├── scripts/
│   ├── create_index.py         # создать индекс (--recreate для пересоздания)
│   └── load_sample_data.py     # залить тестовые товары
├── data/
│   └── sample_products.json    # 15 тестовых товаров
└── models/                     # локальный кэш модели (~1.1 GB, в .gitignore)
```

---

## Конфигурация (`.env`)

| Переменная   | По умолчанию                       | Описание                        |
|--------------|------------------------------------|---------------------------------|
| `ES_URL`     | `http://localhost:9201`            | адрес Elasticsearch             |
| `INDEX_NAME` | `products`                         | имя индекса                     |
| `MODEL_NAME` | `intfloat/multilingual-e5-base`    | модель эмбеддингов              |
| `EMBED_DIM`  | `768`                              | размерность вектора (== модели) |
| `MODELS_DIR` | `models`                           | проектный кэш модели            |

---

## Что НЕ входит в MVP

Реранкинг кросс-энкодером, дотюненная модель, встроенный в ES RRF (`retriever`),
инкрементальная синхронизация каталога, аутентификация, пагинация сложнее
`size`, метрики качества (recall@k, nDCG), мультинодовый ES, кэширование,
загрузка картинок (только URL).
