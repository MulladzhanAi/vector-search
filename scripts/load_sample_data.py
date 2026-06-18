"""Загрузка тестовых товаров из data/sample_products.json в Elasticsearch.

Использование:
    python -m scripts.load_sample_data

Считает эмбеддинги (passage:) и индексирует bulk-ом через app.indexing.
Индекс должен быть уже создан (scripts.create_index).
"""

import json
from pathlib import Path

from app.indexing import index_products
from app.schemas import Product

DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "sample_products.json"


def main() -> None:
    raw = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    products = [Product(**item) for item in raw]
    count = index_products(products)
    print(f"Проиндексировано товаров: {count}")


if __name__ == "__main__":
    main()
