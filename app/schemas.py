from pydantic import BaseModel


class HealthResponse(BaseModel):
    es: str
    model: str
    index_exists: bool


class Product(BaseModel):
    id: str
    name: str
    description: str
    category: str
    brand: str
    color: str
    material: str
    gender: str
    season: str
    sizes: list[str]
    price: float
    in_stock: bool
    image_url: str


class IndexRequest(BaseModel):
    products: list[Product]


class IndexResponse(BaseModel):
    indexed: int


class SearchFilters(BaseModel):
    in_stock: bool | None = None
    price_min: float | None = None
    price_max: float | None = None
    category: str | None = None
    color: str | None = None
    gender: str | None = None
    season: str | None = None


class SearchRequest(BaseModel):
    query: str
    size: int = 20
    mode: str = "hybrid"
    filters: SearchFilters = SearchFilters()


class SearchHit(BaseModel):
    id: str
    name: str
    category: str
    color: str
    price: float
    in_stock: bool
    image_url: str
    score: float


class SearchResponse(BaseModel):
    total: int
    results: list[SearchHit]
