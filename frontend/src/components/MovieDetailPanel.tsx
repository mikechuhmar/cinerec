import type { SimilarMethod } from "../api";
import { useMovie, useSimilar } from "../hooks/useMovies";
import { GenrePills } from "./GenrePills";
import { Poster } from "./Poster";
import { RecGrid } from "./RecGrid";
import { StarRating } from "./StarRating";

const METHODS: SimilarMethod[] = ["hybrid", "content", "collaborative"];

export function MovieDetailPanel({
  movieId,
  userId,
  method,
  setMethod,
  onRate,
  onPick,
}: {
  movieId: number | null;
  userId: number;
  method: SimilarMethod;
  setMethod: (m: SimilarMethod) => void;
  onRate: (value: number) => void;
  onPick: (id: number) => void;
}) {
  const movieQuery = useMovie(movieId);
  const similarQuery = useSimilar(movieId, method);
  const movie = movieQuery.data;

  if (movieId == null || !movie)
    return (
      <div className="rounded-xl border border-dashed border-white/15 p-10 text-center text-slate-500">
        Select a movie to see details and similar titles.
      </div>
    );

  return (
    <div>
      <div className="flex gap-4 rounded-xl border border-white/10 bg-white/5 p-5">
        <div className="w-28 shrink-0">
          <Poster url={movie.poster_url} title={movie.title} />
        </div>
        <div className="flex-1">
          <h2 className="text-xl font-bold">
            {movie.title} {movie.year && <span className="text-slate-400">({movie.year})</span>}
          </h2>
          <div className="mt-2">
            <GenrePills genres={movie.genres} />
          </div>
          <p className="mt-2 text-sm text-slate-300">
            ⭐ {movie.avg_rating ?? "—"} · {movie.num_ratings} ratings
          </p>
          {movie.overview && (
            <p className="mt-2 line-clamp-3 text-xs text-slate-400">{movie.overview}</p>
          )}
          <div className="mt-3">
            <span className="mb-1 block text-xs text-slate-400">Rate as user {userId}:</span>
            <StarRating onRate={onRate} />
          </div>
        </div>
      </div>

      <div className="mt-5">
        <div className="mb-3 flex items-center gap-2">
          <h3 className="font-semibold text-indigo-300">Similar movies</h3>
          <div className="flex gap-1 rounded-lg bg-white/5 p-1 text-xs">
            {METHODS.map((m) => (
              <button
                key={m}
                onClick={() => setMethod(m)}
                className={`rounded px-2 py-1 capitalize transition ${
                  method === m ? "bg-indigo-600 text-white" : "text-slate-400"
                }`}
              >
                {m}
              </button>
            ))}
          </div>
        </div>
        <RecGrid items={similarQuery.data?.items ?? []} onPick={onPick} />
      </div>
    </div>
  );
}
