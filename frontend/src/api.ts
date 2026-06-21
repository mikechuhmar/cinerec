export interface Movie {
  id: number;
  title: string;
  year: number | null;
  genres: string[];
  poster_url: string | null;
  avg_rating: number | null;
  num_ratings: number;
}

export interface MovieDetail extends Movie {
  tags: string | null;
  overview: string | null;
  tmdb_id: number | null;
  imdb_id: string | null;
}

export interface ScoredMovie extends Movie {
  score: number;
}

export interface MoviePage {
  total: number;
  limit: number;
  offset: number;
  items: Movie[];
}

export interface RecommendationResponse {
  source: string;
  items: ScoredMovie[];
}

export type SimilarMethod = "content" | "collaborative" | "hybrid";
export type UserMethod = "hybrid" | "collaborative" | "content";

export interface CatalogQuery {
  q?: string;
  genre?: string;
  sort?: string;
  order?: "asc" | "desc";
  minRating?: number;
  limit?: number;
  offset?: number;
}

const API = "/api";

async function getJSON<T>(url: string): Promise<T> {
  const resp = await fetch(`${API}${url}`);
  if (!resp.ok) throw new Error(`${resp.status} ${resp.statusText}`);
  return resp.json() as Promise<T>;
}

export function searchMovies(query: CatalogQuery): Promise<MoviePage> {
  const p = new URLSearchParams();
  if (query.q) p.set("q", query.q);
  if (query.genre) p.set("genre", query.genre);
  if (query.sort) p.set("sort", query.sort);
  if (query.order) p.set("order", query.order);
  if (query.minRating) p.set("min_rating", String(query.minRating));
  p.set("limit", String(query.limit ?? 24));
  p.set("offset", String(query.offset ?? 0));
  return getJSON<MoviePage>(`/movies?${p.toString()}`);
}

export const getGenres = () => getJSON<string[]>("/movies/genres");

export const getMovie = (id: number) => getJSON<MovieDetail>(`/movies/${id}`);

export const getSimilar = (id: number, method: SimilarMethod) =>
  getJSON<RecommendationResponse>(`/recommend/similar/${id}?method=${method}&limit=8`);

export const getUserRecs = (userId: number, method: UserMethod) =>
  getJSON<RecommendationResponse>(`/recommend/user/${userId}?method=${method}&limit=8`);

export async function addRating(
  userId: number,
  movieId: number,
  rating: number,
): Promise<void> {
  const resp = await fetch(`${API}/ratings`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: userId, movie_id: movieId, rating }),
  });
  if (!resp.ok) throw new Error(`${resp.status} ${resp.statusText}`);
}
