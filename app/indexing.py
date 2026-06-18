from elasticsearch.helpers import bulk

from app.config import settings
from app.embeddings import embed
from app.es_client import es
from app.schemas import Product


def build_embed_text(p: Product) -> str:
    """Текст товара для эмбеддинга — собирается из смысловых полей."""
    return (
        f"{p.name}. Категория: {p.category}. Цвет: {p.color}. "
        f"Материал: {p.material}. Пол: {p.gender}. Сезон: {p.season}. {p.description}"
    )


def index_products(products: list[Product]) -> int:
    """Посчитать эмбеддинги (passage:) и залить товары в ES bulk-ом.

    Возвращает количество успешно проиндексированных документов.
    """
    actions = []
    for p in products:
        doc = p.model_dump()
        doc["embedding"] = embed(build_embed_text(p), is_query=False)
        actions.append(
            {
                "_index": settings.index_name,
                "_id": p.id,
                "_source": doc,
            }
        )

    success, _ = bulk(es, actions, refresh=True)
    return success
