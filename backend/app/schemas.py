from pydantic import BaseModel, ConfigDict, Field


class MovieBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    year: int | None = None
    genres: list[str] = []
    poster_url: str | None = None
    avg_rating: float | None = None
    num_ratings: int = 0


class MovieDetail(MovieBase):
    tags: str | None = None
    overview: str | None = None
    tmdb_id: int | None = None
    imdb_id: str | None = None


class MoviePage(BaseModel):
    total: int
    limit: int
    offset: int
    items: list[MovieBase]


class ScoredMovie(MovieBase):
    score: float = Field(..., description="Similarity or recommendation score")


class RecommendationResponse(BaseModel):
    source: str = Field(..., description="Recommendation strategy used")
    items: list[ScoredMovie]


class RatingIn(BaseModel):
    user_id: int = Field(..., ge=1)
    movie_id: int = Field(..., ge=1)
    rating: float = Field(..., ge=0.5, le=5.0)


class HealthResponse(BaseModel):
    status: str
    movies: int
    ratings: int
    embeddings: int
    embedder: str
    cache_backend: str
    als: dict
