from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import embeddings
from app.config import settings
from app.es_client import es
from app.indexing import index_products
from app.schemas import (
    HealthResponse,
    IndexRequest,
    IndexResponse,
    SearchRequest,
    SearchResponse,
)
from app.search import search as run_search


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Подключение к ES на старте: понятная ошибка, если ES недоступен.
    if not es.ping():
        raise RuntimeError(
            f"Не удалось подключиться к Elasticsearch по адресу {settings.es_url}. "
            "Запущен ли docker compose? (ES ожидается на порту 9201)"
        )
    # Модель эмбеддингов грузится один раз на старте (singleton).
    embeddings.load_model()
    yield


app = FastAPI(title="clothing-search", lifespan=lifespan)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    try:
        es_ok = es.ping()
    except Exception:
        es_ok = False

    try:
        index_exists = bool(es.indices.exists(index=settings.index_name))
    except Exception:
        index_exists = False

    return HealthResponse(
        es="ok" if es_ok else "down",
        model="loaded" if embeddings.is_loaded() else "not_loaded",
        index_exists=index_exists,
    )


@app.post("/index", response_model=IndexResponse)
def index(req: IndexRequest) -> IndexResponse:
    count = index_products(req.products)
    return IndexResponse(indexed=count)


@app.post("/search", response_model=SearchResponse)
def search(req: SearchRequest) -> SearchResponse:
    return run_search(req)
