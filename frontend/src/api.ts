export interface Movie {
  id: number;
  title: string;
  year: number | null;
  genres: string[];
}

export interface MovieDetail extends Movie {
  tags: string | null;
  tmdb_id: number | null;
  imdb_id: string | null;
  avg_rating: number | null;
  num_ratings: number;
}

export interface ScoredMovie extends Movie {
  score: number;
}

export interface RecommendationResponse {
  source: string;
  items: ScoredMovie[];
}

const API = "/api";

async function getJSON<T>(url: string): Promise<T> {
  const resp = await fetch(`${API}${url}`);
  if (!resp.ok) throw new Error(`${resp.status} ${resp.statusText}`);
  return resp.json() as Promise<T>;
}

export const searchMovies = (q: string) =>
  getJSON<Movie[]>(`/movies?limit=24${q ? `&q=${encodeURIComponent(q)}` : ""}`);

export const getMovie = (id: number) => getJSON<MovieDetail>(`/movies/${id}`);

export const getSimilar = (id: number, method: "content" | "collaborative") =>
  getJSON<RecommendationResponse>(`/recommend/similar/${id}?method=${method}&limit=8`);

export const getUserRecs = (userId: number, method: "content" | "collaborative") =>
  getJSON<RecommendationResponse>(`/recommend/user/${userId}?method=${method}&limit=8`);
