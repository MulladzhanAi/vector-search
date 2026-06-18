from app.config import settings
from app.embeddings import embed
from app.es_client import es
from app.schemas import SearchFilters, SearchHit, SearchRequest, SearchResponse

# Поля, которые возвращаем из ES (без тяжёлого embedding).
SOURCE_FIELDS = ["id", "name", "category", "color", "price", "in_stock", "image_url"]

# Константа RRF и размер пула кандидатов для каждого из двух списков.
RANK_CONSTANT = 60
HYBRID_POOL = 50


def build_filters(f: SearchFilters) -> list[dict]:
    """Собрать список ES-условий из фильтров (null = не применять).

    Один и тот же список подставляется и в kNN, и в BM25.
    """
    clauses: list[dict] = []

    if f.in_stock is not None:
        clauses.append({"term": {"in_stock": f.in_stock}})

    if f.price_min is not None or f.price_max is not None:
        rng: dict = {}
        if f.price_min is not None:
            rng["gte"] = f.price_min
        if f.price_max is not None:
            rng["lte"] = f.price_max
        clauses.append({"range": {"price": rng}})

    for field in ("category", "color", "gender", "season"):
        value = getattr(f, field)
        if value is not None:
            clauses.append({"term": {field: value}})

    return clauses


def search_knn(req: SearchRequest) -> SearchResponse:
    """Смысловой поиск: эмбеддинг запроса + kNN по полю embedding."""
    qvec = embed(req.query, is_query=True)
    filters = build_filters(req.filters)

    body = {
        "knn": {
            "field": "embedding",
            "query_vector": qvec,
            "k": req.size,
            "num_candidates": 100,
            "filter": filters,
        },
        "size": req.size,
        "_source": SOURCE_FIELDS,
    }

    resp = es.search(index=settings.index_name, body=body)
    hits = resp["hits"]["hits"]
    results = [
        SearchHit(**hit["_source"], score=hit["_score"]) for hit in hits
    ]
    return SearchResponse(total=len(results), results=results)


def search_hybrid(req: SearchRequest) -> SearchResponse:
    """Гибрид: kNN + BM25 с одинаковыми фильтрами, слияние ручным RRF."""
    qvec = embed(req.query, is_query=True)
    filters = build_filters(req.filters)

    # 1) kNN-список (пул кандидатов).
    knn_body = {
        "knn": {
            "field": "embedding",
            "query_vector": qvec,
            "k": HYBRID_POOL,
            "num_candidates": 100,
            "filter": filters,
        },
        "size": HYBRID_POOL,
        "_source": SOURCE_FIELDS,
    }
    knn_resp = es.search(index=settings.index_name, body=knn_body)
    knn_hits = knn_resp["hits"]["hits"]

    # 2) Словесный (BM25) список.
    bm25_body = {
        "query": {
            "bool": {
                "must": {
                    "multi_match": {
                        "query": req.query,
                        "fields": [
                            "name^2",
                            "description",
                            "category",
                            "color",
                            "brand",
                        ],
                    }
                },
                "filter": filters,
            }
        },
        "size": HYBRID_POOL,
        "_source": SOURCE_FIELDS,
    }
    bm25_resp = es.search(index=settings.index_name, body=bm25_body)
    bm25_hits = bm25_resp["hits"]["hits"]

    # _source сохраняем при первом проходе, чтобы не ходить в ES повторно.
    sources: dict[str, dict] = {}
    scores: dict[str, float] = {}
    for hits in (knn_hits, bm25_hits):
        for rank, hit in enumerate(hits, start=1):
            doc_id = hit["_id"]
            sources.setdefault(doc_id, hit["_source"])
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (RANK_CONSTANT + rank)

    ranked = sorted(scores, key=lambda d: scores[d], reverse=True)[: req.size]
    results = [
        SearchHit(**sources[doc_id], score=scores[doc_id]) for doc_id in ranked
    ]
    return SearchResponse(total=len(results), results=results)


def search(req: SearchRequest) -> SearchResponse:
    """Диспетчер по режиму поиска."""
    if req.mode == "knn":
        return search_knn(req)
    return search_hybrid(req)
