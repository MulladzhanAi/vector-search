"""Создание индекса Elasticsearch с маппингом для товаров.

Использование:
    python -m scripts.create_index            # создать, если индекса нет
    python -m scripts.create_index --recreate # удалить существующий и создать заново

Удаление индекса — деструктивно, поэтому только под явным флагом --recreate.
"""

import argparse

from app.config import settings
from app.es_client import es


def build_mapping() -> dict:
    """Маппинг индекса (раздел 5 ТЗ). dims берётся из настроек (EMBED_DIM)."""
    return {
        "mappings": {
            "properties": {
                "id": {"type": "keyword"},
                "name": {"type": "text"},
                "description": {"type": "text"},
                "category": {"type": "keyword"},
                "brand": {"type": "keyword"},
                "color": {"type": "keyword"},
                "material": {"type": "keyword"},
                "gender": {"type": "keyword"},
                "season": {"type": "keyword"},
                "sizes": {"type": "keyword"},
                "price": {"type": "float"},
                "in_stock": {"type": "boolean"},
                "image_url": {"type": "keyword", "index": False},
                "embedding": {
                    "type": "dense_vector",
                    "dims": settings.embed_dim,
                    "index": True,
                    "similarity": "cosine",
                },
            }
        }
    }


def create_index(recreate: bool = False) -> None:
    index = settings.index_name
    exists = es.indices.exists(index=index)

    if exists and recreate:
        print(f"Удаляю существующий индекс '{index}' (--recreate)...")
        es.indices.delete(index=index)
        exists = False

    if exists:
        print(
            f"Индекс '{index}' уже существует. "
            "Запусти с --recreate, чтобы пересоздать (это удалит данные)."
        )
        return

    es.indices.create(index=index, body=build_mapping())
    print(f"Индекс '{index}' создан (dims={settings.embed_dim}, similarity=cosine).")


def main() -> None:
    parser = argparse.ArgumentParser(description="Создать индекс ES для товаров.")
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Удалить существующий индекс и создать заново (ДЕСТРУКТИВНО).",
    )
    args = parser.parse_args()
    create_index(recreate=args.recreate)


if __name__ == "__main__":
    main()
