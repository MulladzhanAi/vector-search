from sentence_transformers import SentenceTransformer

from app.config import settings

# Singleton: модель грузится один раз (на старте приложения), не на каждый запрос.
_model: SentenceTransformer | None = None


def load_model() -> SentenceTransformer:
    """Загрузить модель эмбеддингов один раз и закэшировать."""
    global _model
    if _model is None:
        _model = SentenceTransformer(
            settings.model_name, cache_folder=settings.models_dir
        )
    return _model


def is_loaded() -> bool:
    return _model is not None


def embed(text: str, is_query: bool) -> list[float]:
    """Вектор текста с обязательными префиксами модели e5.

    Тексты товаров эмбеддятся с префиксом `passage: `, поисковые запросы — с
    `query: `. Без префиксов качество e5 падает.
    """
    model = load_model()
    prefix = "query: " if is_query else "passage: "
    return model.encode(prefix + text, normalize_embeddings=True).tolist()
