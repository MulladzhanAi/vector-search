from elasticsearch import Elasticsearch

from app.config import settings

# Один общий клиент ES на всё приложение.
es: Elasticsearch = Elasticsearch(settings.es_url)
